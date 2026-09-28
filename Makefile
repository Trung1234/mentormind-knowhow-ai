.PHONY: up down check test demo fmt vlm-server-sync vlm-server vlm-server-smoke

up:
	docker compose up -d

down:
	docker compose down

# spec 01 FR-04; constitution Điều 6 (mypy --strict for core/schemas and core/guard).
check:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	uv run mypy --strict mentormind/core/schemas mentormind/core/guard
	uv run pytest

test:
	uv run pytest

demo:
	bash scripts/demo.sh

fmt:
	uv run ruff format .
	uv run ruff check --fix .

# spec 04 FR-08: self-hosted Qwen3-VL server, its own uv project under 3rdparty/vlm_server.
vlm-server-sync:
	cd 3rdparty/vlm_server && uv sync

vlm-server:
	cd 3rdparty/vlm_server && uv run python -m vlm_server serve

vlm-server-smoke:
	cd 3rdparty/vlm_server && uv run python -m vlm_server smoke
