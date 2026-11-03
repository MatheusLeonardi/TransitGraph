def dfs(graph, origin, destination=None):

    if not graph.has_stop(origin):
        raise ValueError("Parada de origem inexistente.")

    if destination is not None and not graph.has_stop(destination):
        raise ValueError("Parada de destino inexistente.")

    stack = [origin]

    discovered = {origin}

    parent = {origin: None}

    visit_order = []

    while stack:

        current = stack.pop()

        visit_order.append(current)

        if current == destination:
            break

        neighbors = graph.get_neighbors(current)

        # Inverte para preservar a ordem de inserção
        for neighbor in reversed(neighbors):

            if neighbor not in discovered:

                discovered.add(neighbor)
                parent[neighbor] = current
                stack.append(neighbor)

    path = None

    if destination is not None and destination in visit_order:
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
        "visited_count": len(visit_order),
        "processed_count": len(visit_order),
        "discovered_count": len(discovered),
        "reachable_stops": visit_order,
        "path": path,
        "distance": len(path) - 1 if path else None,
        "found": path is not None if destination is not None else None
    }
