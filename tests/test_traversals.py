import pytest

from backend.algorithms.bfs import bfs
from backend.algorithms.dfs import dfs
from backend.algorithms.graph import Graph


@pytest.mark.parametrize("search", [bfs, dfs])
def test_single_stop_and_same_origin_destination(search):
    graph = Graph()
    graph.add_stop("A")
    complete = search(graph, "A")
    assert complete["visited_order"] == ["A"]
    assert complete["edges_examined"] == 0
    assert complete["found"] is None
    result = search(graph, "A", "A")
    assert result["found"] is True
    assert result["path"] == ["A"]
    assert result["distance"] == 0
    assert result["discovered_count"] == 1


@pytest.mark.parametrize("search", [bfs, dfs])
def test_linear_directed_graph_and_unreachable_destination(search):
    graph = Graph()
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    graph.add_stop("Z")
    assert search(graph, "A", "C")["path"] == ["A", "B", "C"]
    for start, goal, order in (("C", "A", ["C"]), ("A", "Z", ["A", "B", "C"])):
        result = search(graph, start, goal)
        assert result["found"] is False
        assert result["path"] is None
        assert result["distance"] is None
        assert result["visited_order"] == order


@pytest.mark.parametrize(("search", "expected"), [
    (bfs, ["A", "B", "C", "D", "E", "A1"]),
    (dfs, ["A", "B", "D", "A1", "C", "E"]),
])
def test_cyclic_branching_graph(search, expected):
    graph = Graph()
    for edge in [("A", "B"), ("A", "C"), ("B", "D"), ("D", "A"),
                 ("D", "A1"), ("A1", "C"), ("C", "E"), ("E", "B"), ("X", "Y")]:
        graph.add_edge(*edge)

    result = search(graph, "A")
    assert result["visited_order"] == expected
    assert set(result["visited_order"]) == {"A", "B", "C", "D", "E", "A1"}
    assert result["discovered_count"] == 6
    assert result["edges_examined"] == 8


@pytest.mark.parametrize(("targets", "first"), [(("B", "C"), "B"), (("C", "B"), "C")])
def test_adjacency_order_breaks_equal_length_ties(targets, first):
    graph = Graph()
    for target in targets:
        graph.add_edge("A", target)
        graph.add_edge(target, "D")
    for search in (bfs, dfs):
        assert search(graph, "A", "D")["path"] == ["A", first, "D"]


def test_bfs_returns_shortest_path_even_if_long_branch_was_inserted_first():
    graph = Graph()
    for edge in [("A", "B"), ("A", "C"), ("B", "D"), ("D", "E"), ("C", "E")]:
        graph.add_edge(*edge)
    result = bfs(graph, "A", "E")
    assert result["path"] == ["A", "C", "E"]
    assert result["distance"] == 2
    assert all(target in graph.adjacency[source]
               for source, target in zip(result["path"], result["path"][1:]))


def test_dfs_reaches_later_sibling_through_first_branch_and_records_returns():
    graph = Graph()
    for edge in [("A", "B"), ("A", "C"), ("B", "C"), ("C", "D"), ("B", "E")]:
        graph.add_edge(*edge)
    result = dfs(graph, "A")
    assert result["visited_order"] == ["A", "B", "C", "D", "E"]
    assert result["finish_order"] == ["D", "C", "E", "B", "A"]
    targeted = dfs(graph, "A", "C")
    assert targeted["path"] == ["A", "B", "C"]
    assert targeted["finish_order"] == []
    assert targeted["discovered_count"] == 3
    assert targeted["edges_examined"] == 2


def test_dfs_can_follow_a_deep_path_without_recursion():
    graph = Graph()
    stops = list(map(str, range(5000)))
    for source, target in zip(stops, stops[1:]):
        graph.add_edge(source, target)
    result = dfs(graph, stops[0])
    assert result["visited_order"] == stops
    assert result["finish_order"] == stops[::-1]
    assert dfs(graph, stops[0], stops[-1])["path"] == stops
