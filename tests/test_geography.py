import io
import json
from pathlib import Path
from pathlib import Path

import pytest

from backend.algorithms.bfs import bfs
from backend.algorithms.dfs import dfs
from backend.algorithms.graph import Graph
from backend.gtfs.shape_locations import locate_stops
from backend.models.database import load_graph, save_graph
from backend.services import road_matching_service as roads
from backend.services.itinerary_service import build_itinerary


def stop(latitude, longitude):
    return {"latitude": latitude, "longitude": longitude}


def test_project_stops_along_curve_and_repeated_passage():
    points = [
        (10, -23.5, -46.6), (20, -23.499, -46.601),
        (30, -23.498, -46.6), (40, -23.499, -46.599),
        (50, -23.5, -46.6), (60, -23.501, -46.6),
    ]
    stops = [stop(*points[index][1:]) for index in (0, 2, 4, 5)]
    located, method = locate_stops(points, [], [None] * len(stops), stops, 25)
    assert method == "monotone-projection"
    assert [sequence for sequence, _ in located] == [10, 30, 50, 60]


def test_interpolates_gtfs_distance_and_falls_back_when_inconsistent():
    points = [(1, -23.5, -46.6), (2, -23.5, -46.599), (3, -23.5, -46.598)]
    stops = [stop(-23.5, -46.5995), stop(-23.5, -46.598)]
    located, method = locate_stops(points, [0, 100, 200], [50, 200], stops, 25)
    assert method == "gtfs-distance"
    assert [location[0] for location in located] == [1.5, 3]
    located, method = locate_stops(points, [0, 100, 200], [200, 50], stops, 25)
    assert method == "monotone-projection"
    assert [location[0] for location in located] == pytest.approx([1.5, 3.0])


def test_missing_stop_and_repeated_coordinates_leave_gap():
    points = [(1, -23.5, -46.6), (2, -23.5, -46.6), (3, -23.5, -46.597)]
    located, _ = locate_stops(points, [], [], [stop(*points[0][1:]), None,
                                                stop(*points[-1][1:])], 25)
    assert located[1] is None
    assert located[0][0] < located[2][0]
    invalid, method = locate_stops(points[::-1], [], [], [stop(*points[0][1:])], 25)
    assert invalid == [None]
    assert method == "invalid-shape"


def test_selects_compatible_trip_occurrences_after_sqlite_round_trip(tmp_path):
    graph = Graph()
    for code, longitude in zip("ABC", [-46.6, -46.599, -46.598]):
        graph.add_stop(code, latitude=-23.5, longitude=longitude)
    for a, b in zip("AB", "BC"):
        graph.add_edge(a, b, "R")

    graph.shape_points["S"] = [
        (10, -23.5, -46.6005), (20, -23.5, -46.599),
        (30, -23.5, -46.598), (40, -23.5, -46.597)
    ]
    def reference(trip, start, end, a, b):
        return {"trip_id": trip, "shape_id": "S", "from_stop_sequence": start,
                "to_stop_sequence": end, "from_sequence": a, "to_sequence": b}
    graph.add_trip_edge("A", "B", "R", reference("opposite", 8, 9, 20, 30))
    graph.add_trip_edge("A", "B", "R", reference("correct", 1, 2, 13.333333, 20))
    graph.add_trip_edge("B", "C", "R", reference("correct", 2, 3, 20, 30))
    database = tmp_path / "occurrences.db"
    save_graph(graph, database)
    loaded = load_graph(database)
    for algorithm in (bfs, dfs):
        path = algorithm(loaded, "A", "C")["path"]
        assert path == ["A", "B", "C"]
        segments = build_itinerary(loaded, path, database)["legs"][0]["geometry_segments"]
        assert [segment["reference"]["trip_id"] for segment in segments] == ["correct"] * 2
        assert segments[0]["geometry"][0][1] == pytest.approx(-46.6)
        assert segments[0]["geometry"][-1] == segments[1]["geometry"][0]
        assert segments[0]["quality"]["issues"] == []


@pytest.mark.parametrize(("alter", "expected"), [
    ("omitted", "unmatched-tracepoint"), ("missing", "incomplete-tracepoints"),
    ("parallel", "anchor-displacement"), ("reversed", "waypoint-order"),
    ("split", "split-trace"), (None, None)
])
def test_osrm_audits_anchors_and_direction(monkeypatch, alter, expected):
    original = [[-23.5, -46.6], [-23.499, -46.5995], [-23.498, -46.6]]
    coordinates = [point[::-1] for point in original]
    shape = {"geometry": {"coordinates": coordinates}, "confidence": 0.98}
    points = [
        {"location": point.copy(), "matchings_index": 0, "waypoint_index": i}
        for i, point in enumerate(coordinates)
    ]
    response = {"code": "Ok", "matchings": [shape], "tracepoints": points}
    if alter == "omitted":
        points[1] = None
    elif alter == "missing":
        points.pop()
    elif alter == "parallel":
        points[1]["location"][1] += 0.001
    elif alter == "reversed":
        points.reverse()
    elif alter == "split":
        response["matchings"].append(shape)
    monkeypatch.setattr(roads.urllib.request, "urlopen", lambda *_a, **_kw:
                         io.StringIO(json.dumps(response)))
    result = roads._request_osrm_match(original, "https://example.invalid")
    assert result["accepted"] == (expected is None)
    assert result.get("reason") == expected


def test_osrm_does_not_replace_dense_or_insufficient_gtfs(monkeypatch, tmp_path):
    monkeypatch.setenv("TRANSITGRAPH_MAP_MATCHING", "1")
    def forbidden(*_):
        pytest.fail("Dense or two-point shape must not be sent to a car router.")
    monkeypatch.setattr(roads, "_request_osrm_match", forbidden)
    dense = [[-23.5, -46.6], [-23.5, -46.5998], [-23.5, -46.5996]]
    sparse = [[-23.5, -46.6], [-23.5, -46.597]]
    segments = [
        {"source": "gtfs", "geometry": dense, "quality": {"issues": []}},
        {"source": "gtfs", "geometry": sparse,
         "quality": {"issues": [{"code": "sparse-geometry"}]}}
    ]
    itinerary = {"legs": [{"stops": ["A", "B", "C"], "geometry_segments": segments}],
                 "uses_gtfs_shapes": True}
    result = roads.refine_itinerary_geometry(itinerary, tmp_path / "test.db")
    assert result["road_matching_status"] == "not-needed"
    assert [segment["geometry"] for segment in segments] == [dense, sparse]


@pytest.mark.parametrize(("source", "target", "start", "end"), [
    ("5614822", "5614776", 618, 621.3536),
    ("5614776", "5614702", 621.3536, 657.4444),
])
def test_cipo_projection_stays_on_outbound_shape(source, target, start, end):
    database = Path(__file__).resolve().parents[1] / "data/processed/transitgraph.db"
    graph = load_graph(database)
    segment = build_itinerary(graph, [source, target], database)["legs"][0]["geometry_segments"][0]
    reference = segment["reference"]
    assert reference["trip_id"] == "6099-10-0"
    assert reference["shape_id"] == "80239"
    assert reference["from_sequence"] == pytest.approx(start, abs=0.001)
    assert reference["to_sequence"] == pytest.approx(end, abs=0.001)
    assert segment["source"] == "gtfs"
    colocated = build_itinerary(graph, ["5614821", "5614822"], database)
    unresolved = colocated["legs"][0]["geometry_segments"][0]
    assert unresolved["reference"]["issue"] == "co-located-stops"
    assert unresolved["gtfs_geometry"] == []


def test_osrm_retries_explicit_point_limit_and_validates_resampled_trace(monkeypatch):
    import urllib.error

    geometry = [[-23.5, -46.6 + index / 10000] for index in range(17)]
    requests = []

    def fetch(request, **_kwargs):
        coordinates = [
            [float(number) for number in pair.split(",")]
            for pair in request.full_url.split("/driving/")[1].split("?")[0].split(";")
        ]
        requests.append(len(coordinates))
        if len(coordinates) > 10:
            raise urllib.error.HTTPError(request.full_url, 400, "Bad Request", {},
                                         io.BytesIO(b'{"code":"TooBig"}'))
        return io.StringIO(json.dumps({
            "code": "Ok",
            "matchings": [{"geometry": {"coordinates": coordinates}, "confidence": 0.95}],
            "tracepoints": [{"location": point, "matchings_index": 0, "waypoint_index": index}
                            for index, point in enumerate(coordinates)]
        }))

    monkeypatch.setattr(roads.urllib.request, "urlopen", fetch)
    result = roads._request_osrm_match(geometry, "https://example.invalid")
    assert requests == [17, 10]
    assert result["accepted"] is True
    assert result["geometry"][0] == geometry[0]
    assert result["geometry"][-1] == geometry[-1]
