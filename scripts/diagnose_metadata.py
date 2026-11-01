import sqlite3
import zipfile
import csv
import io

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
GTFS_PATH = PROJECT_DIR / "data" / "raw" / "_sptrans_gtfs.zip"
DB_PATH = PROJECT_DIR / "data" / "processed" / "transitgraph.db"

STOP_ID = "301790"

print("=" * 55)
print("DIAGNÓSTICO DOS METADADOS")
print("=" * 55)

# 1. Verificar os dados originais do GTFS
with zipfile.ZipFile(GTFS_PATH, "r") as archive:
    with archive.open("stops.txt") as file:
        reader = csv.DictReader(
            io.TextIOWrapper(file, encoding="utf-8-sig")
        )

        for row in reader:
            if row["stop_id"] == STOP_ID:
                print("\n1. DADOS ORIGINAIS DO GTFS:")
                print(row)
                break

# 2. Verificar os dados salvos no SQLite
with sqlite3.connect(DB_PATH) as connection:
    cursor = connection.execute(
        """
        SELECT stop_id, name, latitude, longitude
        FROM stops
        WHERE stop_id = ?
        """,
        (STOP_ID,)
    )

    print("\n2. DADOS NO SQLITE:")
    print(cursor.fetchone())

    cursor = connection.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN name IS NOT NULL THEN 1 ELSE 0 END) AS com_nome,
            SUM(CASE WHEN latitude IS NOT NULL THEN 1 ELSE 0 END) AS com_latitude,
            SUM(CASE WHEN longitude IS NOT NULL THEN 1 ELSE 0 END) AS com_longitude
        FROM stops
    """)

    print("\n3. RESUMO DOS METADADOS:")
    print(cursor.fetchone())

print("\nDiagnóstico concluído.")