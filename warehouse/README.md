# FluxSG dbt warehouse

This directory contains the bronze loader, silver dbt views, contracted gold
models, custom quality tests, deterministic fixtures, and reproducible analyses
for FluxSG Milestone 3.

From the repository root:

```bash
make warehouse           # build from snapshots in object storage
make warehouse-fixtures  # credential-free deterministic build
make warehouse-docs      # browse docs and lineage on localhost:8080
```

See [`docs/WAREHOUSE.md`](../docs/WAREHOUSE.md) for the architecture, validation
report, live-data evidence, and analysis results.
