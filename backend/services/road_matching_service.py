import hashlib
import json
import math
import os
import sqlite3
import urllib.error
import urllib.request
import zlib
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone


DEFAULT_OSRM_URL = "https://router.project-osrm.org"
MAX_CONTROL_POINTS = 10
SPARSE_GAP_METERS = 60
MIN_CONFIDENCE = 0.5
MAX_ENDPOINT_ERROR_METERS = 100
MAX_CORRIDOR_ERROR_METERS = 200
MIN_LENGTH_RATIO = 0.65
MAX_LENGTH_RATIO = 1.8
MAX_ITINERARY_STOPS = 120
MAX_ITINERARY_LEGS = 20
ROAD_CACHE_ENV = "TRANSITGRAPH_ROAD_CACHE_DB"


def _distance_meters(first, second):
    latitude_1, longitude_1 = map(math.radians, first)
    latitude_2, longitude_2 = map(math.radians, second)
    latitude_delta = latitude_2 - latitude_1
    longitude_delta = longitude_2 - longitude_1
    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude_1)
        * math.cos(latitude_2)
        * math.sin(longitude_delta / 2) ** 2
    )
    return 12_742_000 * math.asin(math.sqrt(haversine))


def _geometry_length(geometry):
    return sum(
        _distance_meters(first, second)
        for first, second in zip(geometry, geometry[1:])
    )


def _maximum_gap(geometry):
    return max(
        (
            _distance_meters(first, second)
            for first, second in zip(geometry, geometry[1:])
        ),
        default=0
    )


def _control_points(geometry):
    if len(geometry) <= MAX_CONTROL_POINTS:
        return geometry

    selected = {0, len(geometry) - 1}
    gaps = sorted(
        (
            (_distance_meters(geometry[index], geometry[index + 1]), index)
            for index in range(len(geometry) - 1)
        ),
        reverse=True
    )

    for _, index in gaps:
        if len(selected) >= MAX_CONTROL_POINTS:
            break
        selected.add(index)

        if len(selected) < MAX_CONTROL_POINTS:
            selected.add(index + 1)

    if len(selected) < MAX_CONTROL_POINTS:
        for position in range(MAX_CONTROL_POINTS):
            index = round(
                position * (len(geometry) - 1) / (MAX_CONTROL_POINTS - 1)
            )
            selected.add(index)

            if len(selected) >= MAX_CONTROL_POINTS:
                break

    return [geometry[index] for index in sorted(selected)[:MAX_CONTROL_POINTS]]


def _cache_key(geometry):
    normalized = [
        [round(latitude, 6), round(longitude, 6)]
        for latitude, longitude in geometry
    ]
    content = json.dumps(normalized, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def _cache_database_path(database_path):
    """Retorna um banco de cache separado do banco versionado do grafo."""
    configured_path = os.getenv(ROAD_CACHE_ENV)
    if configured_path:
        return Path(configured_path)

    database_path = Path(database_path)

    # Na aplicação, mantém o cache em data/runtime/road_cache.db.
    if database_path.name == "transitgraph.db":
        return database_path.parent.parent / "runtime" / "road_cache.db"

    # Em testes e bancos temporários, preserva o isolamento no mesmo diretório.
    return database_path.with_name(
        f"{database_path.stem}_road_cache{database_path.suffix}"
    )


def _open_cache_connection(database_path):
    cache_path = _cache_database_path(database_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(cache_path)


def _ensure_cache_table(connection):
    connection.execute("""
        CREATE TABLE IF NOT EXISTS road_geometry_cache (
            cache_key TEXT PRIMARY KEY,
            geometry BLOB NOT NULL,
            confidence REAL NOT NULL,
            original_distance REAL NOT NULL,
            matched_distance REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS road_geometry_rejections (
            cache_key TEXT PRIMARY KEY,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)


def _load_cached(connection, key):
    row = connection.execute(
        "SELECT geometry, confidence FROM road_geometry_cache WHERE cache_key = ?",
        (key,)
    ).fetchone()

    if row is None:
        return None

    return {
        "geometry": json.loads(zlib.decompress(row[0])),
        "confidence": row[1],
        "source": "osrm-cache"
    }


def _load_rejection(connection, key):
    row = connection.execute(
        "SELECT reason FROM road_geometry_rejections WHERE cache_key = ?",
        (key,)
    ).fetchone()
    return row[0] if row else None


def _save_rejection(connection, key, reason):
    connection.execute(
        """
        INSERT OR REPLACE INTO road_geometry_rejections
        (cache_key, reason, created_at)
        VALUES (?, ?, ?)
        """,
        (key, reason, datetime.now(timezone.utc).isoformat())
    )


def _save_cached(connection, key, result, original_distance):
    geometry_blob = sqlite3.Binary(zlib.compress(
        json.dumps(
            result["geometry"],
            separators=(",", ":")
        ).encode("utf-8"),
        level=9
    ))
    connection.execute(
        """
        INSERT OR REPLACE INTO road_geometry_cache
        (cache_key, geometry, confidence, original_distance,
         matched_distance, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            key,
            geometry_blob,
            result["confidence"],
            original_distance,
            result["matched_distance"],
            datetime.now(timezone.utc).isoformat()
        )
    )


def is_coherent_match(original, matched, confidence):
    if len(original) < 2 or len(matched) < 2 or confidence < MIN_CONFIDENCE:
        return False

    if (
        _distance_meters(original[0], matched[0]) > MAX_ENDPOINT_ERROR_METERS
        or _distance_meters(original[-1], matched[-1])
        > MAX_ENDPOINT_ERROR_METERS
    ):
        return False

    original_distance = _geometry_length(original)
    matched_distance = _geometry_length(matched)

    if original_distance <= 0:
        return False

    ratio = matched_distance / original_distance

    if not MIN_LENGTH_RATIO <= ratio <= MAX_LENGTH_RATIO:
        return False

    maximum_corridor_error = max(
        min(
            _distance_meters(point, original_point)
            for original_point in original
        )
        for point in matched
    )
    return maximum_corridor_error <= MAX_CORRIDOR_ERROR_METERS


def _request_osrm_match(geometry, osrm_url):
    control_points = _control_points(geometry)
    coordinates = ";".join(
        f"{longitude:.6f},{latitude:.6f}"
        for latitude, longitude in control_points
    )
    url = (
        f"{osrm_url.rstrip('/')}/match/v1/driving/{coordinates}"
        "?geometries=geojson&overview=full&tidy=true&gaps=ignore"
    )
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "TransitGraph-academic/1.0"}
    )

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            data = json.load(response)
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
        return {"accepted": False, "reason": "service-unavailable"}

    matchings = data.get("matchings") or []

    if data.get("code") != "Ok":
        return {
            "accepted": False,
            "reason": data.get("code") or "osrm-error"
        }

    if len(matchings) != 1:
        return {"accepted": False, "reason": "split-trace"}

    matching = matchings[0]
    coordinates = matching.get("geometry", {}).get("coordinates") or []
    matched = [
        [latitude, longitude]
        for longitude, latitude in coordinates
    ]
    confidence = float(matching.get("confidence") or 0)

    if not is_coherent_match(geometry, matched, confidence):
        return {"accepted": False, "reason": "incoherent-match"}

    return {
        "accepted": True,
        "geometry": matched,
        "confidence": confidence,
        "matched_distance": _geometry_length(matched),
        "source": "osrm"
    }


def refine_itinerary_geometry(itinerary, database_path):
    """Refina shapes esparsos no OSM e mantém fallback integral para GTFS."""

    itinerary["uses_road_matching"] = False
    itinerary["road_matching_status"] = "not-needed"

    if not itinerary.get("uses_gtfs_shapes"):
        return itinerary

    total_stops = sum(len(leg.get("stops", [])) for leg in itinerary["legs"])

    if (
        total_stops > MAX_ITINERARY_STOPS
        or len(itinerary["legs"]) > MAX_ITINERARY_LEGS
    ):
        itinerary["road_matching_status"] = "skipped-large-itinerary"
        return itinerary

    enabled = os.getenv("TRANSITGRAPH_MAP_MATCHING", "1").lower() not in {
        "0", "false", "no"
    }

    if not enabled or database_path is None:
        itinerary["road_matching_status"] = "disabled"
        return itinerary

    candidates = []

    with _open_cache_connection(database_path) as connection:
        _ensure_cache_table(connection)

        for index, leg in enumerate(itinerary["legs"]):
            geometry = leg.get("geometry") or []
            leg["geometry_source"] = "gtfs"

            if len(geometry) < 2 or _maximum_gap(geometry) <= SPARSE_GAP_METERS:
                continue

            key = _cache_key(geometry)
            cached = _load_cached(connection, key)

            if cached:
                leg["geometry"] = cached["geometry"]
                leg["geometry_source"] = cached["source"]
                leg["map_matching_confidence"] = round(
                    cached["confidence"], 4
                )
                itinerary["uses_road_matching"] = True
                continue

            rejection = _load_rejection(connection, key)

            if rejection:
                leg["geometry_source"] = "gtfs-coherence-fallback"
                leg["map_matching_reason"] = rejection
                continue

            candidates.append((index, key, geometry))

    if candidates:
        osrm_url = os.getenv("TRANSITGRAPH_OSRM_URL", DEFAULT_OSRM_URL)
        results = {}
        rejections = {}

        with ThreadPoolExecutor(max_workers=min(4, len(candidates))) as executor:
            futures = {
                executor.submit(_request_osrm_match, geometry, osrm_url):
                    (index, key, geometry)
                for index, key, geometry in candidates
            }

            for future in as_completed(futures):
                index, key, geometry = futures[future]

                try:
                    result = future.result()
                except Exception:
                    result = None

                if result and result.get("accepted"):
                    results[index] = (key, geometry, result)

                elif result and result.get("reason") != "service-unavailable":
                    rejections[index] = (key, result.get("reason"))

        if results or rejections:
            with _open_cache_connection(database_path) as connection:
                _ensure_cache_table(connection)

                for index, (key, original, result) in results.items():
                    leg = itinerary["legs"][index]
                    leg["geometry"] = result["geometry"]
                    leg["geometry_source"] = result["source"]
                    leg["map_matching_confidence"] = round(
                        result["confidence"], 4
                    )
                    _save_cached(
                        connection,
                        key,
                        result,
                        _geometry_length(original)
                    )

                for index, (key, reason) in rejections.items():
                    leg = itinerary["legs"][index]
                    leg["geometry_source"] = "gtfs-coherence-fallback"
                    leg["map_matching_reason"] = reason
                    _save_rejection(connection, key, reason)

                connection.commit()

            if results:
                itinerary["uses_road_matching"] = True

    itinerary["road_matching_status"] = (
        "applied" if itinerary["uses_road_matching"] else "fallback-gtfs"
    )
    return itinerary
