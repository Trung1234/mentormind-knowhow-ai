.PHONY: up down dev-up dev-shell check test demo fmt vlm-server-sync vlm-server vlm-server-smoke

# spec 01 FR-05 / task D3. COMPOSE_FILES adds overrides, e.g. on the rootless GPU box:
#   make up COMPOSE_FILES="-f docker-compose.yml -f docker-compose.cdi.yml -f docker-compose.devbox.yml"
COMPOSE_FILES ?= -f docker-compose.yml
COMPOSE = docker compose $(COMPOSE_FILES)

# Whole dev stack: mentormind + vlm-server + PostgreSQL/pgvector + Neo4j (profile lite).
up:
	$(COMPOSE) --profile lite up -d --build

down:
	$(COMPOSE) --profile lite down

# Only the two dev containers; VLM_SERVER_AUTOSTART=true also starts the VLM server.
dev-up:
	$(COMPOSE) up -d --build mentormind vlm-server

dev-shell:
	$(COMPOSE) exec mentormind bash

# spec 01 FR-04; constitution art. 6 (mypy --strict for core/schemas and core/guard).
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
