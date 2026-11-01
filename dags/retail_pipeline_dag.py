"""Airflow DAG: the production schedule for the pipeline.

extract -> load_raw -> dbt_run -> dbt_test -> build_report

`run_pipeline.py` runs the same steps locally and in CI, so the logic is
tested on every push without needing an Airflow deployment.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG

try:  # Airflow 3
    from airflow.providers.standard.operators.bash import BashOperator
except ImportError:  # Airflow 2
    from airflow.operators.bash import BashOperator

PROJECT = "/opt/airflow/retail-data-pipeline"
DBT = f"cd {PROJECT}/transform && dbt {{cmd}} --profiles-dir ."

default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="retail_daily_pipeline",
    description="Daily load of retail exports into the DuckDB warehouse with dbt models and tests",
    start_date=datetime(2026, 1, 1),
    schedule="0 6 * * *",  # 06:00 daily, after overnight exports land
    catchup=False,
    default_args=default_args,
    tags=["retail", "dbt", "duckdb"],
) as dag:
    extract = BashOperator(task_id="extract", bash_command=f"cd {PROJECT} && python -m ingest.generate_raw")
    load_raw = BashOperator(task_id="load_raw", bash_command=f"cd {PROJECT} && python -m ingest.load")
    dbt_run = BashOperator(task_id="dbt_run", bash_command=DBT.format(cmd="run"))
    # Tests run as their own task: a failed data test stops the report from publishing bad numbers.
    dbt_test = BashOperator(task_id="dbt_test", bash_command=DBT.format(cmd="test"))
    report = BashOperator(task_id="build_report", bash_command=f"cd {PROJECT} && python -m reports.build_report")

    extract >> load_raw >> dbt_run >> dbt_test >> report
