
import os
from pathlib import Path
from time import perf_counter
from flask import Flask, g, jsonify, request, render_template
from collections import deque
from backend.algorithms.bfs import bfs
from backend.algorithms.dfs import dfs
from backend.algorithms.dijkstra import dijkstra
from backend.algorithms.connectivity import weakly_connected_components
from backend.models.database import load_graph
from backend.services.instance_service import INSTANCE_LABELS, build_instances
from backend.services.itinerary_service import build_itinerary
from backend.services.road_matching_service import refine_itinerary_geometry


# Caminhos do projeto
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_DIR / "data" / "processed" / "transitgraph.db"
VISIT_ORDER_LIMIT = 200
DFS_TREE_DEPTH_LIMIT = 5
DFS_TREE_EDGE_LIMIT = 80


def prepare_algorithm_result(result, graph, database_path=None):
    """Prepara uma resposta compacta sem perder as métricas da busca."""
    response = dict(result)
    visit_order = response["visited_order"]

    response["visited_order"] = visit_order[:VISIT_ORDER_LIMIT]
    response["visited_order_total"] = len(visit_order)
    response["visited_order_truncated"] = (
        len(visit_order) > VISIT_ORDER_LIMIT
    )

    if "finish_order" in response:
        finish_order = response["finish_order"]
        response["finish_order"] = finish_order[:VISIT_ORDER_LIMIT]
        response["finish_order_total"] = len(finish_order)

    # reachable_stops repete integralmente visited_order na DFS.
    response.pop("reachable_stops", None)

    path = response.get("path") or []
    response["path_stops"] = [
        graph.get_stop(stop_id)
        for stop_id in path
    ]
    itinerary = build_itinerary(
        graph,
        path,
        database_path=database_path
    )
    response["itinerary"] = refine_itinerary_geometry(
        itinerary,
        database_path
    )

    return response


def prepare_reachability(graph, origin, reachable_stops):
    reachable_ids = set(reachable_stops)
    coverage = {"origin": None, "reachable": [], "unreachable": []}
    for stop_id, stop in graph.stops.items():
        latitude, longitude = stop["latitude"], stop["longitude"]
        if latitude is None or longitude is None:
            continue
        point = [latitude, longitude]
        category = "reachable" if stop_id in reachable_ids else "unreachable"
        coverage[category].append(point)
        if stop_id == origin:
            coverage["origin"] = point
    return coverage


def prepare_dfs_tree(graph, result, show_full_tree):
    """Recover the DFS parent links from its full discovery and finish orders."""
    visit_order = result["visited_order"]
    finish_position = {
        stop_id: position for position, stop_id in enumerate(result["finish_order"])
    }
    ancestors = []
    nodes = []
    edges = []

    for stop_id in visit_order:
        # An earlier vertex is an ancestor only if it finishes after this one.
        while ancestors and finish_position[ancestors[-1]] < finish_position[stop_id]:
            ancestors.pop()
        parent = ancestors[-1] if ancestors else None
        depth = len(ancestors)
        ancestors.append(stop_id)
        if not show_full_tree and depth > DFS_TREE_DEPTH_LIMIT:
            continue

        stop = graph.get_stop(stop_id)
        nodes.append({"data": {
            "id": stop_id,
            "label": stop["name"] or stop_id,
            "isOrigin": parent is None
        }})
        if parent is not None:
            edges.append({"data": {"source": parent, "target": stop_id}})
        if not show_full_tree and len(edges) == DFS_TREE_EDGE_LIMIT:
            break

    return {
        "elements": nodes + edges,
        "edge_count": len(edges),
        "total_edges": len(visit_order) - 1,
        "depth_limit": None if show_full_tree else DFS_TREE_DEPTH_LIMIT,
        "edge_limit": None if show_full_tree else DFS_TREE_EDGE_LIMIT
    }


def read_algorithm_input():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("Informe um objeto JSON com as paradas.")
    stops = []
    for field in ("origin", "destination"):
        value = data.get(field)
        if value is not None and type(value) not in (str, int):
            raise ValueError("Informe códigos de parada válidos.")
        stops.append(str(value).strip() if value is not None else "")
    return stops


def create_app(graph=None, database_path=None):

    database_path = Path(
        database_path or os.getenv("TRANSITGRAPH_DATABASE") or DATABASE_PATH
    )

    app = Flask(
        __name__,
        template_folder=str(PROJECT_DIR / "frontend" / "templates"),
        static_folder=str(PROJECT_DIR / "frontend" / "static")
    )

    # Carrega o grafo somente uma vez
    if graph is None:
        if not database_path.exists():
            raise FileNotFoundError(
                f"Banco de dados não encontrado: {database_path}. "
                "Execute primeiro scripts/build_graph.py."
            )

        graph = load_graph(database_path)

    app.config["GRAPH"] = graph
    app.config["DATABASE_PATH"] = database_path

    instances = build_instances(graph)

    @app.before_request
    def select_instance():
        instance = request.args.get("instance", "full")
        if instance not in instances:
            return jsonify({"error": "Instância da rede indisponível."}), 400
        g.instance = instance
        g.graph = instances[instance]

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            instances={key: INSTANCE_LABELS[key] for key in instances},
            active_instance=g.instance
        )

    # --------------------------------------------------
    # ROTA: VERIFICAR SE A API ESTÁ FUNCIONANDO
    # --------------------------------------------------

    @app.get("/api/health")
    def health():
        graph = g.graph

        return jsonify({
            "status": "online",
            "application": "TransitGraph",
            "vertices": graph.vertex_count(),
            "edges": graph.edge_count()
        })

    # --------------------------------------------------
    # ROTA: ESTATÍSTICAS DO GRAFO
    # --------------------------------------------------

    @app.get("/api/stats")
    def statistics():
        graph = g.graph

        return jsonify({
            "instance": g.instance,
            "vertices": graph.vertex_count(),
            "edges": graph.edge_count(),
            "service_date": graph.metadata.get("service_date"),
            "active_shapes": graph.metadata.get("active_shapes"),
            "edge_routes": sum(
                len(routes)
                for routes in graph.edge_routes.values()
            )
        })

    # --------------------------------------------------
    # ROTA: PESQUISAR PARADAS
    # --------------------------------------------------

    @app.get("/api/stops")
    def search_stops():
        graph = g.graph

        query = request.args.get("q", "").strip()

        try:
            limit = int(request.args.get("limit", 30))
        except ValueError:
            return jsonify({"error": "Limite inválido."}), 400

        limit = max(1, min(limit, 100))

        if not query:
            return jsonify({"error": "Informe um termo de pesquisa usando q."}), 400

        query = query.casefold()
        matches = [
            stop for stop in graph.stops.values()
            if query in stop["stop_id"].casefold()
            or query in (stop["name"] or "").casefold()
        ]
        matches.sort(key=lambda stop: (stop["name"] or "", stop["stop_id"]))
        stops = matches[:limit]
        return jsonify({"count": len(stops), "stops": stops})

    # --------------------------------------------------
    # ROTA: PARADAS VISÍVEIS NO MAPA
    # --------------------------------------------------

    @app.get("/api/stops/map")
    def map_stops():
        graph = g.graph

        required = ["south", "north", "west", "east"]

        if not all(key in request.args for key in required):
            return jsonify({
                "error": "Informe os limites geográficos: south, north, west e east."
            }), 400

        try:
            south = float(request.args["south"])
            north = float(request.args["north"])
            west = float(request.args["west"])
            east = float(request.args["east"])
            limit = int(request.args.get("limit", 3000))
        except ValueError:
            return jsonify({"error": "Coordenadas ou limite inválidos."}), 400

        if south >= north or west >= east:
            return jsonify({"error": "Limites geográficos inválidos."}), 400

        limit = max(1, min(limit, 10000))

        rows = []
        for stop in graph.stops.values():
            latitude, longitude = stop["latitude"], stop["longitude"]
            if latitude is None or longitude is None:
                continue
            if south <= latitude <= north and west <= longitude <= east:
                rows.append(stop)
                if len(rows) == limit:
                    break
        return jsonify({"count": len(rows), "limit": limit, "stops": rows})

    # --------------------------------------------------
    # ROTA: DETALHES DE UMA PARADA
    # --------------------------------------------------

    @app.get("/api/stops/<stop_id>")
    def stop_details(stop_id):
        graph = g.graph

        stop = graph.get_stop(stop_id)

        if stop is None:
            return jsonify({"error": "Parada não encontrada."}), 404

        return jsonify(stop)

    # --------------------------------------------------
    # ROTA: ALGORITMO BFS
    # --------------------------------------------------

    @app.post("/api/algorithms/bfs")
    def run_bfs():
        graph = g.graph
        try:
            origin, destination = read_algorithm_input()
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

        if not origin or not destination:
            return jsonify({
                "error": "Informe as paradas de origem e destino."
            }), 400

        try:
            start = perf_counter()
            result = bfs(graph, origin, destination)

            result["execution_time_ms"] = round((perf_counter() - start) * 1000, 4)
            return jsonify(prepare_algorithm_result(
                result,
                graph,
                database_path
            ))

        except ValueError as error:
            return jsonify({"error": str(error)}), 400

    # --------------------------------------------------
    # ROTA: ALGORITMO DFS
    # --------------------------------------------------

    @app.post("/api/algorithms/dfs")
    def run_dfs():
        graph = g.graph
        try:
            origin, destination = read_algorithm_input()
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

        if not origin:
            return jsonify({
                "error": "Informe a parada de origem."
            }), 400

        try:
            start = perf_counter()
            result = dfs(graph, origin, destination or None)
            result["execution_time_ms"] = round((perf_counter() - start) * 1000, 4)
            result["network_size"] = graph.vertex_count()

            response = prepare_algorithm_result(result, graph, database_path)
            if not destination:
                response["reachability"] = prepare_reachability(
                    graph, origin, result["reachable_stops"]
                )
                response["discovery_tree"] = prepare_dfs_tree(
                    graph, result, show_full_tree=g.instance == "local"
                )
            return jsonify(response)

        except ValueError as error:
            return jsonify({"error": str(error)}), 400

    @app.post("/api/algorithms/dijkstra")
    def run_dijkstra():
        graph = g.graph
        try:
            origin, destination = read_algorithm_input()
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

        if not origin or not destination:
            return jsonify({
                "error": "Informe as paradas de origem e destino."
            }), 400

        try:
            start = perf_counter()
            result = dijkstra(graph, origin, destination)
            result["execution_time_ms"] = round((perf_counter() - start) * 1000, 4)
            return jsonify(prepare_algorithm_result(
                result,
                graph,
                database_path
            ))
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

    # --------------------------------------------------
    # ROTA: COMPARAR BFS E DFS NA MESMA CONSULTA
    # --------------------------------------------------

    @app.post("/api/algorithms/compare")
    def compare_algorithms():
        graph = g.graph
        try:
            origin, destination = read_algorithm_input()
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

        if not origin or not destination:
            return jsonify({
                "error": "Informe as paradas de origem e destino."
            }), 400

        try:
            start = perf_counter()
            bfs_result = bfs(graph, origin, destination)
            bfs_time_ms = (perf_counter() - start) * 1000

            start = perf_counter()
            dfs_result = dfs(graph, origin, destination)
            dfs_time_ms = (perf_counter() - start) * 1000

            bfs_response = prepare_algorithm_result(
                bfs_result,
                graph,
                database_path
            )
            dfs_response = prepare_algorithm_result(
                dfs_result,
                graph,
                database_path
            )
            bfs_response["execution_time_ms"] = round(bfs_time_ms, 4)
            dfs_response["execution_time_ms"] = round(dfs_time_ms, 4)

            return jsonify({
                "origin": origin,
                "destination": destination,
                "bfs": bfs_response,
                "dfs": dfs_response,
                "explanation": {
                    "bfs": (
                        "Explora por níveis e garante o menor caminho em "
                        "número de arestas em um grafo não ponderado."
                    ),
                    "dfs": (
                        "Aprofunda um ramo antes de retroceder e não "
                        "garante o menor caminho."
                    )
                }
            })

        except ValueError as error:
            return jsonify({"error": str(error)}), 400

    # --------------------------------------------------
    # ROTA: COMPONENTES FRACAMENTE CONEXOS
    # --------------------------------------------------

    @app.get("/api/connectivity")
    def connectivity():
        graph = g.graph

        result = weakly_connected_components(graph)

        component_sizes = sorted(
            [len(component) for component in result["components"]],
            reverse=True
        )

        return jsonify({
            "component_count": result["component_count"],
            "largest_component_size": result["largest_component_size"],
            "isolated_stops": result["isolated_stops"],
            "component_sizes": component_sizes
        })

    
    # --------------------------------------------------
    # ROTA: VIZINHANÇA DO GRAFO PARA VISUALIZAÇÃO
    # --------------------------------------------------

    @app.get("/api/graph/neighborhood")
    def graph_neighborhood():
        graph = g.graph

        origin = request.args.get("stop_id", "").strip()

        if not origin:
            return jsonify({
                "error": "Informe o código da parada."
            }), 400

        if not graph.has_stop(origin):
            return jsonify({
                "error": "Parada de origem inexistente."
            }), 404

        try:
            depth = int(request.args.get("depth", 2))
            limit = int(request.args.get("limit", 120))
        except ValueError:
            return jsonify({
                "error": "Profundidade ou limite inválido."
            }), 400

        depth = max(1, min(depth, 10))
        limit = max(10, min(limit, 300))

        queue = deque([(origin, 0)])
        visited = {origin: None}
        edges = {}

        while queue:

            current, current_depth = queue.popleft()

            if current_depth >= depth:
                continue

            for neighbor in graph.get_neighbors(current):

                if neighbor not in visited:

                    if len(visited) >= limit:
                        continue

                    visited[neighbor] = None
                    queue.append((neighbor, current_depth + 1))

                if neighbor in visited:

                    edge = (current, neighbor)

                    if edge not in edges:
                        edges[edge] = len(
                            graph.edge_routes.get(edge, set())
                        )

        nodes = []

        for stop_id in visited:

            stop = graph.get_stop(stop_id)

            nodes.append({
                "data": {
                    "id": stop_id,
                    "label": stop.get("name") or stop_id,
                    "latitude": stop.get("latitude"),
                    "longitude": stop.get("longitude")
                }
            })

        edge_data = []

        for (source, target), route_count in edges.items():

            edge_data.append({
                "data": {
                    "id": f"{source}-{target}",
                    "source": source,
                    "target": target,
                    "route_count": route_count
                }
            })

        return jsonify({
            "origin": origin,
            "depth": depth,
            "node_count": len(nodes),
            "edge_count": len(edge_data),
            "elements": nodes + edge_data
        })


    return app


app = create_app()


if __name__ == "__main__":
    debug = os.getenv("TRANSITGRAPH_DEBUG", "").lower() in {
        "1", "true", "yes"
    }
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=debug
    )
