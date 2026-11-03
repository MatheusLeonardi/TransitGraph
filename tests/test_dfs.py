import pytest

from backend.algorithms.dfs import dfs
from backend.algorithms.graph import Graph


def create_graph():
    graph = Graph()
    graph.add_edge("A", "B")
    graph.add_edge("A", "C")
    graph.add_edge("B", "X")
    graph.add_edge("X", "D")
    graph.add_edge("C", "D")
    return graph


def test_dfs_follows_a_branch_before_backtracking():
    result = dfs(create_graph(), "A")

    assert result["visited_order"] == ["A", "B", "X", "D", "C"]


def test_dfs_returns_a_path_without_claiming_it_is_shortest():
    result = dfs(create_graph(), "A", "D")

    assert result["found"] is True
    assert result["path"] == ["A", "B", "X", "D"]
    assert result["distance"] == 3


def test_dfs_rejects_unknown_origin():
    with pytest.raises(ValueError, match="origem"):
        dfs(create_graph(), "Z")
