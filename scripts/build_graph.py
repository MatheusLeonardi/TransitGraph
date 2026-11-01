
import argparse
import sys

from datetime import date
from pathlib import Path

# Adiciona a raiz do projeto ao caminho de importação
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from backend.gtfs.importer import import_gtfs


GTFS_FILE = PROJECT_DIR / "data" / "raw" / "_sptrans_gtfs.zip"



def main():
    parser = argparse.ArgumentParser(
        description="Construir o grafo da rede de ônibus da SPTrans"
    )

    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Data de operação no formato AAAA-MM-DD"
    )

    args = parser.parse_args()
    service_date = date.fromisoformat(args.date)

    print("=" * 55)
    print("TRANSITGRAPH - CONSTRUÇÃO DO GRAFO")
    print("=" * 55)

    graph, stats = import_gtfs(GTFS_FILE, service_date)

    print("\nIMPORTAÇÃO CONCLUÍDA!\n")

    for key, value in stats.items():
        print(f"{key}: {value}")

    print("\nGRAFO CONSTRUÍDO COM SUCESSO")


if __name__ == "__main__":
    main()
