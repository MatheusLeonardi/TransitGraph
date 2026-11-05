
import csv
import io
import math
import statistics
import zipfile

from collections import defaultdict
from pathlib import Path

from backend.algorithms.graph import Graph
from backend.gtfs.service_filter import get_active_service_ids


MAX_SHAPE_STOP_DISTANCE_METERS = 150


def geographic_distance_meters(first, second):
    """Calcula a distância aproximada entre dois pontos geográficos."""

    latitude_1, longitude_1 = map(math.radians, first)
    latitude_2, longitude_2 = map(math.radians, second)
    latitude_delta = latitude_2 - latitude_1
    longitude_delta = longitude_2 - longitude_1
    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude_1)
        * math.cos(latitude_2)
        * math.sin(longitude_delta / 2) ** 2
    )
    return 12_742_000 * math.asin(math.sqrt(haversine))


def parse_gtfs_time(value):
    """Converte horário GTFS HH:MM:SS em segundos, incluindo horas > 24."""
    if not value:
        return None
    try:
        hours, minutes, seconds = (int(part) for part in value.split(":"))
    except (TypeError, ValueError):
        return None
    if hours < 0 or not 0 <= minutes < 60 or not 0 <= seconds < 60:
        return None
    return hours * 3600 + minutes * 60 + seconds


def is_shape_match_valid(stop, shape_point):
    return geographic_distance_meters(
        (stop["latitude"], stop["longitude"]),
        (shape_point[1], shape_point[2])
    ) <= MAX_SHAPE_STOP_DISTANCE_METERS


def match_stops_to_shape(ordered_stops, stops, shape_points):
    """Encontra a sequência monotônica global de pontos mais próxima."""

    if not shape_points or not ordered_stops:
        return []

    stop_coordinates = []

    for stop_id in ordered_stops:
        stop = stops.get(stop_id)

        if stop is None:
            return [None] * len(ordered_stops)

        stop_coordinates.append((
            stop["latitude"],
            stop["longitude"]
        ))

    point_coordinates = [
        (latitude, longitude)
        for _, latitude, longitude in shape_points
    ]
    point_count = len(point_coordinates)

    def squared_distance(stop_coordinate, point_coordinate):
        return (
            (stop_coordinate[0] - point_coordinate[0]) ** 2
            + (stop_coordinate[1] - point_coordinate[1]) ** 2
        )

    previous_costs = [
        squared_distance(stop_coordinates[0], point)
        for point in point_coordinates
    ]
    parents = [[-1] * point_count]

    for stop_coordinate in stop_coordinates[1:]:
        prefix_costs = []
        prefix_indexes = []
        best_cost = float("inf")
        best_index = 0

        for index, cost in enumerate(previous_costs):
            if cost < best_cost:
                best_cost = cost
                best_index = index

            prefix_costs.append(best_cost)
            prefix_indexes.append(best_index)

        current_costs = [
            prefix_costs[index]
            + squared_distance(stop_coordinate, point_coordinates[index])
            for index in range(point_count)
        ]
        parents.append(prefix_indexes)
        previous_costs = current_costs

    final_index = min(
        range(point_count),
        key=previous_costs.__getitem__
    )
    matched_indexes = [final_index]

    for stop_index in range(len(stop_coordinates) - 1, 0, -1):
        final_index = parents[stop_index][final_index]
        matched_indexes.append(final_index)

    matched_indexes.reverse()

    return matched_indexes


def find_gtfs_file(files, filename):
    """Localiza um arquivo pelo nome dentro do ZIP."""

    for file in files:
        if Path(file).name.lower() == filename.lower():
            return file

    return None


def read_gtfs_csv(archive, filename):
    """Lê um CSV diretamente do arquivo ZIP."""

    with archive.open(filename) as file:
        text = io.TextIOWrapper(
            file,
            encoding="utf-8-sig",
            newline=""
        )

        yield from csv.DictReader(text)


def import_gtfs(gtfs_path, service_date):
    """
    Importa os dados GTFS e constrói um grafo direcionado
    contendo somente viagens de ônibus ativas na data escolhida.

    Retorna:
        graph: grafo da rede de ônibus.
        stats: estatísticas da importação.
    """

    gtfs_path = Path(gtfs_path)

    if not gtfs_path.exists():
        raise FileNotFoundError(
            f"Arquivo GTFS não encontrado: {gtfs_path}"
        )

    with zipfile.ZipFile(gtfs_path, "r") as archive:

        files = archive.namelist()

        required_files = [
            "stops.txt",
            "routes.txt",
            "trips.txt",
            "stop_times.txt",
            "calendar.txt",
            "shapes.txt"
        ]

        file_paths = {}

        for filename in required_files:
            path = find_gtfs_file(files, filename)

            if path is None:
                raise ValueError(
                    f"Arquivo obrigatório ausente: {filename}"
                )

            file_paths[filename] = path

        # 1. Carregar paradas e coordenadas
        stops = {}

        for row in read_gtfs_csv(
            archive, file_paths["stops.txt"]
        ):
            stops[row["stop_id"]] = {
                "name": row["stop_name"],
                "latitude": float(row["stop_lat"]),
                "longitude": float(row["stop_lon"])
            }

        # 2. Identificar somente linhas de ônibus
        bus_routes = {}

        for row in read_gtfs_csv(
            archive, file_paths["routes.txt"]
        ):
            if row["route_type"] == "3":
                bus_routes[row["route_id"]] = {
                    "short_name": row["route_short_name"],
                    "long_name": row["route_long_name"]
                }

        # 3. Identificar serviços ativos na data
        calendar_rows = list(
            read_gtfs_csv(
                archive, file_paths["calendar.txt"]
            )
        )

        active_services = get_active_service_ids(
            calendar_rows,
            service_date
        )

        # 4. Selecionar viagens de ônibus ativas
        active_trips = {}

        for row in read_gtfs_csv(
            archive, file_paths["trips.txt"]
        ):
            route_id = row["route_id"]
            service_id = row["service_id"]

            if (
                route_id in bus_routes
                and service_id in active_services
            ):
                active_trips[row["trip_id"]] = {
                    "route_id": route_id,
                    "shape_id": row.get("shape_id"),
                    "headsign": row.get("trip_headsign"),
                    "direction_id": row.get("direction_id")
                }

        # 5. Agrupar horários por viagem
        trip_stops = defaultdict(list)

        for row in read_gtfs_csv(
            archive, file_paths["stop_times.txt"]
        ):
            trip_id = row["trip_id"]

            if trip_id in active_trips:
                trip_stops[trip_id].append(
                    (
                        int(row["stop_sequence"]),
                        row["stop_id"],
                        parse_gtfs_time(row.get("arrival_time")),
                        parse_gtfs_time(row.get("departure_time"))
                    )
                )

        # 6. Carregar somente shapes utilizados pelas viagens ativas
        active_shape_ids = {
            trip["shape_id"]
            for trip in active_trips.values()
            if trip.get("shape_id")
        }
        shape_points = defaultdict(list)

        for row in read_gtfs_csv(
            archive, file_paths["shapes.txt"]
        ):
            shape_id = row["shape_id"]

            if shape_id in active_shape_ids:
                shape_points[shape_id].append((
                    int(row["shape_pt_sequence"]),
                    float(row["shape_pt_lat"]),
                    float(row["shape_pt_lon"])
                ))

        for points in shape_points.values():
            points.sort(key=lambda point: point[0])

        # 7. Construir o grafo
        graph = Graph()

        for route_id, route in bus_routes.items():
            graph.add_route(
                route_id,
                short_name=route["short_name"],
                long_name=route["long_name"]
            )

        graph.shape_points = dict(shape_points)
        rejected_shape_edges = 0
        edge_time_samples = defaultdict(list)

        for trip_id, stop_sequence in trip_stops.items():

            stop_sequence.sort(key=lambda item: item[0])

            ordered_stops = [
                item[1]
                for item in stop_sequence
            ]

            # Adicionar vértices e seus dados geográficos
            for stop_id in ordered_stops:

                stop_data = stops.get(stop_id)

                if stop_data is None:
                    continue

                graph.add_stop(
                    stop_id,
                    name=stop_data["name"],
                    latitude=stop_data["latitude"],
                    longitude=stop_data["longitude"]
                )

            # Criar arestas entre paradas consecutivas
            trip = active_trips[trip_id]
            route_id = trip["route_id"]
            shape_id = trip.get("shape_id")
            points = shape_points.get(shape_id, [])
            matched_indexes = match_stops_to_shape(
                ordered_stops,
                stops,
                points
            )

            for index in range(len(ordered_stops) - 1):

                source = ordered_stops[index]
                target = ordered_stops[index + 1]

                if source not in stops or target not in stops:
                    continue

                if source == target:
                    continue

                graph.add_edge(
                    source,
                    target,
                    route_id=route_id
                )

                departure_seconds = stop_sequence[index][3]
                arrival_seconds = stop_sequence[index + 1][2]
                if (
                    departure_seconds is not None
                    and arrival_seconds is not None
                    and arrival_seconds > departure_seconds
                ):
                    edge_time_samples[(source, target)].append(
                        arrival_seconds - departure_seconds
                    )

                source_shape_index = matched_indexes[index]
                target_shape_index = matched_indexes[index + 1]

                if (
                    points
                    and source_shape_index is not None
                    and target_shape_index is not None
                ):
                    source_shape_point = points[source_shape_index]
                    target_shape_point = points[target_shape_index]
                    if (
                        not is_shape_match_valid(
                            stops[source],
                            source_shape_point
                        )
                        or not is_shape_match_valid(
                            stops[target],
                            target_shape_point
                        )
                    ):
                        rejected_shape_edges += 1
                        continue

                    graph.add_edge_shape(
                        source,
                        target,
                        route_id,
                        trip_id,
                        shape_id,
                        source_shape_point[0],
                        target_shape_point[0],
                        headsign=trip.get("headsign")
                    )

        for (source, target), samples in edge_time_samples.items():
            graph.set_edge_weight(
                source,
                target,
                statistics.median(samples)
            )

        # 8. Estatísticas
        stats = {
            "service_date": service_date.isoformat(),
            "active_services": len(active_services),
            "bus_routes": len(bus_routes),
            "active_trips": len(active_trips),
            "processed_trips": len(trip_stops),
            "vertices": graph.vertex_count(),
            "edges": graph.edge_count(),
            "stops_available": len(stops),
            "active_shapes": len(shape_points),
            "shape_points": sum(
                len(points)
                for points in shape_points.values()
            ),
            "shape_edges": len(graph.edge_shapes),
            "weighted_edges": len(graph.edge_weights),
            "rejected_shape_edges": rejected_shape_edges
        }

        graph.metadata = stats.copy()

        return graph, stats
