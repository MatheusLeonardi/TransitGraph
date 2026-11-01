from backend.algorithms.graph import Graph
from backend.algorithms.bfs import bfs
from backend.algorithms.dfs import dfs
from backend.algorithms.connectivity import (
    reachable_stops,
    weakly_connected_components
)


def create_test_graph():

    graph = Graph()

    graph.add_edge("A", "B")
    graph.add_edge("A", "C")
    graph.add_edge("B", "D")
    graph.add_edge("C", "E")
    graph.add_edge("D", "F")
    graph.add_edge("E", "F")

    return graph


def test_bfs():

    graph = create_test_graph()

    result = bfs(graph, "A", "F")

    assert result["found"] is True
    assert result["distance"] == 3

    assert result["path"] in [
        ["A", "B", "D", "F"],
        ["A", "C", "E", "F"]
    ]


def test_dfs():

    graph = create_test_graph()

    result = dfs(graph, "A")

    assert result["visited_count"] == 6

    assert set(result["reachable_stops"]) == {
        "A", "B", "C", "D", "E", "F"
    }


def test_no_path():

    graph = create_test_graph()

    graph.add_stop("Z")

    result = bfs(graph, "A", "Z")

    assert result["found"] is False
    assert result["path"] is None


def test_isolated_stop():

    graph = Graph()

    graph.add_stop("A")

    result = dfs(graph, "A")

    assert result["visited_count"] == 1


def test_reachable_stops():
    graph = create_test_graph()

    result = reachable_stops(graph, "A")

    assert set(result) == {"A", "B", "C", "D", "E", "F"}


def test_weakly_connected_components():
    graph = create_test_graph()

    graph.add_edge("X", "Y")
    graph.add_stop("Z")

    result = weakly_connected_components(graph)

    assert result["component_count"] == 3
    assert result["largest_component_size"] == 6
    assert "Z" in result["isolated_stops"]


def test_multiple_connected_components():
    graph = Graph()

    graph.add_edge("A", "B")
    graph.add_edge("C", "D")
    graph.add_edge("E", "F")

    result = weakly_connected_components(graph)

    assert result["component_count"] == 3
