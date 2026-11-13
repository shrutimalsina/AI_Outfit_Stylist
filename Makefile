.PHONY: test lint frontend fixture
test:
	.venv/bin/python -m pytest backend/tests
lint:
	.venv/bin/ruff check backend pipeline scripts
frontend:
	cd frontend && npm ci && npm run build
fixture:
	.venv/bin/python -m scripts.create_fixture
