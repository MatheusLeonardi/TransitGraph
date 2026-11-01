
import csv
import io
import zipfile

from collections import defaultdict
from pathlib import Path

from backend.algorithms.graph import Graph
from backend.gtfs.service_filter import get_active_service_ids


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
            "calendar.txt"
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
                active_trips[row["trip_id"]] = route_id

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
                        row["stop_id"]
                    )
                )

        # 6. Construir o grafo
        graph = Graph()

        for trip_id, stop_sequence in trip_stops.items():

            stop_sequence.sort(key=lambda item: item[0])

            ordered_stops = [
                stop_id
                for _, stop_id in stop_sequence
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
            route_id = active_trips[trip_id]

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

        # 7. Estatísticas
        stats = {
            "service_date": service_date.isoformat(),
            "active_services": len(active_services),
            "bus_routes": len(bus_routes),
            "active_trips": len(active_trips),
            "processed_trips": len(trip_stops),
            "vertices": graph.vertex_count(),
            "edges": graph.edge_count(),
            "stops_available": len(stops)
        }

        return graph, stats
