from functools import lru_cache
from mentormind.backend.app.config import get_settings
from mentormind.knowledge_base.store.profile_store import ProfileStore


@lru_cache
def get_profile_store() -> ProfileStore:
    settings = get_settings()
    return ProfileStore(db_path=settings.profile_db)
