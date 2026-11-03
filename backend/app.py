
import os
import sqlite3
from pathlib import Path
from time import perf_counter
from flask import Flask, jsonify, request, render_template
from collections import deque
from backend.algorithms.bfs import bfs
from backend.algorithms.dfs import dfs
from backend.algorithms.connectivity import weakly_connected_components
from backend.models.database import load_graph
from backend.services.itinerary_service import build_itinerary
from backend.services.road_matching_service import refine_itinerary_geometry


# Caminhos do projeto
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_DIR / "data" / "processed" / "transitgraph.db"
VISIT_ORDER_LIMIT = 200


def prepare_algorithm_result(result, graph, database_path=None):
    """Prepara uma resposta compacta sem perder as métricas da busca."""
    response = dict(result)
    visit_order = response["visited_order"]

    response["visited_order"] = visit_order[:VISIT_ORDER_LIMIT]
    response["visited_order_total"] = len(visit_order)
    response["visited_order_truncated"] = (
        len(visit_order) > VISIT_ORDER_LIMIT
    )

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


def get_database_connection(database_path=DATABASE_PATH):
    """Abre uma conexão com o banco SQLite."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def create_app(graph=None, database_path=None):

    database_path = Path(database_path or DATABASE_PATH)

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
                "Execute primeiro scripts/save_graph.py."
            )

        graph = load_graph(database_path)

    app.config["GRAPH"] = graph
    app.config["DATABASE_PATH"] = database_path

    @app.get("/")
    def index():
     return render_template("index.html")

    # --------------------------------------------------
    # ROTA: VERIFICAR SE A API ESTÁ FUNCIONANDO
    # --------------------------------------------------

    @app.get("/api/health")
    def health():

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

        return jsonify({
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

        query = request.args.get("q", "").strip()

        try:
            limit = int(request.args.get("limit", 30))
        except ValueError:
            return jsonify({"error": "Limite inválido."}), 400

        limit = max(1, min(limit, 100))

        with get_database_connection(database_path) as connection:

            if query:

                search = f"%{query}%"

                rows = connection.execute(
                    """
                    SELECT stop_id, name, latitude, longitude
                    FROM stops
                    WHERE stop_id LIKE ? OR name LIKE ?
                    ORDER BY name
                    LIMIT ?
                    """,
                    (search, search, limit)
                ).fetchall()

            else:

                return jsonify({
                    "error": "Informe um termo de pesquisa usando q."
                }), 400

        return jsonify({
            "count": len(rows),
            "stops": [dict(row) for row in rows]
        })

    # --------------------------------------------------
    # ROTA: PARADAS VISÍVEIS NO MAPA
    # --------------------------------------------------

    @app.get("/api/stops/map")
    def map_stops():

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

        with get_database_connection(database_path) as connection:

            rows = connection.execute(
                """
                SELECT stop_id, name, latitude, longitude
                FROM stops
                WHERE latitude BETWEEN ? AND ?
                  AND longitude BETWEEN ? AND ?
                LIMIT ?
                """,
                (south, north, west, east, limit)
            ).fetchall()

        return jsonify({
            "count": len(rows),
            "limit": limit,
            "stops": [dict(row) for row in rows]
        })

    # --------------------------------------------------
    # ROTA: DETALHES DE UMA PARADA
    # --------------------------------------------------

    @app.get("/api/stops/<stop_id>")
    def stop_details(stop_id):

        stop = graph.get_stop(stop_id)

        if stop is None:
            return jsonify({"error": "Parada não encontrada."}), 404

        return jsonify(stop)

    # --------------------------------------------------
    # ROTA: ALGORITMO BFS
    # --------------------------------------------------

    @app.post("/api/algorithms/bfs")
    def run_bfs():

        data = request.get_json(silent=True) or {}

        origin = data.get("origin")
        destination = data.get("destination")

        if not origin or not destination:
            return jsonify({
                "error": "Informe as paradas de origem e destino."
            }), 400

        try:
            result = bfs(graph, str(origin), str(destination))

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

        data = request.get_json(silent=True) or {}

        origin = data.get("origin")
        destination = data.get("destination")

        if not origin:
            return jsonify({
                "error": "Informe a parada de origem."
            }), 400

        try:
            result = dfs(
                graph,
                str(origin),
                str(destination) if destination else None
            )

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

        data = request.get_json(silent=True) or {}
        origin = data.get("origin")
        destination = data.get("destination")

        if not origin or not destination:
            return jsonify({
                "error": "Informe as paradas de origem e destino."
            }), 400

        try:
            origin = str(origin)
            destination = str(destination)

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
        visited = {origin}
        edges = {}

        while queue:

            current, current_depth = queue.popleft()

            if current_depth >= depth:
                continue

            for neighbor in graph.get_neighbors(current):

                if neighbor not in visited:

                    if len(visited) >= limit:
                        continue

                    visited.add(neighbor)
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
