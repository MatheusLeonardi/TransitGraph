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
