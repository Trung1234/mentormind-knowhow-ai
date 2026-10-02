"""knowhow kg lifecycle commands."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager

import typer

from mentormind.core.config import get_settings
from mentormind.knowledge_base.kg.client import Neo4jGraph
from mentormind.knowledge_base.kg.loader import KnowledgeGraphLoader
from mentormind.knowledge_base.sigma.adapter import CsvSigmaAdapter
from mentormind.knowledge_base.store.profile_store import ProfileStore
from mentormind.knowledge_base.store.vector_store import get_vector_store

app = typer.Typer(help="Knowledge graph publication and statistics", no_args_is_help=True)


@contextmanager
def _loader() -> Iterator[KnowledgeGraphLoader]:
    graph = Neo4jGraph()
    try:
        yield KnowledgeGraphLoader(graph, get_vector_store())
    finally:
        graph.close()


@app.command("init")
def init_graph() -> None:
    graph = Neo4jGraph()
    try:
        graph.init()
    finally:
        graph.close()
    typer.echo("Neo4j schema initialized")


@app.command("load-profiles")
def load_profiles() -> None:
    with _loader() as loader:
        profiles = ProfileStore(get_settings().profile_db).list_profiles()
        result = loader.load_profiles(profiles)
    typer.echo(json.dumps(result.__dict__))


@app.command("load-sigma")
def load_sigma() -> None:
    with _loader() as loader:
        count = loader.load_sigma(CsvSigmaAdapter(get_settings().sigma_csv_dir))
    typer.echo(f"Loaded {count} Sigma lots")


@app.command("stats")
def stats() -> None:
    with _loader() as loader:
        typer.echo(json.dumps(loader.stats()))
