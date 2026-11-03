import pytest

from backend.algorithms.bfs import bfs
from backend.algorithms.graph import Graph


def create_graph():
    graph = Graph()
    graph.add_edge("A", "B")
    graph.add_edge("A", "C")
    graph.add_edge("B", "D")
    graph.add_edge("C", "E")
    return graph


def test_bfs_visits_vertices_by_level():
    result = bfs(create_graph(), "A")

    assert result["visited_order"] == ["A", "B", "C", "D", "E"]
    assert result["processed_count"] == 5
    assert result["discovered_count"] == 5


def test_bfs_distinguishes_discovered_from_processed():
    result = bfs(create_graph(), "A", "B")

    assert result["visited_order"] == ["A", "B"]
    assert result["processed_count"] == 2
    assert result["discovered_count"] == 3


def test_bfs_rejects_unknown_destination():
    with pytest.raises(ValueError, match="destino"):
        bfs(create_graph(), "A", "Z")
