from __future__ import annotations

import asyncio

import pytest

from app.core.redaction import redact_secrets
from app.integrations.contracts import (
    AIProvider,
    AIRequest,
    AIResponse,
    IntegrationFailure,
    PrivateDocumentStorage,
    ProcurementSource,
    PublicOpportunity,
    StoredObject,
    run_with_timeout,
)


class FailingProcurementSource:
    async def search(self, query: str) -> list[PublicOpportunity]:
        raise IntegrationFailure(
            integration="procurement",
            code="source_unavailable",
            retryable=True,
        )

    async def get_by_id(self, external_id: str) -> PublicOpportunity:
        raise NotImplementedError


class FailingAIProvider:
    async def generate(self, request: AIRequest) -> AIResponse:
        raise IntegrationFailure(
            integration="ai",
            code="provider_unavailable",
            retryable=True,
        )


class FailingStorage:
    async def put(
        self, object_key: str, content: bytes, media_type: str
    ) -> StoredObject:
        raise IntegrationFailure(
            integration="storage",
            code="storage_unavailable",
            retryable=False,
        )

    async def get(self, object_key: str) -> bytes:
        raise NotImplementedError

    async def delete(self, object_key: str) -> None:
        raise NotImplementedError


@pytest.mark.asyncio
async def test_procurement_failure_is_typed_and_does_not_expose_details():
    source: ProcurementSource = FailingProcurementSource()

    with pytest.raises(IntegrationFailure) as error:
        await run_with_timeout("procurement", 1, source.search("water"))

    assert error.value.code == "source_unavailable"
    assert "ticket" not in str(error.value).lower()


@pytest.mark.asyncio
async def test_ai_provider_failure_is_typed():
    provider: AIProvider = FailingAIProvider()

    with pytest.raises(IntegrationFailure) as error:
        await run_with_timeout("ai", 1, provider.generate(AIRequest(prompt="Review")))

    assert error.value.code == "provider_unavailable"


@pytest.mark.asyncio
async def test_storage_failure_is_typed():
    storage: PrivateDocumentStorage = FailingStorage()

    with pytest.raises(IntegrationFailure) as error:
        await run_with_timeout("storage", 1, storage.put("private/doc.pdf", b"pdf", "application/pdf"))

    assert error.value.code == "storage_unavailable"


@pytest.mark.asyncio
async def test_adapter_timeout_is_explicit_and_retryable():
    async def slow_operation():
        await asyncio.sleep(1)

    with pytest.raises(IntegrationFailure) as error:
        await run_with_timeout("ai", 0.001, slow_operation())

    assert error.value.code == "integration_timeout"
    assert error.value.retryable is True


def test_secret_redaction_handles_nested_values_and_url_query_parameters():
    value = {
        "authorization": "Bearer abc",
        "metadata": [{"api_key": "secret", "url": "https://example.test/items?ticket=abc&id=7"}],
    }

    assert redact_secrets(value) == {
        "authorization": "[REDACTED]",
        "metadata": [
            {
                "api_key": "[REDACTED]",
                "url": "https://example.test/items?ticket=%5BREDACTED%5D&id=7",
            }
        ],
    }


def test_settings_reject_non_positive_integration_timeouts():
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(ai_provider_timeout_seconds=0)
