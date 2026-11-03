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
