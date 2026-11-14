"""Métricas e evidências da geometria exibida para uma conexão."""

import os

from backend.services.road_matching_service import _distance_meters, _geometry_length


def quality(geometry, stop_coordinates):
    max_gap = float(os.getenv("TRANSITGRAPH_GEOMETRY_GAP_M", "120"))
    max_ratio = float(os.getenv("TRANSITGRAPH_GEOMETRY_LENGTH_RATIO", "5"))
    stops_distance = _distance_meters(*stop_coordinates) if stop_coordinates else 0
    distance = _geometry_length(geometry)
    gaps = [
        _distance_meters(a, b) for a, b in zip(geometry, geometry[1:])
    ]
    maximum_gap = max(gaps, default=0)
    issues = []
    if not distance:
        issues.append({"code": "no-usable-geometry"})
    if maximum_gap > max_gap:
        issues.append({"code": "sparse-geometry", "meters": round(maximum_gap, 1),
                       "limit_m": max_gap})
    if stops_distance >= 25 and distance > max_ratio * stops_distance:
        issues.append({"code": "long-detour", "ratio": round(distance / stops_distance, 2),
                       "limit_ratio": max_ratio})
    if geometry and stop_coordinates:
        start, end = stop_coordinates
        direct = _distance_meters(start, geometry[0]) + _distance_meters(end, geometry[-1])
        reversed_offset = _distance_meters(start, geometry[-1]) + _distance_meters(end, geometry[0])
        if direct - reversed_offset > 25:
            issues.append({"code": "endpoints-closer-in-reverse", "forward_m": round(direct, 1),
                           "reverse_m": round(reversed_offset, 1)})
    return {"distance_m": round(distance, 1), "stop_distance_m": round(stops_distance, 1),
            "max_gap_m": round(maximum_gap, 1), "issues": issues}
