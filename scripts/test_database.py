
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from backend.models.database import load_graph
from backend.algorithms.bfs import bfs


DATABASE_FILE = (
    PROJECT_DIR / "data" / "processed" / "transitgraph.db"
)


def main():
    print("=" * 55)
    print("TRANSITGRAPH - TESTE DO SQLITE")
    print("=" * 55)

    graph = load_graph(DATABASE_FILE)

    print(f"\nParadas carregadas: {graph.vertex_count()}")
    print(f"Arestas carregadas: {graph.edge_count()}")

    # Verificar se os dados geográficos foram preservados
    stop_id = "301790"
    stop = graph.get_stop(stop_id)

    print(f"\nDados da parada {stop_id}:")
    print(stop)

    # Testar BFS no grafo carregado
    result = bfs(graph, "301790", "301724")

    print("\nTeste BFS após carregamento:")
    print(f"Caminho encontrado: {result['found']}")
    print(f"Caminho: {result['path']}")
    print(f"Distância: {result['distance']}")

    assert graph.vertex_count() > 0
    assert graph.edge_count() > 0
    assert result["found"] is True

    print("\nTESTE DO SQLITE CONCLUÍDO COM SUCESSO!")


if __name__ == "__main__":
    main()
