.PHONY: setup run test docs
setup: ; pip install -r requirements.txt
run: ; python run_pipeline.py
test: ; pytest -q
docs: ; cd transform && DBT_DUCKDB_PATH=../data/warehouse.duckdb dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .
