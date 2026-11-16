"""Mede BFS e DFS nas mesmas condições, sem API ou renderização."""

import argparse
import math
import platform
import random
import statistics
import sys
import tracemalloc
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from backend.algorithms.bfs import bfs
from backend.algorithms.dfs import dfs
from backend.algorithms.graph import Graph
from backend.models.database import load_graph
from backend.services.instance_service import INSTANCE_LABELS, build_instances


DEFAULT_DATABASE = PROJECT_DIR / "data" / "processed" / "transitgraph.db"
QUERIES = {
    "local": ("480012875", "480014889"),
    "lines": ("8812664", "940004410"),
    "full": ("480012875", "480014632"),
}
# A rede completa tem 27.218 arestas para 20.812 vértices, cerca de 1,3 por vértice.
EDGE_RATIO = 1.3
SYNTHETIC_SIZES = (1_000, 5_000, 20_000, 50_000, 100_000)
SYNTHETIC_ORIGIN = "0"
DEFAULT_SEED = 2026


def random_strongly_connected_graph(vertex_count, seed=DEFAULT_SEED, edge_ratio=EDGE_RATIO):
    """Ciclo dirigido em ordem aleatória mais atalhos sorteados até E = round(edge_ratio·V).

    O ciclo torna o grafo fortemente conexo. A travessia completa a partir de
    qualquer vértice processa os V vértices e examina as E arestas.
    """
    rng = random.Random(seed)
    stops = [str(index) for index in range(vertex_count)]
    rng.shuffle(stops)
    graph = Graph()
    for source, target in zip(stops, stops[1:] + stops[:1]):
        graph.add_edge(source, target)

    edge_count = vertex_count
    target_count = min(round(vertex_count * edge_ratio), vertex_count * (vertex_count - 1))
    while edge_count < target_count:
        source = stops[rng.randrange(vertex_count)]
        target = stops[rng.randrange(vertex_count)]
        if source != target and target not in graph.adjacency[source]:
            graph.add_edge(source, target)
            edge_count += 1
    return graph


def measure(search, graph, origin, destination, repetitions):
    result = search(graph, origin, destination)
    samples = []
    for _ in range(repetitions):
        start = perf_counter()
        search(graph, origin, destination)
        samples.append((perf_counter() - start) * 1_000)

    tracemalloc.start()
    try:
        search(graph, origin, destination)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return statistics.median(samples), peak / 1024, result


def thousands(number):
    return f"{number:,}".replace(",", ".")


def work(result):
    """Vértices processados mais arestas examinadas, as operações contadas em O(V + E)."""
    return result["processed_count"] + result["edges_examined"]


def measure_traversals(label, graph, origin, repetitions):
    """Travessia completa (sem destino) das duas buscas a partir da mesma origem."""
    row = {"label": label, "vertices": graph.vertex_count(), "edges": graph.edge_count()}
    for search in (bfs, dfs):
        time_ms, peak, result = measure(search, graph, origin, None, repetitions)
        row[result["algorithm"]] = {"time": time_ms, "peak": peak, "result": result}
    return row


def measure_synthetic(sizes, seed, repetitions):
    return [
        measure_traversals(
            "Aleatória", random_strongly_connected_graph(size, seed), SYNTHETIC_ORIGIN, repetitions
        )
        for size in sizes
    ]


def growth_exponent(rows, algorithm):
    """Inclinação de log(tempo) contra log(trabalho); 1 corresponde a crescimento linear."""
    regression = statistics.linear_regression(
        [math.log(work(row[algorithm]["result"])) for row in rows],
        [math.log(row[algorithm]["time"]) for row in rows],
    )
    return regression.slope


def render_summary(rows):
    lines = [
        "| Instância | Vértices | Arestas | Trabalho | Mediana BFS (ms) | Mediana DFS (ms) "
        "| BFS (ns/unidade) | DFS (ns/unidade) | Pico BFS (KiB) | Pico DFS (KiB) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        bfs_row, dfs_row = row["BFS"], row["DFS"]
        units = work(bfs_row["result"])
        lines.append(
            f"| {row['label']} | {row['vertices']} | {row['edges']} | {units} "
            f"| {bfs_row['time']:.4f} | {dfs_row['time']:.4f} "
            f"| {bfs_row['time'] * 1e6 / units:.0f} | {dfs_row['time'] * 1e6 / units:.0f} "
            f"| {bfs_row['peak']:.1f} | {dfs_row['peak']:.1f} |"
        )
    return lines


def render_growth(rows):
    lines = [
        "",
        "## Crescimento com o tamanho",
        "",
        "| Faixa de vértices | Trabalho | Mediana BFS | Mediana DFS | Expoente BFS | Expoente DFS |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    def ratios(before, after):
        return [after[key] / before[key] for key in ("work", "BFS", "DFS")]

    points = [
        {"vertices": row["vertices"], "work": work(row["BFS"]["result"]),
         "BFS": row["BFS"]["time"], "DFS": row["DFS"]["time"]}
        for row in rows
    ]
    for before, after in zip(points, points[1:]):
        work_ratio, bfs_ratio, dfs_ratio = ratios(before, after)
        lines.append(
            f"| {thousands(before['vertices'])} → {thousands(after['vertices'])} "
            f"| ×{work_ratio:.1f} | ×{bfs_ratio:.1f} | ×{dfs_ratio:.1f} "
            f"| {math.log(bfs_ratio) / math.log(work_ratio):.2f} "
            f"| {math.log(dfs_ratio) / math.log(work_ratio):.2f} |"
        )
    work_ratio, bfs_ratio, dfs_ratio = ratios(points[0], points[-1])
    lines.extend([
        f"| {thousands(points[0]['vertices'])} → {thousands(points[-1]['vertices'])}, ajuste "
        f"| ×{work_ratio:.1f} | ×{bfs_ratio:.1f} | ×{dfs_ratio:.1f} "
        f"| {growth_exponent(rows, 'BFS'):.2f} | {growth_exponent(rows, 'DFS'):.2f} |",
        "",
        "O expoente compara o crescimento da mediana com o do trabalho. Na última linha ele "
        "vem de mínimos quadrados sobre log(tempo) e log(V + E). Expoente 1 é crescimento "
        "linear, como prevê O(V + E). Como o trabalho vale exatamente V + E em todos os "
        "tamanhos, um expoente acima de 1 indica que cada operação ficou mais cara, por "
        "exemplo quando as estruturas deixam de caber no cache do processador, e não que a "
        "busca executou operações extras.",
    ])
    return lines


def render_instance(key, instance, repetitions):
    origin, destination = QUERIES[key]
    lines = [
        "",
        f"## {INSTANCE_LABELS[key]}",
        "",
        f"{thousands(instance.vertex_count())} vértices e {thousands(instance.edge_count())} "
        f"arestas. Origem {origin}.",
        "",
        "| Consulta | Busca | Mediana (ms) | Pico (KiB) | Descobertas | Visitas | Arestas examinadas | Arestas do caminho |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    traversals = measure_traversals(INSTANCE_LABELS[key], instance, origin, repetitions)
    measured = [("Alcance completo", traversals[algorithm]) for algorithm in ("BFS", "DFS")]
    if instance.has_stop(destination):
        for search in (bfs, dfs):
            time_ms, peak, result = measure(search, instance, origin, destination, repetitions)
            measured.append((f"Até {destination}", {"time": time_ms, "peak": peak, "result": result}))

    for label, entry in measured:
        result = entry["result"]
        distance = result["distance"]
        lines.append(
            f"| {label} | {result['algorithm']} | {entry['time']:.4f} | {entry['peak']:.1f} "
            f"| {result['discovered_count']} | {result['processed_count']} "
            f"| {result['edges_examined']} | {distance if distance is not None else '—'} |"
        )
    return traversals, lines


def render_markdown(graph, instances, sizes, seed, repetitions):
    timestamp = datetime.now(timezone(timedelta(hours=-3))).isoformat(timespec="seconds")
    lines = [
        "# Benchmark de BFS e DFS",
        "",
        f"- Execução em {timestamp}, horário de São Paulo.",
        f"- Python {platform.python_version()}, {platform.platform()}, "
        f"{platform.processor() or 'processador não identificado'}.",
    ]
    if graph is None:
        lines.append("- Banco SQLite não encontrado. As instâncias reais foram omitidas.")
    else:
        lines.append(
            f"- Data de serviço do banco registrada como {graph.metadata.get('service_date', 'desconhecida')}."
        )
    lines.extend([
        f"- Uma execução de aquecimento e mediana de {repetitions} repetições por algoritmo e consulta.",
        "- Tempos medidos após carregar o SQLite e construir os grafos. A medição inclui "
        "a construção do resultado da busca, com geometria, API e renderização fora do intervalo.",
        "- Pico de alocações Python em execução adicional com tracemalloc, em KiB. "
        "O grafo já estava em memória. A medição cobre a alocação incremental da busca.",
        f"- Grafos aleatórios: ciclo dirigido em ordem aleatória mais atalhos sorteados até "
        f"E = round({EDGE_RATIO}·V), seed {seed}. O ciclo garante que a travessia a partir do "
        f"vértice \"{SYNTHETIC_ORIGIN}\" alcance todo o grafo.",
    ])

    synthetic = measure_synthetic(sizes, seed, repetitions)
    real_rows, real_lines = [], []
    for key in QUERIES:
        if key not in instances:
            continue
        instance = instances[key]
        if not instance.has_stop(QUERIES[key][0]):
            real_lines.extend(["", f"## {INSTANCE_LABELS[key]}", "", "Origem de referência ausente."])
            continue
        traversals, section = render_instance(key, instance, repetitions)
        real_rows.append(traversals)
        real_lines.extend(section)

    lines.extend([
        "",
        "## Travessia completa",
        "",
        "Sem destino, cada busca percorre todo o alcance da origem. O trabalho soma os "
        "vértices processados e as arestas examinadas. Nos grafos aleatórios ele vale "
        "exatamente V + E. Nas instâncias reais conta apenas a parte alcançável da origem "
        "de referência.",
        "",
        *render_summary(synthetic + real_rows),
    ])
    if len(synthetic) >= 2:
        lines.extend(render_growth(synthetic))
    lines.extend(real_lines)
    lines.extend([
        "",
        "Na travessia completa, compare as contagens das duas buscas partindo da mesma origem. "
        "Em consultas com destino, as ordens de visita determinam quanto trabalho cada busca "
        "faz antes de parar. A BFS encerra ao retirar o destino da fila e a DFS ao descobri-lo.",
        "",
        "As diferenças de tempo refletem este computador, o alcance de cada origem e a "
        "instrumentação de cada algoritmo. O limite assintótico depende dos vértices e "
        "arestas examinados.",
        "",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--repetitions", type=int, default=21)
    parser.add_argument("--sizes", type=int, nargs="+", default=list(SYNTHETIC_SIZES),
                        help="Quantidade de vértices de cada grafo aleatório.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("--repetitions deve ser positivo.")
    if min(args.sizes) < 2:
        parser.error("--sizes deve ter ao menos 2 vértices por grafo.")

    graph = load_graph(args.database) if args.database.exists() else None
    instances = build_instances(graph) if graph is not None else {}
    markdown = render_markdown(graph, instances, args.sizes, args.seed, args.repetitions)
    print(markdown)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")


if __name__ == "__main__":
    main()
