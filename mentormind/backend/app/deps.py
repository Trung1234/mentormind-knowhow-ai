from collections.abc import Iterator
from functools import lru_cache

from mentormind.core.config import get_settings
from mentormind.knowledge_base.kg.client import Neo4jGraph
from mentormind.knowledge_base.kg.loader import KnowledgeGraphLoader
from mentormind.knowledge_base.store.profile_store import ProfileStore
from mentormind.knowledge_base.store.vector_store import get_vector_store


@lru_cache
def get_profile_store() -> ProfileStore:
    settings = get_settings()
    return ProfileStore(db_path=settings.profile_db)


def get_knowledge_loader() -> Iterator[KnowledgeGraphLoader]:
    graph = Neo4jGraph()
    try:
        yield KnowledgeGraphLoader(graph, get_vector_store())
    finally:
        graph.close()
