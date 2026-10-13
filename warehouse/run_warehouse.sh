#!/usr/bin/env bash
set -euo pipefail

python tools/load_bronze.py
dbt build --profiles-dir .
dbt source freshness --profiles-dir .
dbt docs generate --profiles-dir .
