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
MAX_CONTROL_POINTS = 40
FALLBACK_CONTROL_POINTS = 10
MAX_MATCH_REQUESTS = 20
SPARSE_GAP_METERS = 60
MIN_CONFIDENCE = 0.5
MAX_ENDPOINT_ERROR_METERS = 45
MAX_CORRIDOR_ERROR_METERS = 75
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


def _control_points(geometry, limit=MAX_CONTROL_POINTS):
    if len(geometry) <= limit:
        return geometry

    last = len(geometry) - 1
    return [
        geometry[round(position * last / (limit - 1))]
        for position in range(limit)
    ]


def _cache_key(geometry, osrm_url):
    normalized = [
        [round(latitude, 6), round(longitude, 6)]
        for latitude, longitude in geometry
    ]
    content = json.dumps(
        [5, osrm_url.rstrip("/"), normalized], separators=(",", ":")
    ).encode("utf-8")
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
        "SELECT geometry, confidence, matched_distance FROM road_geometry_cache WHERE cache_key = ?",
        (key,)
    ).fetchone()

    if row is None:
        return None

    return {
        "geometry": json.loads(zlib.decompress(row[0])),
        "confidence": row[1],
        "matched_distance": row[2],
        "source": "osrm-cache"
    }


def _load_rejection(connection, key):
    row = connection.execute(
        "SELECT reason FROM road_geometry_rejections WHERE cache_key = ?",
        (key,)
    ).fetchone()
    if row is None:
        return None
    return json.loads(row[0])


def _save_rejection(connection, key, result):
    connection.execute(
        """
        INSERT OR REPLACE INTO road_geometry_rejections
        (cache_key, reason, created_at)
        VALUES (?, ?, ?)
        """,
        (key, json.dumps(result, separators=(",", ":")), datetime.now(timezone.utc).isoformat())
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

    return (
        _within_corridor(original, matched)
        and _within_corridor(matched, original)
    )


def _within_corridor(points, reference):
    """Compara pontos e pontos médios com os segmentos da outra polilinha."""
    latitude_scale = 111_195
    longitude_scale = latitude_scale * math.cos(math.radians(reference[0][0]))
    limit = MAX_CORRIDOR_ERROR_METERS ** 2
    segments = []
    for (lat_a, lon_a), (lat_b, lon_b) in zip(reference, reference[1:]):
        dy = (lat_b - lat_a) * latitude_scale
        dx = (lon_b - lon_a) * longitude_scale
        segments.append((lat_a, lon_a, dy, dx, dy * dy + dx * dx))

    def close_to_reference(point):
        latitude, longitude = point
        for lat_a, lon_a, dy, dx, length_squared in segments:
            y = (latitude - lat_a) * latitude_scale
            x = (longitude - lon_a) * longitude_scale
            position = (y * dy + x * dx) / length_squared if length_squared else 0
            position = min(1, max(0, position))
            if (y - position * dy) ** 2 + (x - position * dx) ** 2 <= limit:
                return True
        return False

    return all(close_to_reference(point) for point in points) and all(
        close_to_reference(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
        for a, b in zip(points, points[1:])
    )


def _fetch_osrm_match(control_points, osrm_url):
    coordinates = ";".join(
        f"{longitude:.6f},{latitude:.6f}" for latitude, longitude in control_points
    )
    url = (
        f"{osrm_url.rstrip('/')}/match/v1/driving/{coordinates}"
        "?geometries=geojson&overview=full&tidy=false&gaps=split"
    )
    request = urllib.request.Request(url, headers={"User-Agent": "TransitGraph-academic/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        with error:
            if error.code == 400:
                try:
                    return json.load(error)
                except (OSError, ValueError):
                    pass
        return {"code": "service-unavailable"}
    except (OSError, ValueError):
        return {"code": "service-unavailable"}


def _request_osrm_match(geometry, osrm_url):
    control_points = _control_points(geometry)
    data = _fetch_osrm_match(control_points, osrm_url)
    if (isinstance(data, dict) and data.get("code") == "TooBig"
            and len(control_points) > FALLBACK_CONTROL_POINTS):
        control_points = _control_points(geometry, FALLBACK_CONTROL_POINTS)
        data = _fetch_osrm_match(control_points, osrm_url)

    if not isinstance(data, dict):
        return {"accepted": False, "reason": "service-unavailable"}
    matchings = data.get("matchings") or []
    if not isinstance(matchings, list):
        return {"accepted": False, "reason": "service-unavailable"}

    if data.get("code") != "Ok":
        return {
            "accepted": False,
            "reason": data.get("code") or "osrm-error"
        }

    if len(matchings) != 1:
        return {"accepted": False, "reason": "split-trace"}

    try:
        matching = matchings[0]
        coordinates = matching.get("geometry", {}).get("coordinates") or []
        matched = [[float(latitude), float(longitude)] for longitude, latitude in coordinates]
        confidence = float(matching.get("confidence") or 0)
    except (AttributeError, TypeError, ValueError):
        return {"accepted": False, "reason": "service-unavailable"}
    if not math.isfinite(confidence) or any(
        not (-90 <= latitude <= 90 and -180 <= longitude <= 180)
        for latitude, longitude in matched
    ):
        return {"accepted": False, "reason": "service-unavailable"}

    tracepoints = data.get("tracepoints")
    evidence = {"geometry": matched, "confidence": confidence,
                "matched_distance": _geometry_length(matched)}
    if not isinstance(tracepoints, list) or len(tracepoints) != len(control_points):
        return {"accepted": False, "reason": "incomplete-tracepoints", **evidence}

    try:
        waypoint_indexes = []
        displacements = []
        for point, waypoint in zip(control_points, tracepoints):
            if waypoint is None or waypoint["matchings_index"] != 0:
                return {"accepted": False, "reason": "unmatched-tracepoint", **evidence}
            longitude, latitude = waypoint["location"]
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise ValueError("Coordenada inválida.")
            waypoint_indexes.append(waypoint["waypoint_index"])
            displacements.append(_distance_meters(point, (latitude, longitude)))
        if waypoint_indexes != list(range(len(control_points))):
            return {"accepted": False, "reason": "waypoint-order", **evidence}
        evidence["max_anchor_offset_m"] = round(max(displacements), 1)
        if max(displacements) > MAX_ENDPOINT_ERROR_METERS:
            return {"accepted": False, "reason": "anchor-displacement", **evidence}
    except (KeyError, TypeError, ValueError):
        return {"accepted": False, "reason": "invalid-tracepoints", **evidence}

    if not is_coherent_match(geometry, matched, confidence):
        return {"accepted": False, "reason": "incoherent-match", **evidence}

    return {
        "accepted": True,
        **evidence,
        "source": "osrm"
    }


def _diagnostic_match(result):
    return {
        "geometry": result.get("geometry", []),
        "confidence": result.get("confidence"),
        "distance_m": result.get("matched_distance"),
        "max_anchor_offset_m": result.get("max_anchor_offset_m"),
        "reason": result.get("reason"),
    }


def _apply_rejection(leg, segment, result):
    if segment is None:
        leg["geometry_source"] = "gtfs-coherence-fallback"
        leg["map_matching_reason"] = result["reason"]
    else:
        segment["osrm"] = _diagnostic_match(result)
        if "quality" in segment:
            segment["quality"]["issues"].append({
                "code": "osrm-rejected", "reason": result["reason"]
            })


def _apply_match(leg, segment, result):
    if segment is None:
        leg["geometry"] = result["geometry"]
        leg["geometry_source"] = result["source"]
        leg["map_matching_confidence"] = round(result["confidence"], 4)
        return

    segment["osrm"] = _diagnostic_match(result)
    segment["geometry"] = result["geometry"]
    segment["source"] = "osrm"
    if len(leg["geometry_segments"]) == 1:
        leg["geometry"] = result["geometry"]
        leg["geometry_source"] = result["source"]
        leg["map_matching_confidence"] = round(result["confidence"], 4)


def refine_itinerary_geometry(itinerary, database_path):
    """Ajusta fragmentos GTFS independentes e conserva os demais."""
    itinerary["uses_road_matching"] = False
    itinerary["road_matching_status"] = "not-needed"

    if not itinerary.get("uses_gtfs_shapes"):
        return itinerary

    total_stops = sum(len(leg.get("stops", [])) for leg in itinerary["legs"])
    if total_stops > MAX_ITINERARY_STOPS or len(itinerary["legs"]) > MAX_ITINERARY_LEGS:
        itinerary["road_matching_status"] = "skipped-large-itinerary"
        return itinerary

    enabled = os.getenv("TRANSITGRAPH_MAP_MATCHING", "1").lower() not in {
        "0", "false", "no"
    }
    if not enabled or database_path is None:
        itinerary["road_matching_status"] = "disabled"
        return itinerary

    osrm_url = os.getenv("TRANSITGRAPH_OSRM_URL", DEFAULT_OSRM_URL)
    candidates = {}
    attempted = False
    with _open_cache_connection(database_path) as connection:
        _ensure_cache_table(connection)

        for leg in itinerary["legs"]:
            for segment in leg.get("geometry_segments", [None]):
                if segment is not None and segment["source"] != "gtfs":
                    continue
                geometry = (segment if segment is not None else leg).get("geometry") or []
                gap = _maximum_gap(geometry)
                if gap <= SPARSE_GAP_METERS:
                    continue
                if (segment is not None and "quality" in segment
                        and (len(geometry) < 3 or not any(
                            issue["code"] == "sparse-geometry"
                            for issue in segment["quality"]["issues"]
                        ))):
                    continue

                attempted = True
                key = _cache_key(geometry, osrm_url)
                cached = _load_cached(connection, key)
                if cached:
                    _apply_match(leg, segment, cached)
                    itinerary["uses_road_matching"] = True
                    continue

                rejection = _load_rejection(connection, key)
                if rejection:
                    _apply_rejection(leg, segment, rejection)
                    continue

                _, _, destinations = candidates.setdefault(key, (gap, geometry, []))
                destinations.append((leg, segment))

    if candidates:
        # Limita chamadas ao serviço e prioriza os maiores saltos no desenho.
        pending = sorted(candidates, key=lambda key: candidates[key][0], reverse=True)
        pending = pending[:MAX_MATCH_REQUESTS]
        responses = {}
        with ThreadPoolExecutor(max_workers=min(4, len(pending))) as executor:
            futures = {
                executor.submit(_request_osrm_match, candidates[key][1], osrm_url): key
                for key in pending
            }
            for future in as_completed(futures):
                responses[futures[future]] = future.result()

        with _open_cache_connection(database_path) as connection:
            for key, result in responses.items():
                if not result:
                    continue
                _, original, destinations = candidates[key]
                if result["accepted"]:
                    for leg, segment in destinations:
                        _apply_match(leg, segment, result)
                    itinerary["uses_road_matching"] = True
                    _save_cached(connection, key, result, _geometry_length(original))
                else:
                    for leg, segment in destinations:
                        _apply_rejection(leg, segment, result)
                    if result["reason"] != "service-unavailable":
                        _save_rejection(connection, key, result)
            connection.commit()

    if itinerary["uses_road_matching"]:
        itinerary["road_matching_status"] = "applied"
    elif attempted:
        itinerary["road_matching_status"] = "fallback-gtfs"
    return itinerary
