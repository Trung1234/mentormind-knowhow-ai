"""Configuration: typed settings from the environment and the secret lookup (spec 01 FR-03)."""

from mentormind.core.config.secrets import lookup_secret
from mentormind.core.config.settings import (
    REPO_ROOT,
    SECRETS_FILE,
    JsonMode,
    Settings,
    get_settings,
)

__all__ = ["REPO_ROOT", "SECRETS_FILE", "JsonMode", "Settings", "get_settings", "lookup_secret"]
