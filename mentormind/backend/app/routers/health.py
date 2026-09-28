
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    # In mock/offline mode, report ok for neo4j and postgres
    return {
        "status": "ok",
        "neo4j": "healthy",
        "postgres": "healthy",
    }
