"""Compara a rota com menos paradas (BFS) e a de menor tempo estimado (Dijkstra)."""

import argparse
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from backend.algorithms.bfs import bfs
from backend.algorithms.dijkstra import _estimated_travel_time, dijkstra
from backend.models.database import load_graph


DEFAULT_DATABASE = PROJECT_DIR / "data" / "processed" / "transitgraph.db"


def path_time(graph, path):
    """Soma os pesos do caminho com a mesma regra do Dijkstra.

    Retorna os segundos e quantas arestas usaram a estimativa geográfica
    por falta de horário no GTFS.
    """
    total, estimated = 0.0, 0
    for source, target in zip(path, path[1:]):
        weight = graph.edge_weights.get((source, target))
        if weight is None:
            weight = _estimated_travel_time(graph, source, target)
            estimated += 1
        total += weight
    return total, estimated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("origin", nargs="?", default="600012584")
    parser.add_argument("destination", nargs="?", default="3609172")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    graph = load_graph(args.database)
    print(f"Rede completa: {graph.vertex_count()} vértices, {graph.edge_count()} arestas, "
          f"data de serviço {graph.metadata.get('service_date', 'desconhecida')}.")
    print(f"Origem {args.origin}, destino {args.destination}.")
    print()
    print("| Algoritmo | Arestas | Tempo estimado (s) | Tempo estimado (min) | Arestas sem horário GTFS |")
    print("|---|---:|---:|---:|---:|")
    for name, result in (("BFS", bfs(graph, args.origin, args.destination)),
                         ("Dijkstra", dijkstra(graph, args.origin, args.destination))):
        if not result["found"]:
            print(f"| {name} | sem caminho | — | — | — |")
            continue
        seconds, estimated = path_time(graph, result["path"])
        print(f"| {name} | {result['distance']} | {seconds:.1f} | {seconds / 60:.1f} | {estimated} |")


if __name__ == "__main__":
    main()
