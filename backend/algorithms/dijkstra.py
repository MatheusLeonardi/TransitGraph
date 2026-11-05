import heapq
import math


AVERAGE_BUS_SPEED_METERS_PER_SECOND = 5.0


def _estimated_travel_time(graph, source, target):
    """Estima segundos de viagem pela distância reta a 18 km/h."""
    first = graph.get_stop(source)
    second = graph.get_stop(target)
    if (
        not first or not second
        or first.get("latitude") is None
        or first.get("longitude") is None
        or second.get("latitude") is None
        or second.get("longitude") is None
    ):
        return 60.0

    lat1, lon1 = map(math.radians, (first["latitude"], first["longitude"]))
    lat2, lon2 = map(math.radians, (second["latitude"], second["longitude"]))
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    distance = 12_742_000 * math.asin(math.sqrt(haversine))
    return max(distance / AVERAGE_BUS_SPEED_METERS_PER_SECOND, 1.0)


def dijkstra(graph, origin, destination):
    """Busca a rota com menor soma de tempos por Dijkstra."""
    if not graph.has_stop(origin):
        raise ValueError("Parada de origem inexistente.")
    if not graph.has_stop(destination):
        raise ValueError("Parada de destino inexistente.")

    best_time = {origin: 0.0}
    parent = {origin: None}
    pending = [(0.0, origin)]
    visited = []

    while pending:
        current_time, current = heapq.heappop(pending)
        if current_time != best_time.get(current):
            continue
        visited.append(current)
        if current == destination:
            break

        for neighbor in graph.get_neighbors(current):
            edge = (current, neighbor)
            weight = graph.edge_weights.get(edge)
            if weight is None:
                weight = _estimated_travel_time(graph, current, neighbor)

            candidate_time = current_time + weight
            if candidate_time < best_time.get(neighbor, float("inf")):
                best_time[neighbor] = candidate_time
                parent[neighbor] = current
                heapq.heappush(pending, (candidate_time, neighbor))

    path = None
    if destination in best_time:
        path = []
        current = destination
        while current is not None:
            path.append(current)
            current = parent[current]
        path.reverse()

    path_edges = list(zip(path, path[1:])) if path else []
    scheduled_edges = sum(edge in graph.edge_weights for edge in path_edges)
    estimated_edges = len(path_edges) - scheduled_edges

    if scheduled_edges and estimated_edges:
        weight_source = "GTFS + estimativa geográfica"
    elif scheduled_edges:
        weight_source = "Horários programados do GTFS"
    else:
        weight_source = "Estimativa geográfica (18 km/h)"

    total_seconds = best_time.get(destination) if path else None
    return {
        "algorithm": "Dijkstra",
        "origin": origin,
        "destination": destination,
        "visited_order": visited,
        "visited_count": len(visited),
        "processed_count": len(visited),
        "discovered_count": len(best_time),
        "path": path,
        "distance": len(path) - 1 if path else None,
        "found": path is not None,
        "travel_time_seconds": round(total_seconds, 1) if total_seconds is not None else None,
        "travel_time_minutes": round(total_seconds / 60, 1) if total_seconds is not None else None,
        "weight_source": weight_source,
        "scheduled_edges_used": scheduled_edges,
        "estimated_edges_used": estimated_edges
    }
