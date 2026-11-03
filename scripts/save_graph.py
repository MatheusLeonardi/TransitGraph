
import argparse
import sys
from pathlib import Path
from datetime import date

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from backend.gtfs.importer import import_gtfs
from backend.models.database import save_graph


GTFS_FILE = PROJECT_DIR / "data" / "raw" / "_sptrans_gtfs.zip"

DATABASE_FILE = (
    PROJECT_DIR / "data" / "processed" / "transitgraph.db"
)


def main():
    parser = argparse.ArgumentParser(
        description="Importar um GTFS e salvar o grafo no SQLite"
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Data de operação no formato AAAA-MM-DD"
    )
    parser.add_argument("--gtfs", type=Path, default=GTFS_FILE)
    parser.add_argument("--database", type=Path, default=DATABASE_FILE)
    args = parser.parse_args()

    print("=" * 55)
    print("TRANSITGRAPH - SALVANDO GRAFO NO SQLITE")
    print("=" * 55)

    print("\nImportando GTFS...")

    graph, stats = import_gtfs(
        args.gtfs,
        date.fromisoformat(args.date)
    )

    print("Grafo construído!")
    print(f"Vértices: {stats['vertices']}")
    print(f"Arestas: {stats['edges']}")

    print("\nSalvando no banco de dados...")

    result = save_graph(graph, args.database, metadata=stats)

    print("\nSALVAMENTO CONCLUÍDO!")

    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
