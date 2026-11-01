
import csv
import zipfile
from pathlib import Path

# Caminho do projeto
PROJECT_DIR = Path(__file__).resolve().parent.parent

# Arquivo GTFS
GTFS_FILE = PROJECT_DIR / "data" / "raw" / "_sptrans_gtfs.zip"

# Arquivos mais importantes para o TransitGraph
IMPORTANT_FILES = [
    "stops.txt",
    "routes.txt",
    "trips.txt",
    "stop_times.txt",
    "calendar.txt",
    "calendar_dates.txt"
]


def inspect_gtfs():
    if not GTFS_FILE.exists():
        print(f"ERRO: arquivo não encontrado: {GTFS_FILE}")
        return

    print("=" * 60)
    print("TRANSITGRAPH - INSPEÇÃO DO GTFS")
    print("=" * 60)

    with zipfile.ZipFile(GTFS_FILE, "r") as archive:

        available_files = archive.namelist()

        print("\nARQUIVOS ENCONTRADOS NO ZIP:")
        for filename in available_files:
            print(f"- {filename}")

        print("\n" + "=" * 60)
        print("ANÁLISE DOS ARQUIVOS PRINCIPAIS")
        print("=" * 60)

        for target in IMPORTANT_FILES:

            # Localiza o arquivo mesmo se estiver dentro de uma pasta no ZIP
            matches = [
                name for name in available_files
                if Path(name).name.lower() == target.lower()
            ]

            if not matches:
                print(f"\n[{target}] NÃO ENCONTRADO")
                continue

            filename = matches[0]

            print(f"\n[{target}]")

            with archive.open(filename) as file:
                text_file = (
                    line.decode("utf-8-sig")
                    for line in file
                )

                reader = csv.DictReader(text_file)

                print("Colunas:")
                print(reader.fieldnames)

                print("\nPrimeiros registros:")

                for index, row in enumerate(reader):
                    if index >= 3:
                        break

                    print(row)


if __name__ == "__main__":
    inspect_gtfs()
