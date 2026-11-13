.PHONY: run css css-watch sprite favicons test lint format check

run:
	uv run python manage.py runserver

css:
	pnpm run build:css

css-watch:
	pnpm run watch:css

sprite:
	uv run python scripts/build_sprite.py

favicons:
	uv run python scripts/make_favicons.py static/logo.webp static/favicon

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run pytest
