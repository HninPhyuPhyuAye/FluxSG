.PHONY: install dev api web test check warehouse warehouse-fixtures warehouse-docs forecast-data forecast forecast-drift forecast-test

install:
	pnpm install
	python3 -m pip install -e 'services/api[dev]'

dev:
	docker compose up --build

api:
	cd services/api && python3 -m uvicorn app.main:app --reload --port 8000

web:
	pnpm dev

test:
	cd services/api && python3 -m pytest
	pnpm test

check:
	cd services/api && python3 -m ruff check .
	cd services/api && python3 -m pytest
	pnpm lint
	pnpm typecheck
	pnpm build

warehouse:
	docker compose --profile warehouse run --build --rm warehouse

warehouse-fixtures:
	docker compose --profile warehouse run --build --rm warehouse bash -c "python tools/load_bronze.py --fixture-dir fixtures && dbt build --profiles-dir . && dbt source freshness --profiles-dir . && dbt docs generate --profiles-dir ."

warehouse-docs:
	docker compose --profile warehouse run --rm -p 127.0.0.1:8080:8080 warehouse dbt docs serve --profiles-dir . --host 0.0.0.0 --port 8080

forecast-data:
	docker compose --profile forecast run --build --rm forecast fetch --output-dir data/raw

forecast:
	GIT_SHA=$$(git rev-parse HEAD) docker compose --profile forecast run --build --rm forecast train --input-dir data/raw --output-dir artifacts/latest

forecast-drift:
	docker compose --profile forecast run --rm forecast monitor --input-dir data/raw --reference artifacts/latest/training_reference.json --output artifacts/latest/drift_live.json

forecast-test:
	docker compose --profile forecast run --build --rm --entrypoint sh forecast -c "pip install --no-cache-dir '.[dev]' && ruff check src tests && ruff format --check src tests && pytest"
