from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelRequest:
    role: str
    prompt: str
    context: str = ""
    model: str | None = None
    temperature: float = 0.0


class LLMProvider(ABC):
    """Provider-neutral interface. Business logic must depend on this, not a vendor SDK."""

    name: str = "abstract"

    @abstractmethod
    def generate(self, request: ModelRequest) -> str:
        raise NotImplementedError


class LocalLLMProvider(LLMProvider):
    name = "local"

    def __init__(self, endpoint: str = "http://127.0.0.1:11434"):
        self.endpoint = endpoint

    def generate(self, request: ModelRequest) -> str:
        raise RuntimeError("Local LLM adapter is not configured yet. The provider interface is ready; no network call is made by KOS V1.")


class CloudLLMProvider(LLMProvider):
    """Base adapter for optional cloud providers; credentials stay outside source code."""

    name = "cloud"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    def generate(self, request: ModelRequest) -> str:
        raise RuntimeError("No cloud vendor is enabled. Configure a concrete adapter explicitly before sending book text externally.")


@dataclass
class ModelRouting:
    fast_model: str | None = None
    extraction_model: str | None = None
    quality_model: str | None = None

    def for_role(self, role: str) -> str | None:
        return {"fast": self.fast_model, "extraction": self.extraction_model, "quality": self.quality_model}.get(role)
