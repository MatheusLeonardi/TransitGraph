"""Mede BFS e DFS nas mesmas condições, sem API ou renderização."""

import argparse
import platform
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
from backend.models.database import load_graph
from backend.services.instance_service import INSTANCE_LABELS, build_instances


DEFAULT_DATABASE = PROJECT_DIR / "data" / "processed" / "transitgraph.db"
QUERIES = {
    "local": ("480012875", "480014889"),
    "lines": ("8812664", "940004410"),
    "full": ("480012875", "480014632"),
}


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


def render_markdown(graph, instances, repetitions):
    timestamp = datetime.now(timezone(timedelta(hours=-3))).isoformat(timespec="seconds")
    lines = [
        "# Benchmark de BFS e DFS",
        "",
        f"- Execução em {timestamp}, horário de São Paulo.",
        f"- Python {platform.python_version()}, {platform.platform()}, "
        f"{platform.processor() or 'processador não identificado'}.",
        f"- Data de serviço do banco registrada como {graph.metadata.get('service_date', 'desconhecida')}.",
        f"- Uma execução de aquecimento e mediana de {repetitions} repetições por algoritmo e consulta.",
        "- Tempos medidos após carregar o SQLite e construir os recortes. A medição inclui "
        "a construção do resultado da busca, com geometria, API e renderização fora do intervalo.",
        "- Pico de alocações Python em execução adicional com tracemalloc, em KiB. "
        "O grafo já estava em memória. A medição cobre a alocação incremental da busca.",
    ]
    for key, (origin, destination) in QUERIES.items():
        if key not in instances:
            continue
        instance = instances[key]
        if not instance.has_stop(origin):
            lines.extend(["", f"## {INSTANCE_LABELS[key]}", "", "Origem de referência ausente."])
            continue
        lines.extend([
            "",
            f"## {INSTANCE_LABELS[key]}",
            "",
            (f"{instance.vertex_count():,} vértices e {instance.edge_count():,} arestas. "
             f"Origem {origin}.").replace(",", "."),
            "",
            "| Consulta | Busca | Mediana (ms) | Pico (KiB) | Descobertas | Visitas | Arestas examinadas | Arestas do caminho |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ])
        queries = [("Alcance completo", None)]
        if instance.has_stop(destination):
            queries.append((f"Até {destination}", destination))
        for label, target in queries:
            for search in (bfs, dfs):
                time_ms, peak, result = measure(search, instance, origin, target, repetitions)
                distance = result["distance"]
                lines.append(
                    f"| {label} | {result['algorithm']} | {time_ms:.4f} | {peak:.1f} "
                    f"| {result['discovered_count']} | {result['processed_count']} "
                    f"| {result['edges_examined']} | {distance if distance is not None else '—'} |"
                )
    lines.extend([
        "",
        "Na travessia completa, compare as contagens das duas buscas partindo da mesma origem. "
        "Em consultas com destino, as ordens de visita determinam quanto trabalho cada busca "
        "faz antes de parar. A BFS encerra ao retirar o destino da fila e a DFS ao descobri-lo.",
        "",
        "As diferenças de tempo refletem este computador, o alcance de cada origem e a "
        "instrumentação de cada algoritmo. As medições das três instâncias ilustram a escala "
        "do trabalho executado. O limite assintótico depende dos vértices e arestas examinados.",
        "",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--repetitions", type=int, default=21)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("--repetitions deve ser positivo.")

    graph = load_graph(args.database)
    markdown = render_markdown(graph, build_instances(graph), args.repetitions)
    print(markdown)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")


if __name__ == "__main__":
    main()
