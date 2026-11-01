
from backend.algorithms.dfs import dfs


def reachable_stops(graph, origin):
    """
    Retorna todas as paradas alcançáveis a partir de uma origem
    utilizando DFS.
    """
    result = dfs(graph, origin)

    return result["reachable_stops"]


def weakly_connected_components(graph):
    """
    Identifica os componentes fracamente conexos do grafo.

    Para isso, considera as arestas como não direcionadas.
    Duas paradas pertencem ao mesmo componente se existe
    um caminho entre elas desconsiderando a direção das arestas.
    """

    # Criar uma representação não direcionada do grafo
    undirected = {stop: set() for stop in graph.adjacency}

    for source, neighbors in graph.adjacency.items():
        for target in neighbors:
            undirected[source].add(target)
            undirected[target].add(source)

    visited = set()
    components = []

    for stop in undirected:

        if stop in visited:
            continue

        component = []
        stack = [stop]
        visited.add(stop)

        while stack:
            current = stack.pop()
            component.append(current)

            for neighbor in undirected[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)

        components.append(component)

    return {
        "component_count": len(components),
        "components": components,
        "largest_component_size": max(
            (len(component) for component in components),
            default=0
        ),
        "isolated_stops": [
            component[0]
            for component in components
            if len(component) == 1
            and not undirected[component[0]]
        ]
    }
