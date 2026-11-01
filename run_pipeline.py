"""Run the whole pipeline locally, in the same order as the Airflow DAG:
extract (generate) -> load raw -> dbt build (models + tests) -> report.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from ingest.generate_raw import generate  # noqa: E402
from ingest.load import load  # noqa: E402


def step(name, fn):
    t = time.perf_counter()
    out = fn()
    print(f"✔ {name:<28} {time.perf_counter() - t:5.2f}s")
    return out


def dbt_build():
    env = {**os.environ, "DBT_DUCKDB_PATH": str(ROOT / "data" / "warehouse.duckdb")}
    r = subprocess.run(["dbt", "build", "--profiles-dir", "."], cwd=ROOT / "transform", env=env,
                       capture_output=True, text=True)
    summary = [l for l in r.stdout.splitlines() if "Done." in l]
    if r.returncode != 0:
        print(r.stdout[-3000:])
        raise SystemExit("dbt build failed")
    return summary[-1].split("Done.")[-1].strip() if summary else ""


if __name__ == "__main__":
    t0 = time.perf_counter()
    step("extract (generate raw)", generate)
    step("load raw -> DuckDB", load)
    print("  dbt:", step("dbt build (models + tests)", dbt_build))
    from reports.build_report import build
    step("report + charts", build)
    print(f"Pipeline finished in {time.perf_counter() - t0:.1f}s")
