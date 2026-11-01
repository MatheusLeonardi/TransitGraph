from collections import deque


def bfs(graph, origin, destination=None):

    if not graph.has_stop(origin):
        raise ValueError("Parada de origem inexistente.")

    if destination is not None and not graph.has_stop(destination):
        raise ValueError("Parada de destino inexistente.")

    queue = deque([origin])

    visited = {origin}

    parent = {
        origin: None
    }

    visit_order = []

    while queue:

        current = queue.popleft()

        visit_order.append(current)

        if current == destination:
            break

        for neighbor in graph.get_neighbors(current):

            if neighbor not in visited:

                visited.add(neighbor)

                parent[neighbor] = current

                queue.append(neighbor)

    path = None

    if destination is not None and destination in visited:

        path = []

        current = destination

        while current is not None:

            path.append(current)

            current = parent[current]

        path.reverse()

    return {
        "algorithm": "BFS",
        "origin": origin,
        "destination": destination,
        "visited_order": visit_order,
        "visited_count": len(visited),
        "path": path,
        "distance": len(path) - 1 if path else None,
        "found": path is not None if destination is not None else None
    }