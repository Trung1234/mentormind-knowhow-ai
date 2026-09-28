from typing import Dict
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> Dict[str, str]:
    # In mock/offline mode, report ok for neo4j and postgres
    return {
        "status": "ok",
        "neo4j": "healthy",
        "postgres": "healthy",
    }
