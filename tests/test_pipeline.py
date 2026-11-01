"""End-to-end tests: run the real pipeline, then check the warehouse."""
import json
import os
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parent.parent
WH = ROOT / "data" / "warehouse.duckdb"


@pytest.fixture(scope="session", autouse=True)
def pipeline():
    subprocess.run([sys.executable, "run_pipeline.py"], cwd=ROOT, check=True)


@pytest.fixture
def con():
    c = duckdb.connect(str(WH), read_only=True)
    yield c
    c.close()


def test_every_injected_issue_is_detected(con):
    from reports.build_report import scorecard
    card = scorecard(con)
    assert all(r["match"] for r in card), [r for r in card if not r["match"]]


def test_no_duplicate_orders_reach_the_marts(con):
    assert con.execute("select count(*) - count(distinct order_id) from marts.fct_orders").fetchone()[0] == 0


def test_revenue_reconciles_to_source(con):
    # Net revenue rebuilt straight from raw text must equal the mart.
    raw = con.execute("""
        with o as (select distinct order_id, status from raw.orders)
        select sum(cast(i.quantity as int) * cast(replace(replace(i.unit_price,'$',''),',','') as decimal(12,2)))
        from raw.order_items i join o using (order_id) where o.status != 'cancelled'
    """).fetchone()[0]
    mart = con.execute("select sum(net_revenue) from marts.fct_orders").fetchone()[0]
    assert abs(float(raw) - float(mart)) < 0.01


def test_cancelled_orders_carry_no_revenue(con):
    assert con.execute("select coalesce(sum(abs(net_revenue)),0) from marts.fct_orders where status='cancelled'").fetchone()[0] == 0


def test_cohort_month_zero_is_100_percent(con):
    assert con.execute("select min(retention_rate) from marts.mart_cohort_retention where months_since_first=0").fetchone()[0] == 1


def test_incremental_rerun_is_idempotent():
    env = {**os.environ, "DBT_DUCKDB_PATH": str(WH)}
    before = duckdb.connect(str(WH), read_only=True).execute("select count(*), sum(net_revenue) from marts.fct_orders").fetchone()
    subprocess.run(["dbt", "run", "--select", "fct_orders", "--profiles-dir", "."], cwd=ROOT / "transform", env=env, check=True, capture_output=True)
    after = duckdb.connect(str(WH), read_only=True).execute("select count(*), sum(net_revenue) from marts.fct_orders").fetchone()
    assert before == after
