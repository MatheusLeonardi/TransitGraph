"""Relaciona ocorrências de parada à progressão de um shape GTFS."""

import math
from bisect import bisect_left


METERS_PER_DEGREE = 111_195


def coordinate_valid(latitude, longitude):
    return -90 <= latitude <= 90 and -180 <= longitude <= 180


def coordinate_at(points, index, fraction):
    _, latitude, longitude = points[index]
    _, next_latitude, next_longitude = points[index + 1]
    return [
        latitude + fraction * (next_latitude - latitude),
        longitude + fraction * (next_longitude - longitude)
    ]


def locate_stops(points, shape_distances, stop_distances, stops, max_offset):
    """Retorna (fração na sequência GTFS, erro em metros) por ocorrência."""
    if not stops:
        return [], "monotone-projection"
    if len(points) < 2 or any(
        a[0] >= b[0] for a, b in zip(points, points[1:])
    ) or any(not coordinate_valid(*point[1:]) for point in points):
        return [None] * len(stops), "invalid-shape"

    if (
        len(shape_distances) == len(points) and len(stop_distances) == len(stops)
        and all(value is not None for value in shape_distances + stop_distances)
        and all(a < b for a, b in zip(shape_distances, shape_distances[1:]))
        and all(a < b for a, b in zip(stop_distances, stop_distances[1:]))
        and shape_distances[0] <= stop_distances[0] <= stop_distances[-1] <= shape_distances[-1]
    ):
        locations = []
        for stop, distance in zip(stops, stop_distances):
            index = max(0, bisect_left(shape_distances, distance) - 1)
            fraction = ((distance - shape_distances[index])
                        / (shape_distances[index + 1] - shape_distances[index]))
            latitude, longitude = coordinate_at(points, index, fraction)
            error = offset_meters(stop, latitude, longitude) if stop else math.inf
            locations.append((sequence_at(points, index, fraction), error))
        if all(error <= max_offset for _, error in locations):
            return locations, "gtfs-distance"

    # Coordenadas idênticas em paradas consecutivas podem designar a
    # mesma posição física. Não force uma segunda passagem pelo local
    # sem uma distância GTFS que comprove progressão entre elas.
    groups = []
    occurrences = []
    for stop in stops:
        coordinates = (stop["latitude"], stop["longitude"]) if stop else None
        if coordinates is None or not groups or coordinates != groups[-1][0]:
            groups.append((coordinates, stop))
        occurrences.append(len(groups) - 1)
    locations = project_stops(points, [stop for _, stop in groups], max_offset)
    return [locations[index] for index in occurrences], "monotone-projection"


def offset_meters(stop, latitude, longitude):
    scale = METERS_PER_DEGREE * math.cos(math.radians(stop["latitude"]))
    return math.hypot(
        (latitude - stop["latitude"]) * METERS_PER_DEGREE,
        (longitude - stop["longitude"]) * scale,
    )


def sequence_at(points, index, fraction):
    return points[index][0] + fraction * (points[index + 1][0] - points[index][0])


def projection_candidates(points, stop, max_offset):
    if not stop or not coordinate_valid(stop["latitude"], stop["longitude"]):
        return []
    scale = METERS_PER_DEGREE * math.cos(math.radians(stop["latitude"]))
    candidates = {}
    for index, (a, b) in enumerate(zip(points, points[1:])):
        dy = (b[1] - a[1]) * METERS_PER_DEGREE
        dx = (b[2] - a[2]) * scale
        length = dy * dy + dx * dx
        if not length:
            continue
        y = (stop["latitude"] - a[1]) * METERS_PER_DEGREE
        x = (stop["longitude"] - a[2]) * scale
        fraction = min(1, max(0, (y * dy + x * dx) / length))
        error = math.hypot(y - fraction * dy, x - fraction * dx)
        if error <= max_offset:
            position = sequence_at(points, index, fraction)
            candidates[position] = min(error, candidates.get(position, math.inf))
    return sorted(candidates.items())


def project_stops(points, stops, max_offset):
    # Cada camada tem candidatos na ordem do shape. O mínimo de prefixo compara
    # apenas posições anteriores, inclusive quando a mesma parada reaparece.
    result = [None] * len(stops)
    layers = []

    def finish_run():
        if layers:
            best = min(range(len(layers[-1])), key=lambda i: layers[-1][i][1])
            for layer in reversed(layers):
                index, _, candidate, parent = layer[best]
                result[index] = candidates_by_stop[index][candidate]
                best = parent
            layers.clear()

    candidates_by_stop = [
        projection_candidates(points, stop, max_offset) for stop in stops
    ]
    for index, candidates in enumerate(candidates_by_stop):
        if not candidates:
            finish_run()
            continue
        if not layers:
            layers.append([(index, error ** 2, i, None) for i, (_, error) in enumerate(candidates)])
            continue

        previous = layers[-1]
        best = None
        cursor = 0
        layer = []
        for i, (position, error) in enumerate(candidates):
            while cursor < len(previous):
                previous_index, cost, previous_candidate, _ = previous[cursor]
                if candidates_by_stop[previous_index][previous_candidate][0] >= position:
                    break
                if best is None or cost < previous[best][1]:
                    best = cursor
                cursor += 1
            if best is not None:
                layer.append((index, previous[best][1] + error ** 2, i, best))
        if not layer:
            # A ocorrência atual não admite progresso dentro do limite. Deixa
            # uma lacuna, impedindo a união entre os dois lados do conflito.
            finish_run()
        else:
            layers.append(layer)

    finish_run()
    return result
