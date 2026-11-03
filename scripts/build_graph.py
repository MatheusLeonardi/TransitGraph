
import argparse
import sys

from datetime import date
from pathlib import Path

# Adiciona a raiz do projeto ao caminho de importação
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from backend.gtfs.importer import import_gtfs
from backend.models.database import save_graph


GTFS_FILE = PROJECT_DIR / "data" / "raw" / "_sptrans_gtfs.zip"
DATABASE_FILE = PROJECT_DIR / "data" / "processed" / "transitgraph.db"



def main():
    parser = argparse.ArgumentParser(
        description="Construir o grafo da rede de ônibus da SPTrans"
    )

    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Data de operação no formato AAAA-MM-DD"
    )

    parser.add_argument(
        "--gtfs",
        type=Path,
        default=GTFS_FILE,
        help="Caminho do arquivo GTFS compactado"
    )

    parser.add_argument(
        "--database",
        type=Path,
        default=DATABASE_FILE,
        help="Caminho do banco SQLite de saída"
    )

    args = parser.parse_args()
    service_date = date.fromisoformat(args.date)

    print("=" * 55)
    print("TRANSITGRAPH - CONSTRUÇÃO DO GRAFO")
    print("=" * 55)

    graph, stats = import_gtfs(args.gtfs, service_date)

    print("\nIMPORTAÇÃO CONCLUÍDA!\n")

    for key, value in stats.items():
        print(f"{key}: {value}")

    result = save_graph(graph, args.database, metadata=stats)

    print("\nGRAFO CONSTRUÍDO E SALVO COM SUCESSO")
    print(f"database: {result['database']}")
    print(f"stops_saved: {result['stops_saved']}")
    print(f"edges_saved: {result['edges_saved']}")
    print(f"routes_saved: {result['routes_saved']}")
    print(f"edge_shapes_saved: {result['edge_shapes_saved']}")
    print(f"shape_points_saved: {result['shape_points_saved']}")


if __name__ == "__main__":
    main()
