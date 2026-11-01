def dfs(graph, origin):

    if not graph.has_stop(origin):
        raise ValueError("Parada de origem inexistente.")

    stack = [origin]

    visited = set()

    visit_order = []

    while stack:

        current = stack.pop()

        if current in visited:
            continue

        visited.add(current)

        visit_order.append(current)

        neighbors = graph.get_neighbors(current)

        # Inverte para preservar a ordem de inserção
        for neighbor in reversed(neighbors):

            if neighbor not in visited:

                stack.append(neighbor)

    return {
        "algorithm": "DFS",
        "origin": origin,
        "visited_order": visit_order,
        "visited_count": len(visited),
        "reachable_stops": visit_order
    }