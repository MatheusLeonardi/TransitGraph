from backend.algorithms.graph import Graph


def test_graph_is_directed_and_avoids_duplicate_edges():
    graph = Graph()

    graph.add_edge("A", "B", route_id="R1")
    graph.add_edge("A", "B", route_id="R2")

    assert graph.edge_count() == 1
    assert graph.get_neighbors("A") == ["B"]
    assert graph.get_neighbors("B") == []
    assert graph.edge_routes[("A", "B")] == {"R1", "R2"}


def test_add_edge_preserves_existing_stop_metadata():
    graph = Graph()
    graph.add_stop("A", name="Parada A", latitude=-23.5, longitude=-46.6)

    graph.add_edge("A", "B")

    assert graph.get_stop("A") == {
        "stop_id": "A",
        "name": "Parada A",
        "latitude": -23.5,
        "longitude": -46.6,
    }


def test_edge_shape_keeps_one_representative_per_route():
    graph = Graph()

    graph.add_edge_shape("A", "B", "R1", "T1", "S1", 1, 2)
    graph.add_edge_shape("A", "B", "R1", "T2", "S2", 3, 4)

    assert len(graph.edge_shapes) == 1
    assert graph.edge_shapes[("A", "B", "R1")]["trip_id"] == "T1"
