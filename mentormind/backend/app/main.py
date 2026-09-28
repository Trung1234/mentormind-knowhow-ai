from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mentormind.backend.app.config import get_settings
from mentormind.backend.app.routers import health

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
