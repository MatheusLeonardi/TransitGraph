from datetime import date

from backend.gtfs.service_filter import get_active_service_ids
from backend.gtfs.importer import (
    is_shape_match_valid,
    match_stops_to_shape
)


def calendar_row(service_id, **days):
    row = {
        "service_id": service_id,
        "monday": "0",
        "tuesday": "0",
        "wednesday": "0",
        "thursday": "0",
        "friday": "0",
        "saturday": "0",
        "sunday": "0",
        "start_date": "20260101",
        "end_date": "20261231"
    }
    row.update(days)
    return row


def test_service_filter_uses_the_correct_weekday():
    rows = [
        calendar_row("WEEKDAY", monday="1"),
        calendar_row("SUNDAY", sunday="1")
    ]

    assert get_active_service_ids(rows, date(2026, 11, 2)) == {"WEEKDAY"}
    assert get_active_service_ids(rows, date(2026, 11, 1)) == {"SUNDAY"}


def test_service_filter_respects_validity_period():
    rows = [calendar_row("OLD", monday="1", end_date="20261001")]

    assert get_active_service_ids(rows, date(2026, 11, 2)) == set()


def test_stop_shape_matching_preserves_travel_order():
    stops = {
        "A": {"latitude": 0.0, "longitude": 0.0},
        "B": {"latitude": 0.0, "longitude": 2.0}
    }
    shape = [
        (1, 0.0, 0.0),
        (2, 0.0, 1.0),
        (3, 0.0, 2.0)
    ]

    assert match_stops_to_shape(["A", "B"], stops, shape) == [0, 2]


def test_stop_shape_matching_avoids_greedy_loop_error():
    stops = {
        "A": {"latitude": 0.0, "longitude": 0.1},
        "B": {"latitude": 0.0, "longitude": 10.0}
    }
    shape = [
        (1, 0.0, 0.0),
        (2, 0.0, 10.0),
        (3, 0.0, 0.0)
    ]

    assert match_stops_to_shape(["A", "B"], stops, shape) == [0, 1]


def test_shape_match_rejects_a_distant_point():
    stop = {"latitude": -23.55, "longitude": -46.63}

    assert is_shape_match_valid(stop, (1, -23.5501, -46.6301)) is True
    assert is_shape_match_valid(stop, (2, -23.60, -46.70)) is False


def test_trip_without_shape_preserves_edges_and_weight(tmp_path):
    from zipfile import ZipFile

    from backend.gtfs.importer import import_gtfs

    feed = tmp_path / "feed.zip"
    with ZipFile(feed, "w") as archive:
        archive.writestr("stops.txt", "stop_id,stop_name,stop_lat,stop_lon\nA,Alpha,0,0\nB,Beta,0,1\n")
        archive.writestr("routes.txt", "route_id,route_type,route_short_name,route_long_name\nR,3,R,Route\n")
        archive.writestr("calendar.txt", "service_id,sunday,start_date,end_date\nS,1,20260101,20261231\n")
        archive.writestr("trips.txt", "route_id,service_id,trip_id,shape_id\nR,S,T,\n")
        archive.writestr("shapes.txt", "shape_id,shape_pt_sequence,shape_pt_lat,shape_pt_lon\n")
        archive.writestr("stop_times.txt", "trip_id,stop_id,stop_sequence,arrival_time,departure_time\n"
                         "T,A,1,08:00:00,08:00:00\nT,B,2,08:01:00,08:01:00\n")

    graph, stats = import_gtfs(feed, date(2026, 11, 1))
    assert graph.get_neighbors("A") == ["B"]
    assert graph.edge_weights["A", "B"] == 60
    assert stats["shape_edges"] == 0
