"""Kind-agnostic provider interface: what a VLM, an LLM (and any future kind) share.

Each kind subclasses :class:`ProviderBase` in its own package
(``mentormind.processing.vlm.providers`` for VLM, ``mentormind.core.llm`` for LLM) and adds its
call surface. Adding a provider never touches business logic (constitution Điều 5): subclass the
kind's base, register it under a name, done.
"""

from __future__ import annotations

from abc import ABC
from typing import ClassVar, Self

from mentormind.core.providers.models import ProviderConfig
from mentormind.core.providers.transport.http import HttpClient


class ProviderBase(ABC):
    """A configurable provider: a registry name, a cloud flag, built from a config."""

    #: Human label of the provider kind, used in error messages ("VLM", "LLM").
    kind: ClassVar[str] = ""

    #: Registry name this instance was built under (goes into ``model_info.provider``).
    name: str
    #: True when calls leave the premises — DataGuard refuses confidential data (Điều 2).
    is_cloud: bool

    @classmethod
    def from_config(cls, config: ProviderConfig, http: HttpClient | None = None) -> Self:
        """Build a ready instance from ``config`` (the registry's only entry point)."""
        raise NotImplementedError(f"{cls.__name__} must implement from_config()")

    @classmethod
    def api_key_env(cls, name: str) -> str | None:
        """Secret variable holding the API key when built as ``name`` (None: keyless)."""
        return None
