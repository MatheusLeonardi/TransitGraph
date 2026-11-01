
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
    print("=" * 55)
    print("TRANSITGRAPH - SALVANDO GRAFO NO SQLITE")
    print("=" * 55)

    print("\nImportando GTFS...")

    graph, stats = import_gtfs(
        GTFS_FILE,
        date(2026, 11, 1)
    )

    print("Grafo construído!")
    print(f"Vértices: {stats['vertices']}")
    print(f"Arestas: {stats['edges']}")

    print("\nSalvando no banco de dados...")

    result = save_graph(graph, DATABASE_FILE)

    print("\nSALVAMENTO CONCLUÍDO!")

    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
