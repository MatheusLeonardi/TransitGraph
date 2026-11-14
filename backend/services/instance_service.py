from collections import deque

from backend.algorithms.graph import Graph


INSTANCE_LABELS = {
    "full": "Grande · Rede completa",
    "local": "Pequena · Dois níveis na Vila Leopoldina",
    "lines": "Intermediária · Linhas 2025-10 e 172K-10",
}
LOCAL_ORIGIN = "480012875"
SELECTED_LINES = {"2025-10", "172K-10"}


def build_instances(graph):
    """Extrai dois recortes da mesma data de serviço da rede completa."""
    instances = {"full": graph}
    if graph.has_stop(LOCAL_ORIGIN):
        distances = {LOCAL_ORIGIN: 0}
        queue = deque([LOCAL_ORIGIN])
        while queue:
            source = queue.popleft()
            if distances[source] == 2:
                continue
            for target in graph.adjacency[source]:
                if target not in distances:
                    distances[target] = distances[source] + 1
                    queue.append(target)
        local_edges = {
            (source, target): graph.edge_routes[source, target]
            for source in distances
            for target in graph.adjacency[source]
            if target in distances
        }
        instances["local"] = copy_subgraph(graph, distances, local_edges)

    line_edges = {
        edge: routes & SELECTED_LINES
        for edge, routes in graph.edge_routes.items()
        if routes & SELECTED_LINES
    }
    if line_edges:
        stops = dict.fromkeys(stop for edge in line_edges for stop in edge)
        instances["lines"] = copy_subgraph(graph, stops, line_edges)

    return instances


def copy_subgraph(graph, stops, edges):
    """Preserva adjacências, linhas, pesos e referências GTFS do recorte."""
    result = Graph()
    result.metadata["service_date"] = graph.metadata.get("service_date")

    for stop_id in stops:
        result.add_stop(**graph.get_stop(stop_id))

    for (source, target), routes in edges.items():
        result.add_edge(source, target)
        for route_id in routes:
            result.add_edge(source, target, route_id)
            if route_id in graph.routes:
                result.add_route(**graph.routes[route_id])
            key = (source, target, route_id)
            if key in graph.trip_edges:
                result.trip_edges[key] = graph.trip_edges[key]
            if key in graph.edge_shapes:
                result.edge_shapes[key] = graph.edge_shapes[key]
        if (source, target) in graph.edge_weights:
            result.set_edge_weight(source, target, graph.edge_weights[source, target])

    result.shape_points = graph.shape_points
    return result
