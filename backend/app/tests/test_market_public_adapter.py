from __future__ import annotations

import httpx
import pytest

from app.integrations.contracts import IntegrationFailure
from app.integrations.procurement.mercado_publico import MercadoPublicoClient


def _tender_payload() -> dict:
    return {
        "Cantidad": 1,
        "Listado": [
            {
                "CodigoExterno": "2415-30-LP26",
                "Nombre": "Adquisición de equipamiento",
                "Descripcion": "Compra de equipamiento municipal.",
                "Estado": "Publicada",
                "CodigoEstado": 5,
                "Comprador": {
                    "NombreOrganismo": "Municipalidad de Prueba",
                    "CodigoOrganismo": 1234,
                },
                "Fechas": {
                    "FechaPublicacion": "2026-11-20T12:00:00",
                    "FechaCierre": "2026-12-04T16:00:00",
                },
                "MontoEstimado": 1500000,
                "Moneda": "CLP",
                "Items": {
                    "Cantidad": 1,
                    "Listado": [
                        {
                            "NombreProducto": "Equipamiento",
                            "Descripcion": "Equipo de prueba",
                            "Cantidad": 2,
                            "UnidadMedida": "Unidad",
                        }
                    ],
                },
            }
        ],
    }


@pytest.mark.asyncio
async def test_get_by_id_maps_official_response_and_sends_ticket_as_query_parameter():
    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        return httpx.Response(200, json=_tender_payload())

    client = MercadoPublicoClient(
        ticket="test-secret-ticket",
        timeout_seconds=2,
        transport=httpx.MockTransport(handler),
    )

    tender = await client.get_by_id("2415-30-LP26")

    assert tender.external_id == "2415-30-LP26"
    assert tender.title == "Adquisición de equipamiento"
    assert tender.status == "Publicada"
    assert tender.status_code == "5"
    assert tender.buyer_name == "Municipalidad de Prueba"
    assert tender.published_at == "2026-11-20T12:00:00"
    assert tender.closing_at == "2026-12-04T16:00:00"
    assert tender.estimated_amount == "1500000"
    assert tender.currency == "CLP"
    assert tender.items[0].quantity == "2"
    request = seen_requests[0]
    assert request.url.params["codigo"] == "2415-30-LP26"
    assert request.url.params["ticket"] == "test-secret-ticket"
    assert "test-secret-ticket" not in request.url.path


@pytest.mark.asyncio
async def test_get_by_id_reports_missing_tender():
    client = MercadoPublicoClient(
        ticket="test-ticket",
        timeout_seconds=2,
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"Listado": []})),
    )

    with pytest.raises(IntegrationFailure) as error:
        await client.get_by_id("2415-30-LP26")

    assert error.value.code == "tender_not_found"
    assert error.value.retryable is False


@pytest.mark.asyncio
async def test_get_by_id_rejects_malformed_response():
    client = MercadoPublicoClient(
        ticket="test-ticket",
        timeout_seconds=2,
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"Listado": {}})),
    )

    with pytest.raises(IntegrationFailure) as error:
        await client.get_by_id("2415-30-LP26")

    assert error.value.code == "source_invalid_response"
    assert error.value.retryable is False


@pytest.mark.asyncio
async def test_get_by_id_surfaces_upstream_timeout_without_ticket_details():
    async def timeout_handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("upstream timed out")

    client = MercadoPublicoClient(
        ticket="test-ticket",
        timeout_seconds=0.01,
        transport=httpx.MockTransport(timeout_handler),
    )

    with pytest.raises(IntegrationFailure) as error:
        await client.get_by_id("2415-30-LP26")

    assert error.value.code == "source_timeout"
    assert error.value.retryable is True
    assert "test-ticket" not in str(error.value)


@pytest.mark.asyncio
async def test_get_by_id_reports_upstream_unavailability():
    async def unavailable_handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("upstream unavailable")

    client = MercadoPublicoClient(
        ticket="test-ticket",
        timeout_seconds=2,
        transport=httpx.MockTransport(unavailable_handler),
    )

    with pytest.raises(IntegrationFailure) as error:
        await client.get_by_id("2415-30-LP26")

    assert error.value.code == "source_unavailable"
    assert error.value.retryable is True
