import io
import json
import urllib.error
import sqlite3

from backend.services import road_matching_service


def test_coherence_accepts_a_close_directional_match():
    original = [
        [-23.5297, -46.5516],
        [-23.5290, -46.5525],
        [-23.5266, -46.5517]
    ]
    matched = [
        [-23.52969, -46.55159],
        [-23.5294, -46.5520],
        [-23.5290, -46.55248],
        [-23.5278, -46.5519],
        [-23.52659, -46.55172]
    ]

    assert road_matching_service.is_coherent_match(
        original, matched, confidence=0.95
    ) is True


def test_coherence_rejects_low_confidence_or_distant_results():
    original = [[-23.53, -46.55], [-23.52, -46.54]]
    distant = [[-23.53, -46.55], [-23.50, -46.50]]

    assert road_matching_service.is_coherent_match(
        original, original, confidence=0.1
    ) is False
    assert road_matching_service.is_coherent_match(
        original, distant, confidence=0.99
    ) is False


def test_refinement_is_cached(monkeypatch, tmp_path):
    database = tmp_path / "cache.db"
    itinerary = {
        "uses_gtfs_shapes": True,
        "legs": [{
            "stops": ["A", "B"],
            "geometry": [
                [-23.5297, -46.5516],
                [-23.5280, -46.5520],
                [-23.5266, -46.5517]
            ]
        }]
    }
    matched = [
        [-23.5297, -46.5516],
        [-23.5288, -46.5521],
        [-23.5276, -46.5519],
        [-23.5266, -46.5517]
    ]

    def fake_match(geometry, osrm_url):
        return {
            "accepted": True,
            "geometry": matched,
            "confidence": 0.98,
            "matched_distance": 400,
            "source": "osrm"
        }

    monkeypatch.setattr(
        road_matching_service,
        "_request_osrm_match",
        fake_match
    )
    first = road_matching_service.refine_itinerary_geometry(
        itinerary,
        database
    )

    assert first["uses_road_matching"] is True
    assert first["legs"][0]["geometry_source"] == "osrm"

    monkeypatch.setattr(
        road_matching_service,
        "_request_osrm_match",
        lambda geometry, osrm_url: None
    )
    second = road_matching_service.refine_itinerary_geometry(
        {
            "uses_gtfs_shapes": True,
            "legs": [{
                "stops": ["A", "B"],
                "geometry": [
                    [-23.5297, -46.5516],
                    [-23.5280, -46.5520],
                    [-23.5266, -46.5517]
                ]
            }]
        },
        database
    )

    assert second["legs"][0]["geometry_source"] == "osrm-cache"

    cache_database = tmp_path / "cache_road_cache.db"
    assert cache_database.exists()

    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert "road_geometry_cache" not in tables
    assert "road_geometry_rejections" not in tables


def test_rejected_match_keeps_gtfs_fallback(monkeypatch, tmp_path):
    database = tmp_path / "rejection.db"
    itinerary = {
        "uses_gtfs_shapes": True,
        "legs": [{
            "stops": ["A", "B"],
            "geometry": [
                [-23.5297, -46.5516],
                [-23.5280, -46.5520],
                [-23.5266, -46.5517]
            ]
        }]
    }

    monkeypatch.setattr(
        road_matching_service,
        "_request_osrm_match",
        lambda geometry, osrm_url: {
            "accepted": False,
            "reason": "incoherent-match"
        }
    )

    result = road_matching_service.refine_itinerary_geometry(
        itinerary,
        database
    )

    assert result["uses_road_matching"] is False
    assert result["road_matching_status"] == "fallback-gtfs"
    assert result["legs"][0]["geometry_source"] == "gtfs-coherence-fallback"


def test_refinement_preserves_gaps_and_updates_continuous_segments(monkeypatch, tmp_path):
    database = tmp_path / "graph.db"
    geometry = [[-23.5297, -46.5516], [-23.5266, -46.5517]]
    matched = [geometry[0], [-23.5280, -46.5515], geometry[-1]]
    calls = []

    def fake_match(points, _url):
        calls.append(points)
        return {"accepted": True, "source": "osrm", "geometry": matched,
                "confidence": 0.98, "matched_distance": 350}

    monkeypatch.setenv("TRANSITGRAPH_MAP_MATCHING", "1")
    monkeypatch.setattr(road_matching_service, "_request_osrm_match", fake_match)
    gtfs = {"source": "gtfs", "geometry": geometry}
    approximate = {"source": "approximate", "geometry": geometry[::-1]}
    mixed = {"geometry": geometry, "geometry_segments": [gtfs, approximate]}
    continuous = {"geometry": geometry, "geometry_segments": [gtfs]}
    result = road_matching_service.refine_itinerary_geometry(
        {"uses_gtfs_shapes": True, "legs": [mixed, continuous]}, database
    )

    assert calls == [geometry]
    assert mixed["geometry_segments"][0]["source"] == "osrm"
    assert mixed["geometry_segments"][0]["geometry"] == matched
    assert mixed["geometry_segments"][1]["geometry"] == geometry[::-1]
    assert continuous["geometry_segments"][0]["source"] == "osrm"
    assert continuous["geometry_segments"][0]["geometry"] == matched
    assert result["uses_road_matching"] is True


def test_coherence_accepts_road_points_between_sparse_gtfs_samples():
    original = [[-23.5, -46.6], [-23.5, -46.594]]
    matched = [original[0], [-23.50025, -46.597], original[-1]]
    assert road_matching_service.is_coherent_match(original, matched, 0.95)


def test_coherence_rejects_shortcut_ignoring_original_curve():
    original = [[-23.5, -46.6], [-23.5012, -46.597], [-23.5, -46.594]]
    shortcut = [original[0], original[-1]]
    assert not road_matching_service.is_coherent_match(original, shortcut, 0.95)


def test_control_points_keep_both_ends_and_cover_the_trace():
    geometry = [[-23.5, -46.6 + i / 10000] for i in range(101)]
    points = road_matching_service._control_points(geometry)
    assert len(points) == road_matching_service.MAX_CONTROL_POINTS
    assert points[0] == geometry[0]
    assert points[-1] == geometry[-1]
    assert geometry[50][1] - 0.0002 <= points[len(points) // 2][1] <= geometry[50][1] + 0.0002


def test_cache_separates_osrm_servers():
    geometry = [[-23.5, -46.6], [-23.5, -46.594]]
    assert road_matching_service._cache_key(geometry, "https://a.example") != (
        road_matching_service._cache_key(geometry, "https://b.example")
    )
