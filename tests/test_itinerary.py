from backend.algorithms.graph import Graph
from backend.services.itinerary_service import build_itinerary, choose_routes


def create_route_graph():
    graph = Graph()
    graph.add_stop("A", latitude=-23.50, longitude=-46.60)
    graph.add_stop("B", latitude=-23.51, longitude=-46.61)
    graph.add_stop("C", latitude=-23.52, longitude=-46.62)
    graph.add_stop("D", latitude=-23.53, longitude=-46.63)
    graph.add_edge("A", "B", "R1")
    graph.add_edge("A", "B", "R2")
    graph.add_edge("B", "C", "R1")
    graph.add_edge("C", "D", "R2")
    graph.add_route("R1", "Linha 1", "Bairro - Centro")
    graph.add_route("R2", "Linha 2", "Centro - Terminal")
    return graph


def test_route_selection_minimizes_transfers():
    graph = create_route_graph()

    assert choose_routes(graph, ["A", "B", "C", "D"]) == [
        "R1", "R1", "R2"
    ]


def test_itinerary_groups_edges_by_line():
    itinerary = build_itinerary(
        create_route_graph(),
        ["A", "B", "C", "D"]
    )

    assert itinerary["transfer_count"] == 1
    assert [leg["route_id"] for leg in itinerary["legs"]] == ["R1", "R2"]
    assert itinerary["legs"][0]["stops"] == ["A", "B", "C"]


def test_itinerary_uses_shape_geometry_when_available():
    graph = create_route_graph()
    graph.shape_points["S1"] = [
        (1, -23.50, -46.60),
        (2, -23.505, -46.605),
        (3, -23.51, -46.61)
    ]
    graph.add_edge_shape("A", "B", "R1", "T1", "S1", 1, 3)

    itinerary = build_itinerary(graph, ["A", "B"])

    assert itinerary["uses_gtfs_shapes"] is True
    assert itinerary["legs"][0]["geometry"] == [
        [-23.50, -46.60],
        [-23.505, -46.605],
        [-23.51, -46.61]
    ]
