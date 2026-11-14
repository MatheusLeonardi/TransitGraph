from backend.algorithms.graph import Graph
from backend.app import create_app


def create_client():
    graph = Graph()
    graph.add_edge("A", "B")
    graph.add_edge("A", "C")
    graph.add_edge("B", "X")
    graph.add_edge("X", "D")
    graph.add_edge("C", "D")

    app = create_app(graph)
    app.config.update(TESTING=True)
    return app.test_client()


def test_compare_endpoint_exposes_algorithm_differences():
    response = create_client().post(
        "/api/algorithms/compare",
        json={"origin": "A", "destination": "D"}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["bfs"]["path"] == ["A", "C", "D"]
    assert data["dfs"]["path"] == ["A", "B", "X", "D"]
    assert data["bfs"]["distance"] < data["dfs"]["distance"]
    assert data["bfs"]["visited_order"]
    assert data["dfs"]["visited_order"]


def test_compare_endpoint_requires_both_stops():
    response = create_client().post(
        "/api/algorithms/compare",
        json={"origin": "A"}
    )

    assert response.status_code == 400
    assert "origem e destino" in response.get_json()["error"]


def test_invalid_json_returns_bad_request():
    client = create_client()
    for algorithm in ("bfs", "dfs", "dijkstra", "compare"):
        for payload in (["A", "D"], {"origin": ["A"]}, {"origin": True}):
            response = client.post(f"/api/algorithms/{algorithm}", json=payload)
            assert response.status_code == 400
            assert response.get_json()["error"]


def test_instance_bounds_applied_to_search_traversals_map_and_connectivity():
    graph = Graph()
    root = "480012875"
    for origin, destination, line in [
        (root, "B", "2025-10"), ("B", "C", "2025-10"), ("C", "D", "other"),
        ("D", "E", "172K-10")
    ]:
        graph.add_stop(origin, latitude=-23, longitude=-46)
        graph.add_stop(destination, latitude=-23, longitude=-46)
        graph.add_edge(origin, destination, line)
    app = create_app(graph)
    app.config.update(TESTING=True)
    client = app.test_client()

    assert client.get("/?instance=local").status_code == 200
    assert client.get("/api/stats").get_json()["vertices"] == 5
    assert client.get("/api/stats?instance=local").get_json()["vertices"] == 3
    assert client.get("/api/stats?instance=lines").get_json()["edges"] == 3
    assert client.get("/api/stats?instance=unknown").status_code == 400
    assert client.get("/api/stops?instance=local&q=D").get_json()["count"] == 0
    assert client.get("/api/stops/D?instance=local").status_code == 404
    assert client.get(
        "/api/stops/map?instance=local&south=-24&north=-22&west=-47&east=-45"
    ).get_json()["count"] == 3
    assert client.get(
        "/api/graph/neighborhood?instance=local&depth=10&stop_id=480012875"
    ).get_json()["node_count"] == 3
    assert client.get("/api/connectivity?instance=lines").get_json()["component_count"] == 2

    result = client.post("/api/algorithms/dfs?instance=local", json={"origin": root}).get_json()
    assert result["visited_order"] == [root, "B", "C"]
    assert result["finish_order"] == ["C", "B", root]
    assert result["network_size"] == 3
    assert client.post("/api/algorithms/bfs?instance=local",
                       json={"origin": root, "destination": "D"}).status_code == 400
    assert client.post("/api/algorithms/bfs",
                       json={"origin": root, "destination": "D"}).get_json()["distance"] == 3


def test_dfs_reports_full_counts_when_orders_are_truncated():
    graph = Graph()
    stops = list(map(str, range(240)))
    for source, target in zip(stops, stops[1:]):
        graph.add_edge(source, target)
    response = create_app(graph).test_client().post(
        "/api/algorithms/dfs", json={"origin": "0"}
    )
    data = response.get_json()
    assert data["visited_order"] == stops[:200]
    assert data["finish_order"] == stops[::-1][:200]
    assert data["visited_order_total"] == data["finish_order_total"] == 240
    assert data["visited_order_truncated"] is True
    assert data["network_size"] == data["discovered_count"] == 240
