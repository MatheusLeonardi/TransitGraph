"""Testes do item 4.5 do enunciado para BFS e DFS.

Cada classe corresponde a uma categoria exigida: casos simples, casos sem
solução, situações de fronteira, propriedades em instâncias de tamanhos
diferentes, validação independente e desempenho. A networkx entra somente
aqui, como oráculo. As buscas avaliadas são as de backend/algorithms.
"""

import importlib.util
import random
import sys
from functools import cache
from pathlib import Path

import pytest

from backend.algorithms.bfs import bfs
from backend.algorithms.dfs import dfs
from backend.algorithms.graph import Graph
from backend.models.database import load_graph
from backend.services.instance_service import LOCAL_ORIGIN, build_instances


PROJECT_DIR = Path(__file__).resolve().parents[1]
DATABASE = PROJECT_DIR / "data" / "processed" / "transitgraph.db"
SEARCHES = [bfs, dfs]

# Mini rede calculada à mão. A ordem de inserção é a ordem dos vizinhos.
#   S → A → C → D → T → S   (volta à origem)
#   S → B → T               (atalho)
MINI_NETWORK = [
    ("S", "A"), ("S", "B"), ("A", "C"), ("C", "D"),
    ("D", "T"), ("B", "T"), ("T", "S"),
]

# (vértices, arestas, seed): de poucos vértices até a ordem da rede real,
# com densidades abaixo, perto e acima de E ≈ 1,3·V.
RANDOM_CASES = [
    (8, 10, 11),
    (60, 78, 12),
    (500, 650, 13),
    (2_000, 6_000, 14),
    (5_000, 2_500, 15),
    (20_000, 26_000, 16),
]
RANDOM_IDS = [f"V{vertices}-E{edges}" for vertices, edges, _ in RANDOM_CASES]
LONG_CHAIN = 50_000


def load_script(name):
    """Importa um arquivo de scripts/ pelo caminho, pois a pasta não é um pacote."""
    spec = importlib.util.spec_from_file_location(
        f"transitgraph_{name}", PROJECT_DIR / "scripts" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


benchmark_script = load_script("benchmark")


def build_graph(edges, stops=()):
    graph = Graph()
    for stop_id in stops:
        graph.add_stop(stop_id)
    for edge in edges:
        graph.add_edge(*edge)
    return graph


@cache
def random_graph(vertex_count, edge_count, seed):
    """Grafo dirigido G(n, m) sem auto-laços. Pode conter pares sem caminho."""
    rng = random.Random(seed)
    edges = {}
    while len(edges) < edge_count:
        source, target = rng.randrange(vertex_count), rng.randrange(vertex_count)
        if source != target:
            edges[str(source), str(target)] = None
    return build_graph(edges, map(str, range(vertex_count)))


@cache
def synthetic_graph(vertex_count):
    return benchmark_script.random_strongly_connected_graph(vertex_count)


def sample_origins(graph, seed, count):
    return random.Random(seed).sample(sorted(graph.adjacency), min(count, graph.vertex_count()))


def sample_queries(graph, seed, origin_count, reachable_from):
    """Para cada origem sorteada, um destino alcançável e um inalcançável, quando existem."""
    rng = random.Random(seed)
    stops = sorted(graph.adjacency)
    queries = []
    for origin in rng.sample(stops, min(origin_count, len(stops))):
        reached = reachable_from(origin)
        for candidates in (sorted(reached - {origin}), sorted(set(stops) - reached)):
            if candidates:
                queries.append((origin, rng.choice(candidates)))
    return queries


@cache
def property_queries(vertex_count, edge_count, seed):
    graph = random_graph(vertex_count, edge_count, seed)
    return sample_queries(graph, seed, 15, lambda origin: set(bfs(graph, origin)["visited_order"]))


def assert_valid_path(graph, path, origin, destination):
    assert path[0] == origin
    assert path[-1] == destination
    assert len(set(path)) == len(path)
    for source, target in zip(path, path[1:]):
        # A aresta precisa existir neste sentido.
        assert target in graph.adjacency[source]


def to_networkx(nx, graph):
    """Cópia independente com a mesma ordem de vizinhos do Graph."""
    digraph = nx.DiGraph()
    digraph.add_nodes_from(graph.adjacency)
    digraph.add_edges_from(
        (source, target) for source in graph.adjacency for target in graph.adjacency[source]
    )
    return digraph


@pytest.fixture(scope="module")
def nx():
    return pytest.importorskip("networkx")


@pytest.fixture(scope="module")
def real_instances():
    if not DATABASE.exists():
        pytest.skip(f"Banco da rede real indisponível em {DATABASE}.")
    return build_instances(load_graph(DATABASE))


@pytest.fixture(scope="module")
def long_chain():
    stops = [str(index) for index in range(LONG_CHAIN)]
    return stops, build_graph(zip(stops, stops[1:]))


class TestCasosSimples:
    """Ordens e caminhos escritos à mão para a MINI_NETWORK."""

    def test_bfs_order_and_shortest_path(self):
        graph = build_graph(MINI_NETWORK)

        complete = bfs(graph, "S")
        assert complete["visited_order"] == ["S", "A", "B", "C", "T", "D"]
        assert complete["edges_examined"] == 7

        # T é descoberto por B no 3º nível e retirado da fila depois de C.
        result = bfs(graph, "S", "T")
        assert result["path"] == ["S", "B", "T"]
        assert result["distance"] == 2
        assert result["visited_order"] == ["S", "A", "B", "C", "T"]
        assert result["discovered_count"] == 6
        assert result["edges_examined"] == 5

    def test_dfs_order_finish_and_first_found_path(self):
        graph = build_graph(MINI_NETWORK)

        complete = dfs(graph, "S")
        assert complete["visited_order"] == ["S", "A", "C", "D", "T", "B"]
        assert complete["finish_order"] == ["T", "D", "C", "A", "B", "S"]
        assert complete["edges_examined"] == 7

        # A DFS desce pelo primeiro vizinho de S e chega a T antes de ver o atalho.
        result = dfs(graph, "S", "T")
        assert result["path"] == ["S", "A", "C", "D", "T"]
        assert result["distance"] == 4
        assert result["visited_order"] == ["S", "A", "C", "D", "T"]
        assert result["edges_examined"] == 4

    @pytest.mark.parametrize("search", SEARCHES)
    def test_route_back_follows_edge_direction(self, search):
        # Não há aresta B → A nem B → S. A volta precisa contornar o ciclo.
        result = search(build_graph(MINI_NETWORK), "B", "A")
        assert result["path"] == ["B", "T", "S", "A"]
        assert result["distance"] == 3


class TestSemSolucao:

    @pytest.mark.parametrize("search", SEARCHES)
    def test_edge_only_in_opposite_direction(self, search):
        # D → A existe, A → D não.
        graph = build_graph([("A", "B"), ("B", "C"), ("D", "A")])

        result = search(graph, "A", "D")
        assert result["found"] is False
        assert result["path"] is None
        assert result["distance"] is None
        assert result["visited_order"] == ["A", "B", "C"]
        assert search(graph, "D", "A")["path"] == ["D", "A"]

    @pytest.mark.parametrize("search", SEARCHES)
    def test_unreachable_destination_exhausts_the_reach(self, search):
        graph = build_graph(MINI_NETWORK, stops=["Z"])

        result = search(graph, "S", "Z")
        complete = search(graph, "S")
        assert result["found"] is False
        assert result["visited_order"] == complete["visited_order"]
        assert result["edges_examined"] == complete["edges_examined"] == 7

    # BFS com destino inexistente e DFS com origem inexistente estão em
    # test_bfs.py e test_dfs.py. Aqui ficam as combinações restantes.
    @pytest.mark.parametrize(("search", "origin", "destination", "message"), [
        (bfs, "X", None, "origem"),
        (bfs, "X", "S", "origem"),
        (dfs, "X", "S", "origem"),
        (dfs, "S", "X", "destino"),
    ], ids=["bfs-origem", "bfs-origem-com-destino", "dfs-origem-com-destino", "dfs-destino"])
    def test_unknown_stops_are_rejected(self, search, origin, destination, message):
        with pytest.raises(ValueError, match=message):
            search(build_graph(MINI_NETWORK), origin, destination)


class TestFronteira:

    @pytest.mark.parametrize("search", SEARCHES)
    def test_empty_graph_has_no_valid_origin(self, search):
        with pytest.raises(ValueError, match="origem"):
            search(Graph(), "A")

    @pytest.mark.parametrize("search", SEARCHES)
    def test_origin_equal_to_destination_examines_no_edge(self, search):
        # S tem vizinhos e está num ciclo. O resultado ainda é o caminho trivial.
        result = search(build_graph(MINI_NETWORK), "S", "S")
        assert result["found"] is True
        assert result["path"] == ["S"]
        assert result["distance"] == 0
        assert result["visited_order"] == ["S"]
        assert result["edges_examined"] == 0

    @pytest.mark.parametrize("search", SEARCHES)
    def test_stop_without_outgoing_edges(self, search):
        # B recebe duas arestas e não tem saída. A não recebe nenhuma.
        graph = build_graph([("A", "B"), ("A", "C"), ("C", "B")])

        complete = search(graph, "B")
        assert complete["visited_order"] == ["B"]
        assert complete["edges_examined"] == 0
        assert search(graph, "B", "C")["found"] is False
        assert search(graph, "C", "A")["found"] is False
        assert search(graph, "A", "B")["path"] == ["A", "B"]

    @pytest.mark.parametrize("search", SEARCHES)
    def test_three_vertex_cycle_terminates_from_every_origin(self, search):
        graph = build_graph([("A", "B"), ("B", "C"), ("C", "A")])

        for origin, expected in (("A", ["A", "B", "C"]), ("B", ["B", "C", "A"]),
                                 ("C", ["C", "A", "B"])):
            result = search(graph, origin)
            assert result["visited_order"] == expected
            assert result["edges_examined"] == 3
        assert search(graph, "B", "A")["path"] == ["B", "C", "A"]
        assert search(graph, "A", "C")["path"] == ["A", "B", "C"]

    @pytest.mark.parametrize("search", SEARCHES)
    def test_self_loop_is_examined_but_never_revisited(self, search):
        # O Graph aceita auto-laço. A rede real carregada não possui nenhum.
        graph = build_graph([("A", "A"), ("A", "B"), ("B", "B")])
        assert graph.edge_count() == 3

        complete = search(graph, "A")
        assert complete["visited_order"] == ["A", "B"]
        assert complete["edges_examined"] == 3
        assert search(graph, "A", "B")["path"] == ["A", "B"]
        assert search(graph, "A", "A")["path"] == ["A"]

        alone = search(build_graph([("X", "X")]), "X")
        assert alone["visited_order"] == ["X"]
        assert alone["edges_examined"] == 1

    @pytest.mark.parametrize("search", SEARCHES)
    def test_long_chain_does_not_hit_recursion_limit(self, search, long_chain):
        stops, graph = long_chain
        # Uma DFS recursiva precisaria de 50.000 chamadas aninhadas.
        assert sys.getrecursionlimit() < LONG_CHAIN

        complete = search(graph, stops[0])
        assert complete["visited_order"] == stops
        assert complete["edges_examined"] == LONG_CHAIN - 1

        result = search(graph, stops[0], stops[-1])
        assert result["path"] == stops
        assert result["distance"] == LONG_CHAIN - 1
        assert search(graph, stops[-1], stops[0])["visited_order"] == [stops[-1]]


@pytest.mark.parametrize(("vertex_count", "edge_count", "seed"), RANDOM_CASES, ids=RANDOM_IDS)
class TestPropriedades:
    """Propriedades de qualquer grafo dirigido, verificadas em grafos aleatórios de vários tamanhos."""

    def test_full_traversals_reach_the_same_vertex_set(self, vertex_count, edge_count, seed):
        graph = random_graph(vertex_count, edge_count, seed)

        for origin in sample_origins(graph, seed, 15):
            by_level, by_depth = bfs(graph, origin), dfs(graph, origin)
            reached = set(by_level["visited_order"])
            assert set(by_depth["visited_order"]) == reached
            assert set(by_depth["finish_order"]) == reached
            assert by_depth["finish_order"][-1] == origin
            for result in (by_level, by_depth):
                assert len(result["visited_order"]) == len(reached) == result["discovered_count"]
                # Cada aresta que sai de um vértice alcançado é examinada uma única vez.
                assert result["edges_examined"] == sum(len(graph.adjacency[stop]) for stop in reached)

    def test_returned_paths_follow_existing_directed_edges(self, vertex_count, edge_count, seed):
        graph = random_graph(vertex_count, edge_count, seed)
        queries = property_queries(vertex_count, edge_count, seed)

        found = 0
        for origin, destination in queries:
            by_level, by_depth = bfs(graph, origin, destination), dfs(graph, origin, destination)
            assert by_level["found"] == by_depth["found"]
            for result in (by_level, by_depth):
                if result["found"]:
                    found += 1
                    assert_valid_path(graph, result["path"], origin, destination)
                    assert result["distance"] == len(result["path"]) - 1
                    assert result["visited_order"][-1] == destination
        assert found

    def test_bfs_path_is_never_longer_than_dfs_path(self, vertex_count, edge_count, seed):
        graph = random_graph(vertex_count, edge_count, seed)

        for origin, destination in property_queries(vertex_count, edge_count, seed):
            by_level, by_depth = bfs(graph, origin, destination), dfs(graph, origin, destination)
            if by_level["found"]:
                assert by_level["distance"] <= by_depth["distance"]

    def test_failed_search_explores_the_whole_reach(self, vertex_count, edge_count, seed):
        graph = random_graph(vertex_count, edge_count, seed)

        failed = 0
        for origin, destination in property_queries(vertex_count, edge_count, seed):
            for search in SEARCHES:
                result = search(graph, origin, destination)
                if not result["found"]:
                    failed += 1
                    assert result["path"] is None
                    assert result["distance"] is None
                    assert set(result["visited_order"]) == set(search(graph, origin)["visited_order"])
        assert failed


@pytest.mark.parametrize(("vertex_count", "edge_count", "seed"), RANDOM_CASES, ids=RANDOM_IDS)
class TestValidacaoNetworkx:
    """A networkx calcula as respostas de forma independente nos mesmos grafos aleatórios."""

    def test_bfs_distance_matches_shortest_path_length(self, nx, vertex_count, edge_count, seed):
        graph = random_graph(vertex_count, edge_count, seed)
        oracle = to_networkx(nx, graph)
        queries = sample_queries(
            graph, seed + 1, 15, lambda origin: nx.descendants(oracle, origin) | {origin}
        )

        for origin, destination in queries:
            result = bfs(graph, origin, destination)
            if nx.has_path(oracle, origin, destination):
                assert result["distance"] == nx.shortest_path_length(oracle, origin, destination)
            else:
                assert result["found"] is False

    def test_dfs_reach_matches_descendants(self, nx, vertex_count, edge_count, seed):
        graph = random_graph(vertex_count, edge_count, seed)
        oracle = to_networkx(nx, graph)

        for origin in sample_origins(graph, seed + 1, 15):
            expected = nx.descendants(oracle, origin) | {origin}
            result = dfs(graph, origin)
            assert set(result["visited_order"]) == expected
            assert result["discovered_count"] == len(expected)

    def test_visit_orders_match_networkx_traversals(self, nx, vertex_count, edge_count, seed):
        # Com a mesma ordem de vizinhos, as ordens precisam coincidir posição a posição.
        graph = random_graph(vertex_count, edge_count, seed)
        oracle = to_networkx(nx, graph)

        for origin in sample_origins(graph, seed + 2, 5):
            assert bfs(graph, origin)["visited_order"] == [origin] + [
                target for _, target in nx.bfs_edges(oracle, origin)
            ]
            result = dfs(graph, origin)
            assert result["visited_order"] == list(nx.dfs_preorder_nodes(oracle, origin))
            assert result["finish_order"] == list(nx.dfs_postorder_nodes(oracle, origin))


@pytest.mark.parametrize("key", ["local", "lines", "full"])
class TestRedeReal:
    """Instâncias pequena, intermediária e completa carregadas do SQLite."""

    def test_reach_matches_networkx_descendants(self, nx, real_instances, key):
        graph = real_instances[key]
        oracle = to_networkx(nx, graph)
        origins = sample_origins(graph, 2026, 200 if key != "full" else 15)
        if graph.has_stop(LOCAL_ORIGIN):
            origins.append(LOCAL_ORIGIN)

        for origin in origins:
            expected = nx.descendants(oracle, origin) | {origin}
            assert set(dfs(graph, origin)["visited_order"]) == expected
            assert set(bfs(graph, origin)["visited_order"]) == expected

    def test_visit_orders_match_networkx_traversals(self, nx, real_instances, key):
        graph = real_instances[key]
        oracle = to_networkx(nx, graph)

        for origin in sample_origins(graph, 2027, 3):
            assert bfs(graph, origin)["visited_order"] == [origin] + [
                target for _, target in nx.bfs_edges(oracle, origin)
            ]
            result = dfs(graph, origin)
            assert result["visited_order"] == list(nx.dfs_preorder_nodes(oracle, origin))
            assert result["finish_order"] == list(nx.dfs_postorder_nodes(oracle, origin))

    def test_queries_match_networkx(self, nx, real_instances, key):
        graph = real_instances[key]
        oracle = to_networkx(nx, graph)
        queries = sample_queries(
            graph, 2028, 15, lambda origin: nx.descendants(oracle, origin) | {origin}
        )
        # Consulta publicada em docs/BENCHMARK_RESULTADOS.md.
        queries.append(benchmark_script.QUERIES[key])

        outcomes = set()
        for origin, destination in queries:
            by_level, by_depth = bfs(graph, origin, destination), dfs(graph, origin, destination)
            reachable = nx.has_path(oracle, origin, destination)
            outcomes.add(reachable)
            assert by_level["found"] is by_depth["found"] is reachable
            if reachable:
                assert by_level["distance"] == nx.shortest_path_length(oracle, origin, destination)
                assert by_level["distance"] <= by_depth["distance"]
                assert_valid_path(graph, by_level["path"], origin, destination)
                assert_valid_path(graph, by_depth["path"], origin, destination)
        assert True in outcomes


class TestDesempenho:
    """Os tempos ficam em scripts/benchmark.py. Aqui se fixa o trabalho, que não oscila."""

    @pytest.mark.parametrize("vertex_count", benchmark_script.SYNTHETIC_SIZES)
    @pytest.mark.parametrize("search", SEARCHES)
    def test_traversal_work_is_exactly_v_plus_e(self, search, vertex_count):
        # Mesmos grafos medidos pelo benchmark: cada vértice é processado uma vez
        # e cada aresta examinada uma vez, então o trabalho cresce com V + E.
        graph = synthetic_graph(vertex_count)
        assert graph.vertex_count() == vertex_count
        assert graph.edge_count() == round(benchmark_script.EDGE_RATIO * vertex_count)

        result = search(graph, benchmark_script.SYNTHETIC_ORIGIN)
        assert result["processed_count"] == vertex_count
        assert result["edges_examined"] == graph.edge_count()
