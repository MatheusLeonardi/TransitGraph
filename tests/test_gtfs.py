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
