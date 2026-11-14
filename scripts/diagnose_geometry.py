"""Emite evidências geográficas de uma consulta à base local."""

import argparse
import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from backend.algorithms.bfs import bfs
from backend.algorithms.dfs import dfs
from backend.models.database import load_graph
from backend.services.itinerary_service import build_itinerary
from backend.services.road_matching_service import refine_itinerary_geometry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("origin")
    parser.add_argument("destination")
    parser.add_argument("--algorithm", choices=("bfs", "dfs"), default="bfs")
    parser.add_argument("--database", type=Path,
                        default=PROJECT_DIR / "data/processed/transitgraph.db")
    parser.add_argument("--osrm", action="store_true", help="Consulta o OSRM se habilitado.")
    parser.add_argument("--output", type=Path, help="Salva o JSON em UTF-8.")
    args = parser.parse_args()
    graph = load_graph(args.database)
    search = bfs if args.algorithm == "bfs" else dfs
    try:
        result = search(graph, args.origin, args.destination)
    except ValueError as error:
        parser.error(str(error))
    itinerary = build_itinerary(graph, result["path"] or [], args.database)
    if args.osrm:
        refine_itinerary_geometry(itinerary, args.database)
    report = {
        "service_date": graph.metadata.get("service_date"),
        "geometry_version": graph.metadata.get("geometry_version"),
        "algorithm": result["algorithm"],
        "path": result["path"],
        "edges": result["distance"],
        "itinerary": itinerary,
    }
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(content, encoding="utf-8")
    else:
        print(content, end="")


if __name__ == "__main__":
    main()
