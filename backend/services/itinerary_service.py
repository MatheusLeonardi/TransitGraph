import json
import sqlite3
import zlib
from pathlib import Path


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


def _shape_geometry(graph, database_path, reference):
    if reference is None:
        return []

    shape_id = reference["shape_id"]
    start = reference["from_sequence"]
    end = reference["to_sequence"]

    if shape_id in graph.shape_points:
        points = [
            [latitude, longitude]
            for sequence, latitude, longitude in graph.shape_points[shape_id]
            if min(start, end) <= sequence <= max(start, end)
        ]
        return points if start <= end else list(reversed(points))

    if database_path is None or not Path(database_path).exists():
        return []

    try:
        with sqlite3.connect(database_path) as connection:
            compressed_table_exists = connection.execute(
                """
                SELECT 1 FROM sqlite_master
                WHERE type = 'table' AND name = 'shapes'
                """
            ).fetchone()

            if compressed_table_exists:
                row = connection.execute(
                    "SELECT points FROM shapes WHERE shape_id = ?",
                    (shape_id,)
                ).fetchone()

                if row is None:
                    return []

                shape = json.loads(zlib.decompress(row[0]))
                points = [
                    [latitude, longitude]
                    for sequence, latitude, longitude in shape
                    if min(start, end) <= sequence <= max(start, end)
                ]
                return points if start <= end else list(reversed(points))

            legacy_table_exists = connection.execute(
                """
                SELECT 1 FROM sqlite_master
                WHERE type = 'table' AND name = 'shape_points'
                """
            ).fetchone()

            if not legacy_table_exists:
                return []

            rows = connection.execute(
                """
                SELECT latitude, longitude
                FROM shape_points
                WHERE shape_id = ? AND sequence BETWEEN ? AND ?
                ORDER BY sequence
                """,
                (shape_id, min(start, end), max(start, end))
            ).fetchall()
    except sqlite3.Error:
        return []

    points = [[latitude, longitude] for latitude, longitude in rows]
    return points if start <= end else list(reversed(points))


def _fallback_geometry(graph, source, target):
    geometry = []

    for stop_id in (source, target):
        stop = graph.get_stop(stop_id)

        if stop and stop.get("latitude") is not None:
            geometry.append([stop["latitude"], stop["longitude"]])

    return geometry


def build_itinerary(graph, path, database_path=None):
    """Monta linhas, baldeações e geometria GTFS para um caminho de paradas."""

    if not path or len(path) < 2:
        return {
            "transfer_count": 0,
            "uses_gtfs_shapes": False,
            "legs": []
        }

    edges = list(zip(path, path[1:]))
    selected_routes = choose_routes(graph, path)
    legs = []
    used_shape = False

    for (source, target), route_id in zip(edges, selected_routes):
        reference = graph.edge_shapes.get((source, target, route_id))
        geometry = _shape_geometry(graph, database_path, reference)

        if geometry:
            used_shape = True
        else:
            geometry = _fallback_geometry(graph, source, target)

        if not legs or legs[-1]["route_id"] != route_id:
            route = graph.routes.get(route_id, {})
            legs.append({
                "route_id": route_id,
                "route_short_name": route.get("short_name") or route_id,
                "route_long_name": route.get("long_name"),
                "headsign": reference.get("headsign") if reference else None,
                "from_stop": source,
                "to_stop": target,
                "stops": [source, target],
                "geometry": geometry
            })
            continue

        leg = legs[-1]
        leg["to_stop"] = target
        leg["stops"].append(target)

        if geometry:
            if leg["geometry"] and leg["geometry"][-1] == geometry[0]:
                leg["geometry"].extend(geometry[1:])
            else:
                leg["geometry"].extend(geometry)

    return {
        "transfer_count": max(len(legs) - 1, 0),
        "uses_gtfs_shapes": used_shape,
        "legs": legs
    }
