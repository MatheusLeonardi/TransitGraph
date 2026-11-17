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
    assert "reachability" not in data["dfs"]
    assert "discovery_tree" not in data["dfs"]


def test_compare_endpoint_requires_both_stops():
    response = create_client().post(
        "/api/algorithms/compare",
        json={"origin": "A"}
    )

    assert response.status_code == 400
    assert "origem e destino" in response.get_json()["error"]


def test_dijkstra_endpoint_reports_search_metrics():
    response = create_client().post(
        "/api/algorithms/dijkstra",
        json={"origin": "A", "destination": "D"}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["path"] == ["A", "C", "D"]
    assert data["distance"] == 2
    assert data["processed_count"] == 4
    assert data["discovered_count"] == 5
    assert data["edges_examined"] == 4
    assert data["execution_time_ms"] >= 0


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
    assert len(result["reachability"]["reachable"]) == 3
    assert result["reachability"]["unreachable"] == []
    assert result["discovery_tree"]["depth_limit"] is None
    assert result["discovery_tree"]["edge_count"] == result["discovery_tree"]["total_edges"] == 2
    assert client.post("/api/algorithms/bfs?instance=local",
                       json={"origin": root, "destination": "D"}).status_code == 400
    assert client.post("/api/algorithms/bfs",
                       json={"origin": root, "destination": "D"}).get_json()["distance"] == 3


def test_dfs_reports_full_counts_when_orders_are_truncated():
    graph = Graph()
    stops = list(map(str, range(240)))
    for source, target in zip(stops, stops[1:]):
        graph.add_edge(source, target)
    graph.add_stop("0", latitude=-23.5, longitude=-46.6)
    graph.add_stop("239", latitude=-23.6, longitude=-46.7)
    graph.add_stop("unreachable", latitude=-23.7, longitude=-46.8)
    graph.add_edge("0", "late-branch")
    graph.add_edge("unreachable", "0")
    client = create_app(graph).test_client()
    response = client.post(
        "/api/algorithms/dfs", json={"origin": "0"}
    )
    data = response.get_json()
    assert data["visited_order"] == stops[:200]
    assert data["finish_order"] == stops[::-1][:200]
    assert data["visited_order_total"] == data["finish_order_total"] == 241
    assert data["visited_order_truncated"] is True
    assert data["network_size"] == 242
    assert data["discovered_count"] == 241
    assert data["path"] is None
    assert data["reachability"] == {
        "origin": [-23.5, -46.6],
        "reachable": [[-23.5, -46.6], [-23.6, -46.7]],
        "unreachable": [[-23.7, -46.8]]
    }
    tree = data["discovery_tree"]
    assert tree["total_edges"] == 240
    assert tree["depth_limit"] == 5
    assert [
        element["data"] for element in tree["elements"] if "source" in element["data"]
    ] == [
        *({"source": stops[i], "target": stops[i + 1]} for i in range(5)),
        {"source": "0", "target": "late-branch"}
    ]

    directed_result = client.post(
        "/api/algorithms/dfs", json={"origin": "0", "destination": "239"}
    ).get_json()
    assert directed_result["distance"] == 239
    assert "reachability" not in directed_result
    assert "discovery_tree" not in directed_result


def test_dfs_tree_uses_discovery_predecessors_instead_of_other_graph_edges():
    graph = Graph()
    for source, target in [
        ("A", "B"), ("A", "C"), ("A", "E"), ("B", "D"), ("D", "C"),
        ("C", "A"), ("E", "C"), ("E", "F")
    ]:
        graph.add_edge(source, target)
    client = create_app(graph).test_client()
    data = client.post("/api/algorithms/dfs", json={"origin": "A"}).get_json()
    tree = data["discovery_tree"]
    assert tree["edge_count"] == tree["total_edges"] == data["discovered_count"] - 1
    assert data["edges_examined"] > tree["edge_count"]
    predecessors = {}
    for element in tree["elements"]:
        fields = element["data"]
        if "source" in fields:
            predecessors[fields["target"]] = fields["source"]

    assert predecessors == {"B": "A", "D": "B", "C": "D", "E": "A", "F": "E"}
    for target, predecessor in predecessors.items():
        result = client.post(
            "/api/algorithms/dfs", json={"origin": "A", "destination": target}
        ).get_json()
        assert result["path"][-2:] == [predecessor, target]


def test_dfs_tree_limits_wide_trees():
    graph = Graph()
    for number in range(100):
        graph.add_edge("root", f"leaf-{number}")
    client = create_app(graph).test_client()
    tree = client.post("/api/algorithms/dfs", json={"origin": "root"}).get_json()["discovery_tree"]
    assert tree["edge_count"] == tree["edge_limit"] == 80
    assert tree["total_edges"] == 100
    assert len(tree["elements"]) == 161
    assert tree["elements"][0]["data"]["isOrigin"] is True
