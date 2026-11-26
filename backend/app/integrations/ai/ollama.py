from __future__ import annotations

from collections.abc import Sequence

import httpx

from app.integrations.contracts import AIRequest, AIResponse, IntegrationFailure


class OllamaProvider:
    def __init__(
        self,
        base_url: str,
        *,
        chat_model: str,
        embedding_model: str,
        embedding_dimension: int,
        timeout_seconds: float = 120,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.embedding_dimension = embedding_dimension
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def _post(self, path: str, payload: dict) -> dict:
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(path, json=payload)
        except httpx.TimeoutException as exc:
            raise IntegrationFailure(
                integration="ollama",
                code="integration_timeout",
                retryable=True,
            ) from exc
        except httpx.HTTPError as exc:
            raise IntegrationFailure(
                integration="ollama",
                code="provider_unavailable",
                retryable=True,
            ) from exc

        if response.status_code == 404:
            raise IntegrationFailure(
                integration="ollama",
                code="provider_model_unavailable",
                retryable=False,
            )
        if response.is_error:
            raise IntegrationFailure(
                integration="ollama",
                code="provider_unavailable",
                retryable=response.status_code >= 500,
            )
        try:
            result = response.json()
        except ValueError as exc:
            raise IntegrationFailure(
                integration="ollama",
                code="provider_invalid_response",
                retryable=False,
            ) from exc
        if not isinstance(result, dict):
            raise IntegrationFailure(
                integration="ollama",
                code="provider_invalid_response",
                retryable=False,
            )
        return result

    async def generate(self, request: AIRequest) -> AIResponse:
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        result = await self._post(
            "/api/chat",
            {"model": self.chat_model, "messages": messages, "stream": False},
        )
        message = result.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise IntegrationFailure(
                integration="ollama",
                code="provider_invalid_response",
                retryable=False,
            )
        return AIResponse(
            content=content.strip(),
            provider_code="ollama",
            model_code=self.chat_model,
        )

    async def embed(
        self,
        texts: Sequence[str],
        model_code: str,
    ) -> Sequence[Sequence[float]]:
        if model_code != self.embedding_model:
            raise IntegrationFailure(
                integration="ollama",
                code="embedding_model_not_allowed",
                retryable=False,
            )
        if not texts:
            return []

        result = await self._post(
            "/api/embed",
            {"model": model_code, "input": list(texts)},
        )
        embeddings = result.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise IntegrationFailure(
                integration="ollama",
                code="provider_invalid_response",
                retryable=False,
            )

        vectors: list[list[float]] = []
        for embedding in embeddings:
            if (
                not isinstance(embedding, list)
                or len(embedding) != self.embedding_dimension
                or any(not isinstance(value, (int, float)) for value in embedding)
            ):
                raise IntegrationFailure(
                    integration="ollama",
                    code="embedding_dimension_mismatch",
                    retryable=False,
                )
            vectors.append([float(value) for value in embedding])
        return vectors
