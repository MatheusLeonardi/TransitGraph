
import sqlite3
from pathlib import Path

from backend.algorithms.graph import Graph


def save_graph(graph, db_path):
    """
    Salva vértices, arestas e linhas associadas ao SQLite.
    Substitui os dados anteriores do grafo.
    """

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.executescript("""
            CREATE TABLE IF NOT EXISTS stops (
                stop_id TEXT PRIMARY KEY,
                name TEXT,
                latitude REAL,
                longitude REAL
            );

            CREATE TABLE IF NOT EXISTS edges (
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                PRIMARY KEY (source, target),
                FOREIGN KEY (source) REFERENCES stops(stop_id),
                FOREIGN KEY (target) REFERENCES stops(stop_id)
            );

            CREATE TABLE IF NOT EXISTS edge_routes (
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                route_id TEXT NOT NULL,
                PRIMARY KEY (source, target, route_id),
                FOREIGN KEY (source, target)
                    REFERENCES edges(source, target)
            );
        """)

        # Apagar os dados anteriores
        connection.execute("DELETE FROM edge_routes")
        connection.execute("DELETE FROM edges")
        connection.execute("DELETE FROM stops")

        # Salvar paradas
        stop_rows = []

        for stop_id, data in graph.stops.items():
            stop_rows.append((
                stop_id,
                data.get("name"),
                data.get("latitude"),
                data.get("longitude")
            ))

        connection.executemany(
            """
            INSERT INTO stops
            (stop_id, name, latitude, longitude)
            VALUES (?, ?, ?, ?)
            """,
            stop_rows
        )

        # Salvar arestas
        edge_rows = []

        for source, neighbors in graph.adjacency.items():
            for target in neighbors:
                edge_rows.append((source, target))

        connection.executemany(
            """
            INSERT INTO edges (source, target)
            VALUES (?, ?)
            """,
            edge_rows
        )

        # Salvar linhas associadas às arestas
        route_rows = []

        for (source, target), route_ids in graph.edge_routes.items():
            for route_id in route_ids:
                route_rows.append((source, target, route_id))

        connection.executemany(
            """
            INSERT INTO edge_routes (source, target, route_id)
            VALUES (?, ?, ?)
            """,
            route_rows
        )

    return {
        "stops_saved": len(stop_rows),
        "edges_saved": len(edge_rows),
        "edge_routes_saved": len(route_rows),
        "database": str(db_path)
    }


def load_graph(db_path):
    """
    Carrega o grafo armazenado no SQLite para a memória.
    """

    db_path = Path(db_path)

    if not db_path.exists():
        raise FileNotFoundError(
            f"Banco de dados não encontrado: {db_path}"
        )

    graph = Graph()

    with sqlite3.connect(db_path) as connection:
        # Carregar paradas
        cursor = connection.execute("""
            SELECT stop_id, name, latitude, longitude
            FROM stops
        """)

        for stop_id, name, latitude, longitude in cursor:
            graph.add_stop(
                stop_id,
                name=name,
                latitude=latitude,
                longitude=longitude
            )

        # Carregar arestas
        cursor = connection.execute("""
            SELECT source, target
            FROM edges
        """)

        for source, target in cursor:
            graph.add_edge(source, target)

        # Carregar linhas associadas
        cursor = connection.execute("""
            SELECT source, target, route_id
            FROM edge_routes
        """)

        for source, target, route_id in cursor:
            graph.add_edge(source, target, route_id=route_id)

    return graph
