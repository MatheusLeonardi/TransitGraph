"""Mede BFS e DFS de forma reproduzível para o relatório do TransitGraph."""

import argparse
import platform
import random
import statistics
import sys
from datetime import datetime
from pathlib import Path
from time import perf_counter


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from backend.algorithms.bfs import bfs
from backend.algorithms.dfs import dfs
from backend.algorithms.graph import Graph
from backend.models.database import load_graph


DEFAULT_DATABASE = (
    PROJECT_DIR / "data" / "processed" / "transitgraph.db"
)
DEFAULT_SIZES = (1_000, 5_000, 20_000, 50_000, 100_000, 200_000)


def elapsed_ms(function, *args):
    start = perf_counter()
    function(*args)
    return (perf_counter() - start) * 1_000


def benchmark_real_graph(graph, pair_count, seed):
    vertices = list(graph.adjacency)
    if len(vertices) < 2:
        raise ValueError("O banco precisa ter pelo menos dois vertices.")

    rng = random.Random(seed)
    bfs_times = []
    dfs_times = []

    for _ in range(pair_count):
        origin, destination = rng.sample(vertices, 2)
        bfs_times.append(elapsed_ms(bfs, graph, origin, destination))
        dfs_times.append(elapsed_ms(dfs, graph, origin))

    return {
        "vertices": graph.vertex_count(),
        "edges": graph.edge_count(),
        "bfs_median_ms": statistics.median(bfs_times),
        "dfs_median_ms": statistics.median(dfs_times),
    }


def build_synthetic_graph(vertex_count):
    """Cria um grafo direcionado alcancavel com aproximadamente 2 * V arestas."""
    graph = Graph()

    for index in range(vertex_count):
        graph.add_stop(str(index))

    for index in range(vertex_count - 1):
        graph.add_edge(str(index), str(index + 1))

    for index in range(vertex_count - 2):
        graph.add_edge(str(index), str(index + 2))

    return graph


def benchmark_synthetic_graph(vertex_count, repetitions):
    graph = build_synthetic_graph(vertex_count)
    origin = "0"
    destination = str(vertex_count - 1)

    bfs_times = [
        elapsed_ms(bfs, graph, origin, destination)
        for _ in range(repetitions)
    ]
    dfs_times = [
        elapsed_ms(dfs, graph, origin)
        for _ in range(repetitions)
    ]

    return {
        "vertices": graph.vertex_count(),
        "edges": graph.edge_count(),
        "bfs_median_ms": statistics.median(bfs_times),
        "dfs_median_ms": statistics.median(dfs_times),
    }


def format_number(value):
    return f"{value:,}".replace(",", ".")


def format_ms(value):
    return f"{value:.2f}".replace(".", ",")


def render_markdown(database, pair_count, repetitions, seed, real, synthetic):
    service_date = "nao informada"
    graph = load_graph(database)
    if graph.metadata.get("service_date"):
        service_date = str(graph.metadata["service_date"])

    lines = [
        "# Resultados de benchmark",
        "",
        f"- Executado em: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- Python: {platform.python_version()}",
        f"- Sistema: {platform.platform()}",
        f"- Processador: {platform.processor() or 'nao identificado'}",
        f"- Banco: `{database}`",
        f"- Data de servico do grafo: {service_date}",
        f"- Semente pseudoaleatoria: {seed}",
        f"- Pares aleatorios no grafo real: {pair_count}",
        f"- Repeticoes por grafo sintetico: {repetitions}",
        "",
        "## Grafo real",
        "",
        "| Vertices | Arestas | BFS origem-destino (mediana) | DFS completa (mediana) |",
        "| ---: | ---: | ---: | ---: |",
        (
            f"| {format_number(real['vertices'])} "
            f"| {format_number(real['edges'])} "
            f"| {format_ms(real['bfs_median_ms'])} ms "
            f"| {format_ms(real['dfs_median_ms'])} ms |"
        ),
        "",
        "## Grafos sinteticos",
        "",
        "| Vertices | Arestas | BFS completa (mediana) | DFS completa (mediana) |",
        "| ---: | ---: | ---: | ---: |",
    ]

    for row in synthetic:
        lines.append(
            f"| {format_number(row['vertices'])} "
            f"| {format_number(row['edges'])} "
            f"| {format_ms(row['bfs_median_ms'])} ms "
            f"| {format_ms(row['dfs_median_ms'])} ms |"
        )

    lines.extend([
        "",
        "Os tempos dependem do computador e devem ser regenerados no ambiente usado na apresentacao.",
        "",
    ])
    return "\n".join(lines)


def parse_sizes(value):
    sizes = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    if not sizes or any(size < 2 for size in sizes):
        raise argparse.ArgumentTypeError(
            "Informe tamanhos inteiros maiores ou iguais a 2."
        )
    return sizes


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark reproduzivel de BFS e DFS."
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--pairs", type=int, default=30)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--synthetic-sizes",
        type=parse_sizes,
        default=DEFAULT_SIZES,
        help="Lista separada por virgulas.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Arquivo Markdown opcional para salvar os resultados.",
    )
    args = parser.parse_args()

    if args.pairs < 1 or args.repetitions < 1:
        parser.error("--pairs e --repetitions devem ser positivos.")

    graph = load_graph(args.database)
    real = benchmark_real_graph(graph, args.pairs, args.seed)
    synthetic = [
        benchmark_synthetic_graph(size, args.repetitions)
        for size in args.synthetic_sizes
    ]
    markdown = render_markdown(
        args.database,
        args.pairs,
        args.repetitions,
        args.seed,
        real,
        synthetic,
    )

    print(markdown)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")
        print(f"Resultados salvos em: {args.output}")


if __name__ == "__main__":
    main()
