.PHONY: install dev api web test check

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

