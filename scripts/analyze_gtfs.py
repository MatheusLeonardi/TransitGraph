
import csv
import io
import zipfile
from pathlib import Path
from collections import Counter

PROJECT_DIR = Path(__file__).resolve().parent.parent
GTFS_FILE = PROJECT_DIR / "data" / "raw" / "_sptrans_gtfs.zip"


def read_csv(archive, filename):
    """Lê um CSV diretamente de dentro do ZIP."""
    with archive.open(filename) as file:
        text = io.TextIOWrapper(file, encoding="utf-8-sig", newline="")
        yield from csv.DictReader(text)


def find_file(files, filename):
    """Localiza um arquivo pelo nome, mesmo dentro de subpastas."""
    for file in files:
        if Path(file).name.lower() == filename.lower():
            return file
    return None


def analyze():
    if not GTFS_FILE.exists():
        print(f"Arquivo não encontrado: {GTFS_FILE}")
        return

    with zipfile.ZipFile(GTFS_FILE, "r") as archive:
        files = archive.namelist()

        def rows(filename):
            path = find_file(files, filename)
            return read_csv(archive, path) if path else []

        print("=" * 60)
        print("TRANSITGRAPH - ANÁLISE DO GTFS")
        print("=" * 60)

        # 1. Paradas
        stops = {}
        for row in rows("stops.txt"):
            stops[row["stop_id"]] = row

        print(f"\nParadas cadastradas: {len(stops)}")

        # 2. Linhas
        routes = {}
        route_types = Counter()

        for row in rows("routes.txt"):
            routes[row["route_id"]] = row
            route_types[row["route_type"]] += 1

        bus_routes = {
            route_id
            for route_id, row in routes.items()
            if row["route_type"] == "3"
        }

        print(f"Linhas cadastradas: {len(routes)}")
        print(f"Linhas de ônibus: {len(bus_routes)}")
        print(f"Tipos de transporte: {dict(route_types)}")

        # 3. Viagens
        trips = {}
        bus_trips = set()
        bus_services = set()

        for row in rows("trips.txt"):
            trip_id = row["trip_id"]
            trips[trip_id] = row

            if row["route_id"] in bus_routes:
                bus_trips.add(trip_id)
                bus_services.add(row["service_id"])

        print(f"\nViagens cadastradas: {len(trips)}")
        print(f"Viagens de ônibus: {len(bus_trips)}")
        print(f"Serviços utilizados pelos ônibus: {len(bus_services)}")

        # 4. Calendário
        calendar_services = set()

        for row in rows("calendar.txt"):
            calendar_services.add(row["service_id"])

        missing_services = bus_services - calendar_services

        print(f"\nServiços no calendário: {len(calendar_services)}")
        print(f"Serviços de ônibus sem calendário: {len(missing_services)}")

        if missing_services:
            print("IDs sem calendário:", sorted(missing_services)[:20])

        # 5. Horários e referências às paradas
        total_stop_times = 0
        bus_stop_times = 0
        trip_ids_in_stop_times = set()
        bus_stop_ids = set()
        missing_trip_ids = set()

        for row in rows("stop_times.txt"):
            total_stop_times += 1
            trip_id = row["trip_id"]
            trip_ids_in_stop_times.add(trip_id)

            if trip_id in bus_trips:
                bus_stop_times += 1
                bus_stop_ids.add(row["stop_id"])

            if trip_id not in trips:
                missing_trip_ids.add(trip_id)

        missing_stops = bus_stop_ids - set(stops)

        print(f"\nRegistros em stop_times: {total_stop_times}")
        print(f"Registros de ônibus em stop_times: {bus_stop_times}")
        print(f"Paradas utilizadas por ônibus: {len(bus_stop_ids)}")
        print(f"Paradas de ônibus ausentes em stops.txt: {len(missing_stops)}")
        print(f"Viagens ausentes em trips.txt: {len(missing_trip_ids)}")

        if missing_stops:
            print("IDs de paradas ausentes:", sorted(missing_stops)[:20])

        if missing_trip_ids:
            print("IDs de viagens ausentes:", sorted(missing_trip_ids)[:20])

        # 6. Resumo
        print("\n" + "=" * 60)
        print("RESUMO")
        print("=" * 60)

        print(f"Paradas totais: {len(stops)}")
        print(f"Paradas utilizadas por ônibus: {len(bus_stop_ids)}")
        print(f"Linhas de ônibus: {len(bus_routes)}")
        print(f"Viagens de ônibus: {len(bus_trips)}")
        print(f"Registros de horários de ônibus: {bus_stop_times}")

        if not missing_stops and not missing_trip_ids and not missing_services:
            print("\nReferências básicas: OK")
        else:
            print("\nATENÇÃO: foram encontradas referências inconsistentes.")


if __name__ == "__main__":
    analyze()
