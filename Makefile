.PHONY: install dev api web test check warehouse warehouse-fixtures warehouse-docs

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

