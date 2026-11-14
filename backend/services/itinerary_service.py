import json
import sqlite3
import zlib
from bisect import bisect_left, bisect_right
from pathlib import Path

from backend.services.geometry_quality import quality
from backend.services.road_matching_service import _distance_meters


def choose_routes(graph, path):
    """Escolhe uma linha por aresta minimizando trocas ao longo do caminho."""

    edges = list(zip(path, path[1:]))

    if not edges:
        return []

    layers = []
    first_candidates = sorted(graph.edge_routes.get(edges[0], set())) or [None]
    current = {
        route_id: (0, None)
        for route_id in first_candidates
    }
    layers.append(current)

    for edge in edges[1:]:
        candidates = sorted(graph.edge_routes.get(edge, set())) or [None]
        next_layer = {}

        for route_id in candidates:
            choices = [
                (
                    cost + int(previous_route != route_id),
                    str(previous_route or ""),
                    previous_route
                )
                for previous_route, (cost, _) in current.items()
            ]
            cost, _, previous_route = min(choices)
            next_layer[route_id] = (cost, previous_route)

        current = next_layer
        layers.append(current)

    final_route = min(
        current,
        key=lambda route_id: (current[route_id][0], str(route_id or ""))
    )
    selected = [final_route]

    for layer_index in range(len(layers) - 1, 0, -1):
        previous_route = layers[layer_index][selected[-1]][1]
        selected.append(previous_route)

    selected.reverse()
    return selected


def _shape_points(graph, database_path, shape_id):
    if shape_id in graph.shape_points:
        return graph.shape_points[shape_id]
    if database_path is None or not Path(database_path).exists():
        return []

    with sqlite3.connect(database_path) as connection:
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )}
        if "shapes" in tables:
            row = connection.execute(
                "SELECT points FROM shapes WHERE shape_id = ?", (shape_id,)
            ).fetchone()
            return json.loads(zlib.decompress(row[0])) if row else []
        if "shape_points" in tables:
            return connection.execute(
                "SELECT sequence, latitude, longitude FROM shape_points "
                "WHERE shape_id = ? ORDER BY sequence", (shape_id,)
            ).fetchall()
    return []


def _clip_shape(points, reference):
    if not points or reference is None or reference.get("issue"):
        return []
    start, end = reference["from_sequence"], reference["to_sequence"]
    if start is None or end is None or not points[0][0] <= start < end <= points[-1][0]:
        return []

    def at(position):
        index = bisect_left(points, position, key=lambda point: point[0])
        sequence, latitude, longitude = points[index]
        if sequence == position:
            return [latitude, longitude]
        previous_sequence, previous_latitude, previous_longitude = points[index - 1]
        fraction = (position - previous_sequence) / (sequence - previous_sequence)
        return [previous_latitude + fraction * (latitude - previous_latitude),
                previous_longitude + fraction * (longitude - previous_longitude)]

    first = bisect_right(points, start, key=lambda point: point[0])
    last = bisect_left(points, end, key=lambda point: point[0])
    clipped = [at(start)]
    for _, latitude, longitude in points[first:last]:
        if clipped[-1] != [latitude, longitude]:
            clipped.append([latitude, longitude])
    endpoint = at(end)
    if clipped[-1] != endpoint:
        clipped.append(endpoint)
    return clipped if len(clipped) > 1 else []


def _same_occurrence(previous, current):
    return (
        previous is not None and current is not None
        and previous.get("to_stop_sequence") is not None
        and previous["trip_id"] == current["trip_id"]
        and previous["shape_id"] == current["shape_id"]
        and previous["to_stop_sequence"] == current.get("from_stop_sequence")
    )


def _select_occurrences(graph, edges, routes):
    """Minimiza quebras de viagem e depois referências sem geometria por linha."""
    layers = []
    for (source, target), route in zip(edges, routes):
        key = (source, target, route)
        candidates = graph.trip_edges.get(key) or [graph.edge_shapes.get(key)]
        layer = []
        for current in candidates:
            missing = int(not current or current.get("issue") is not None)
            if layers and layers[-1][0][0] == route:
                last = layers[-1]
                breaks, gaps, parent = min(
                    (cost[0] + int(not _same_occurrence(previous, current)),
                     cost[1] + missing, index)
                    for index, (_, previous, cost, _) in enumerate(last)
                )
                layer.append((route, current, (breaks, gaps), parent))
            else:
                layer.append((route, current, (0, missing), None))
        layers.append(layer)

    selected = []
    index = None
    for layer in reversed(layers):
        if index is None:
            index = min(range(len(layer)), key=lambda i: layer[i][2])
        _, reference, _, index = layer[index]
        selected.append(reference)
    return selected[::-1]


def _stop_coordinates(graph, source, target):
    stops = [graph.get_stop(source), graph.get_stop(target)]
    if all(stop and stop["latitude"] is not None and stop["longitude"] is not None
           for stop in stops):
        return [[stop["latitude"], stop["longitude"]] for stop in stops]
    return []


def build_itinerary(graph, path, database_path=None):
    """Resolve o caminho topológico em ocorrências GTFS e fragmentos exibíveis."""
    edges = list(zip(path, path[1:]))
    routes = choose_routes(graph, path)
    references = _select_occurrences(graph, edges, routes)
    shapes = {}
    legs = []
    previous_reference = None
    used_shape = False
    has_approximate = False
    for (source, target), route_id, reference in zip(edges, routes, references):
        shape_id = reference["shape_id"] if reference else None
        if shape_id and shape_id not in shapes:
            try:
                shapes[shape_id] = _shape_points(graph, database_path, shape_id)
            except (sqlite3.Error, zlib.error, ValueError):
                shapes[shape_id] = []
        original = _clip_shape(shapes.get(shape_id, []), reference)
        coordinates = _stop_coordinates(graph, source, target)
        evidence = quality(original, coordinates)
        suspect_direction = any(
            issue["code"] == "endpoints-closer-in-reverse" for issue in evidence["issues"]
        )
        source_type = "gtfs" if original and not suspect_direction else "approximate"
        geometry = original if source_type == "gtfs" else coordinates
        new_line = not legs or legs[-1]["route_id"] != route_id
        if new_line:
            route = graph.routes.get(route_id, {})
            legs.append({
                "route_id": route_id,
                "route_short_name": route.get("short_name") or route_id,
                "route_long_name": route.get("long_name"),
                "headsign": reference.get("headsign") if reference else None,
                "from_stop": source, "to_stop": source, "stops": [source],
                "geometry": [], "geometry_segments": []
            })

        leg = legs[-1]
        if not new_line and not _same_occurrence(previous_reference, reference):
            evidence["issues"].append({
                "code": "trip-discontinuity",
                "previous_trip_id": previous_reference.get("trip_id") if previous_reference else None,
                "previous_direction_id": previous_reference.get("direction_id") if previous_reference else None
            })
        elif not new_line and leg["geometry_segments"] and original:
            previous = leg["geometry_segments"][-1]
            if previous["source"] == "gtfs" and previous["geometry"][-1] != original[0]:
                evidence["issues"].append({"code": "shape-discontinuity",
                    "meters": round(_distance_meters(previous["geometry"][-1], original[0]), 1)})

        if reference and reference.get("issue"):
            evidence["issues"].append({"code": reference["issue"]})
        elif reference and reference.get("from_stop_sequence") is None:
            evidence["issues"].append({"code": "legacy-reference"})
        elif reference is None:
            evidence["issues"].append({"code": "no-trip-reference"})

        leg["to_stop"] = target
        leg["stops"].append(target)
        leg["geometry_segments"].append({
            "source": source_type,
            "geometry": geometry,
            "gtfs_geometry": original,
            "from_stop": source,
            "to_stop": target,
            "reference": reference,
            "quality": evidence
        })
        # Campo de compatibilidade, usado somente se o trecho tiver um fragmento.
        leg["geometry"] = geometry if len(leg["geometry_segments"]) == 1 else []
        used_shape |= source_type == "gtfs"
        has_approximate |= source_type == "approximate"
        previous_reference = reference

    return {
        "transfer_count": max(len(legs) - 1, 0),
        "uses_gtfs_shapes": used_shape,
        "has_approximate_geometry": has_approximate,
        "has_sparse_geometry": any(
            segment["source"] == "gtfs" and any(
                issue["code"] in {"sparse-geometry", "long-detour"}
                for issue in segment["quality"]["issues"]
            )
            for leg in legs for segment in leg["geometry_segments"]
        ),
        "legs": legs
    }
