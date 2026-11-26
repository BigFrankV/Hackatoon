from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, TypeVar

T = TypeVar("T")


class IntegrationFailure(Exception):
    def __init__(
        self,
        *,
        integration: str,
        code: str,
        retryable: bool,
    ) -> None:
        self.integration = integration
        self.code = code
        self.retryable = retryable
        super().__init__(f"{integration} integration failed ({code})")


class IntegrationTimeoutError(IntegrationFailure):
    def __init__(self, integration: str) -> None:
        super().__init__(
            integration=integration,
            code="integration_timeout",
            retryable=True,
        )


@dataclass(frozen=True)
class PublicOpportunity:
    external_id: str
    title: str
    official_url: str
    source_code: str
    buyer_name: str | None = None
    source_status: str | None = None
    published_at: datetime | None = None
    closing_at: datetime | None = None


class ProcurementSource(Protocol):
    async def search(self, query: str) -> Sequence[PublicOpportunity]: ...

    async def get_by_id(self, external_id: str) -> PublicOpportunity: ...


@dataclass(frozen=True)
class AIRequest:
    prompt: str
    model_code: str | None = None
    system_prompt: str | None = None


@dataclass(frozen=True)
class AIResponse:
    content: str
    provider_code: str
    model_code: str


class AIProvider(Protocol):
    async def generate(self, request: AIRequest) -> AIResponse: ...


class EmbeddingProvider(Protocol):
    async def embed(self, texts: Sequence[str], model_code: str) -> Sequence[Sequence[float]]: ...


@dataclass(frozen=True)
class StoredObject:
    object_key: str
    sha256: str
    byte_size: int
    media_type: str


class PrivateDocumentStorage(Protocol):
    async def put(
        self, object_key: str, content: bytes, media_type: str
    ) -> StoredObject: ...

    async def get(self, object_key: str) -> bytes: ...

    async def delete(self, object_key: str) -> None: ...


async def run_with_timeout(
    integration: str,
    timeout_seconds: float,
    operation: Awaitable[T],
) -> T:
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")
    try:
        return await asyncio.wait_for(operation, timeout=timeout_seconds)
    except TimeoutError as exc:
        raise IntegrationTimeoutError(integration) from exc
