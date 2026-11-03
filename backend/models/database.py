
import json
import sqlite3
import zlib
from pathlib import Path

from backend.algorithms.graph import Graph


def save_graph(graph, db_path, metadata=None):
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

            CREATE TABLE IF NOT EXISTS routes (
                route_id TEXT PRIMARY KEY,
                short_name TEXT,
                long_name TEXT
            );

            CREATE TABLE IF NOT EXISTS shapes (
                shape_id TEXT PRIMARY KEY,
                points BLOB NOT NULL
            );

            CREATE TABLE IF NOT EXISTS edge_shapes (
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                route_id TEXT NOT NULL,
                trip_id TEXT NOT NULL,
                shape_id TEXT NOT NULL,
                from_sequence INTEGER NOT NULL,
                to_sequence INTEGER NOT NULL,
                headsign TEXT,
                PRIMARY KEY (source, target, route_id),
                FOREIGN KEY (source, target, route_id)
                    REFERENCES edge_routes(source, target, route_id)
            );

            CREATE TABLE IF NOT EXISTS build_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

        """)

        # Apagar os dados anteriores
        connection.execute("DELETE FROM edge_shapes")
        connection.execute("DELETE FROM shapes")
        connection.execute("DELETE FROM edge_routes")
        connection.execute("DELETE FROM edges")
        connection.execute("DELETE FROM stops")
        connection.execute("DELETE FROM routes")
        connection.execute("DELETE FROM build_metadata")
        # Bancos antigos podem conter o cache viário. Ele agora fica em
        # data/runtime/road_cache.db e não deve fazer parte do grafo versionado.
        connection.execute("DROP TABLE IF EXISTS road_geometry_cache")
        connection.execute("DROP TABLE IF EXISTS road_geometry_rejections")

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

        # Salvar metadados das linhas
        line_rows = [
            (
                route_id,
                data.get("short_name"),
                data.get("long_name")
            )
            for route_id, data in graph.routes.items()
        ]

        connection.executemany(
            """
            INSERT INTO routes (route_id, short_name, long_name)
            VALUES (?, ?, ?)
            """,
            line_rows
        )

        # Salvar pontos das geometrias GTFS
        shape_point_count = sum(
            len(points)
            for points in graph.shape_points.values()
        )

        shape_rows = [
            (
                shape_id,
                sqlite3.Binary(zlib.compress(
                    json.dumps(
                        points,
                        separators=(",", ":")
                    ).encode("utf-8"),
                    level=9
                ))
            )
            for shape_id, points in graph.shape_points.items()
        ]

        connection.executemany(
            """
            INSERT INTO shapes (shape_id, points)
            VALUES (?, ?)
            """,
            shape_rows
        )

        edge_shape_rows = [
            (
                data["source"],
                data["target"],
                data["route_id"],
                data["trip_id"],
                data["shape_id"],
                data["from_sequence"],
                data["to_sequence"],
                data.get("headsign")
            )
            for data in graph.edge_shapes.values()
        ]

        connection.executemany(
            """
            INSERT INTO edge_shapes
            (source, target, route_id, trip_id, shape_id,
             from_sequence, to_sequence, headsign)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            edge_shape_rows
        )

        metadata_rows = [
            (key, json.dumps(value, ensure_ascii=False))
            for key, value in (metadata or graph.metadata).items()
        ]
        connection.executemany(
            "INSERT INTO build_metadata (key, value) VALUES (?, ?)",
            metadata_rows
        )

    return {
        "stops_saved": len(stop_rows),
        "edges_saved": len(edge_rows),
        "edge_routes_saved": len(route_rows),
        "routes_saved": len(line_rows),
        "shape_points_saved": shape_point_count,
        "edge_shapes_saved": len(edge_shape_rows),
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

        # Bancos antigos continuam compatíveis mesmo sem as tabelas GTFS
        # enriquecidas.
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

        if "routes" in table_names:
            cursor = connection.execute("""
                SELECT route_id, short_name, long_name
                FROM routes
            """)

            for route_id, short_name, long_name in cursor:
                graph.add_route(route_id, short_name, long_name)

        if "edge_shapes" in table_names:
            cursor = connection.execute("""
                SELECT source, target, route_id, trip_id, shape_id,
                       from_sequence, to_sequence, headsign
                FROM edge_shapes
            """)

            for row in cursor:
                graph.add_edge_shape(*row)

        if "build_metadata" in table_names:
            graph.metadata = {
                key: json.loads(value)
                for key, value in connection.execute(
                    "SELECT key, value FROM build_metadata"
                )
            }

    return graph
