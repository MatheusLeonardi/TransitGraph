import sqlite3

from backend.algorithms.graph import Graph
from backend.models.database import load_graph, save_graph
from backend.services.itinerary_service import build_itinerary


def test_database_preserves_routes_and_shapes(tmp_path):
    graph = Graph()
    graph.add_stop("A", latitude=-23.50, longitude=-46.60)
    graph.add_stop("B", latitude=-23.51, longitude=-46.61)
    graph.add_route("R1", "Linha 1", "Bairro - Centro")
    graph.add_edge("A", "B", "R1")
    graph.shape_points["S1"] = [
        (1, -23.50, -46.60),
        (2, -23.51, -46.61)
    ]
    graph.add_edge_shape("A", "B", "R1", "T1", "S1", 1, 2)
    database = tmp_path / "graph.db"

    save_graph(graph, database, metadata={"service_date": "2026-11-01"})
    loaded = load_graph(database)
    itinerary = build_itinerary(loaded, ["A", "B"], database)

    assert loaded.routes["R1"]["short_name"] == "Linha 1"
    assert loaded.metadata["service_date"] == "2026-11-01"
    assert itinerary["uses_gtfs_shapes"] is True
    assert itinerary["legs"][0]["geometry"][-1] == [-23.51, -46.61]

    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM shapes"
        ).fetchone()[0] == 1
