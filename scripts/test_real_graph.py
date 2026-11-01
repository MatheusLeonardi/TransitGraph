
import sys
from pathlib import Path
from datetime import date
from time import perf_counter

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from backend.gtfs.importer import import_gtfs
from backend.algorithms.bfs import bfs
from backend.algorithms.dfs import dfs
from backend.algorithms.connectivity import weakly_connected_components


GTFS_FILE = PROJECT_DIR / "data" / "raw" / "_sptrans_gtfs.zip"


def find_test_pair(graph):
    """
    Procura automaticamente duas paradas conectadas
    por um caminho de pelo menos duas arestas.
    """

    for source, neighbors in graph.adjacency.items():
        for middle in neighbors:
            for target in graph.get_neighbors(middle):
                if target != source:
                    return source, target

    # Caso não encontre um caminho de duas arestas,
    # utiliza uma ligação direta.
    for source, neighbors in graph.adjacency.items():
        if neighbors:
            return source, next(iter(neighbors))

    raise ValueError("O grafo não possui arestas para testar.")


def main():
    print("=" * 60)
    print("TRANSITGRAPH - TESTE COM DADOS REAIS")
    print("=" * 60)

    print("\nConstruindo grafo...")
    graph, stats = import_gtfs(
        GTFS_FILE,
        date(2026, 11, 1)
    )

    print(f"Vértices: {stats['vertices']}")
    print(f"Arestas: {stats['edges']}")

    # ------------------------------------------------
    # TESTE BFS
    # ------------------------------------------------

    origin, destination = find_test_pair(graph)

    print("\n1. TESTE BFS")
    print(f"Origem: {origin}")
    print(f"Destino: {destination}")

    start = perf_counter()
    bfs_result = bfs(graph, origin, destination)
    bfs_time = perf_counter() - start

    print(f"Encontrou caminho: {bfs_result['found']}")
    print(f"Distância em arestas: {bfs_result['distance']}")
    print(f"Caminho: {bfs_result['path']}")
    print(f"Tempo: {bfs_time:.6f} segundos")

    # ------------------------------------------------
    # TESTE DFS
    # ------------------------------------------------

    print("\n2. TESTE DFS")
    print(f"Origem: {origin}")

    start = perf_counter()
    dfs_result = dfs(graph, origin)
    dfs_time = perf_counter() - start

    print(f"Paradas alcançáveis: {dfs_result['visited_count']}")
    print(f"Tempo: {dfs_time:.6f} segundos")

    # ------------------------------------------------
    # TESTE DE CONECTIVIDADE
    # ------------------------------------------------

    print("\n3. TESTE DE CONECTIVIDADE")

    start = perf_counter()
    connectivity = weakly_connected_components(graph)
    connectivity_time = perf_counter() - start

    print(
        "Componentes fracamente conexos:",
        connectivity["component_count"]
    )

    print(
        "Maior componente:",
        connectivity["largest_component_size"]
    )

    print(
        "Paradas isoladas:",
        len(connectivity["isolated_stops"])
    )

    print(f"Tempo: {connectivity_time:.6f} segundos")

    # ------------------------------------------------
    # RESULTADO
    # ------------------------------------------------

    print("\n" + "=" * 60)
    print("TESTES CONCLUÍDOS")
    print("=" * 60)


if __name__ == "__main__":
    main()
