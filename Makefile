.PHONY: run css css-watch sprite favicons test lint format check seed seed-clear warm search expire

run:
	uv run python manage.py runserver

seed:
	uv run python manage.py seed_demo

seed-clear:
	uv run python manage.py seed_demo --clear

warm:
	uv run python manage.py warm_cache

search:
	uv run python manage.py rebuild_search

expire:
	uv run python manage.py expire_orders

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
