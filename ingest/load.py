"""Load raw CSV exports into DuckDB's `raw` schema, exactly as received.

Raw tables keep every column as text plus load metadata. Cleaning happens in
dbt, so the raw layer is always a faithful, replayable copy of the source.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
WAREHOUSE = ROOT / "data" / "warehouse.duckdb"
TABLES = ["customers", "products", "orders", "order_items"]


def load(raw_dir: Path = RAW, warehouse: Path = WAREHOUSE) -> dict[str, int]:
    warehouse.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(warehouse))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    counts = {}
    for t in TABLES:
        src = raw_dir / f"{t}.csv"
        con.execute(
            f"""
            CREATE OR REPLACE TABLE raw.{t} AS
            SELECT *, current_timestamp AS _loaded_at, '{src.name}' AS _source_file
            FROM read_csv(?, header = true, all_varchar = true)
            """,
            [str(src)],
        )
        counts[t] = con.execute(f"SELECT count(*) FROM raw.{t}").fetchone()[0]
    con.close()
    return counts


if __name__ == "__main__":
    for table, n in load().items():
        print(f"raw.{table:<12} {n:>7,} rows")
