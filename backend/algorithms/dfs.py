def dfs(graph, origin, destination=None):

    if not graph.has_stop(origin):
        raise ValueError("Parada de origem inexistente.")

    if destination is not None and not graph.has_stop(destination):
        raise ValueError("Parada de destino inexistente.")

    # Cada quadro retoma os vizinhos depois do retorno de um filho.
    stack = [(origin, iter(graph.adjacency[origin]))]
    parent = {origin: None}
    visit_order = [origin]
    finish_order = []
    edges_examined = 0

    while stack and visit_order[-1] != destination:
        current, neighbors = stack[-1]
        for neighbor in neighbors:
            edges_examined += 1
            if neighbor not in parent:
                parent[neighbor] = current
                visit_order.append(neighbor)
                stack.append((neighbor, iter(graph.adjacency[neighbor])))
                break
        else:
            stack.pop()
            finish_order.append(current)

    path = None

    if destination is not None and destination in parent:
        path = []
        current = destination

        while current is not None:
            path.append(current)
            current = parent[current]

        path.reverse()

    return {
        "algorithm": "DFS",
        "origin": origin,
        "destination": destination,
        "visited_order": visit_order,
        "finish_order": finish_order,
        "visited_count": len(visit_order),
        "processed_count": len(visit_order),
        "discovered_count": len(parent),
        "edges_examined": edges_examined,
        "reachable_stops": visit_order,
        "path": path,
        "distance": len(path) - 1 if path else None,
        "found": path is not None if destination is not None else None
    }
