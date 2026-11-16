.PHONY: run css css-watch sprite favicons test lint format check geo warm search expire recount reconcile stock launch backup purge

run:
	uv run python manage.py runserver

geo:
	uv run python manage.py sync_geo

warm:
	uv run python manage.py warm_cache

search:
	uv run python manage.py rebuild_search

expire:
	uv run python manage.py expire_orders

recount:
	uv run python manage.py recount_purchases

reconcile:
	uv run python manage.py reconcile_counters

stock:
	uv run python manage.py send_back_in_stock

launch:
	uv run python manage.py check_launch

backup:
	uv run python manage.py backup_db --with-media

purge:
	uv run python manage.py purge_otp
	uv run python manage.py purge_sms_logs

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
