import httpx
import pytest

from app.integrations.ai.ollama import OllamaProvider
from app.integrations.contracts import AIRequest, IntegrationFailure


@pytest.mark.asyncio
async def test_chat_uses_configured_model_and_returns_content():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"message": {"content": "Respuesta local"}, "prompt_eval_count": 8, "eval_count": 4},
        )

    provider = OllamaProvider(
        "http://ollama.test",
        chat_model="qwen3:1.7b",
        embedding_model="bge-m3",
        embedding_dimension=1024,
        transport=httpx.MockTransport(handler),
    )

    result = await provider.generate(
        AIRequest(prompt="Pregunta", system_prompt="Responde en español.")
    )

    assert result.content == "Respuesta local"
    assert result.provider_code == "ollama"
    assert result.model_code == "qwen3:1.7b"
    assert requests[0].url.path == "/api/chat"
    assert requests[0].read()


@pytest.mark.asyncio
async def test_embeddings_validate_model_and_vector_dimension():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"embeddings": [[0.1] * 1024]})

    provider = OllamaProvider(
        "http://ollama.test",
        chat_model="qwen3:1.7b",
        embedding_model="bge-m3",
        embedding_dimension=1024,
        transport=httpx.MockTransport(handler),
    )

    vectors = await provider.embed(["texto"], "bge-m3")

    assert len(vectors) == 1
    assert len(vectors[0]) == 1024


@pytest.mark.asyncio
async def test_embedding_dimension_mismatch_is_an_explicit_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2]]})

    provider = OllamaProvider(
        "http://ollama.test",
        chat_model="qwen3:1.7b",
        embedding_model="bge-m3",
        embedding_dimension=1024,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(IntegrationFailure) as error:
        await provider.embed(["texto"], "bge-m3")

    assert error.value.code == "embedding_dimension_mismatch"


@pytest.mark.asyncio
async def test_provider_failure_does_not_expose_upstream_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="private upstream detail")

    provider = OllamaProvider(
        "http://ollama.test",
        chat_model="qwen3:1.7b",
        embedding_model="bge-m3",
        embedding_dimension=1024,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(IntegrationFailure) as error:
        await provider.generate(AIRequest(prompt="Pregunta"))

    assert error.value.code == "provider_unavailable"
    assert "private upstream detail" not in str(error.value)
