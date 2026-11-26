from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from app.integrations.contracts import IntegrationFailure

_API_URL = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"
_TENDER_URL = (
    "https://www.mercadopublico.cl/Procurement/Modules/RFB/"
    "DetailsAcquisition.aspx?idlicitacion="
)


@dataclass(frozen=True)
class TenderItem:
    name: str | None
    description: str | None
    quantity: str | None
    unit: str | None


@dataclass(frozen=True)
class PublicTender:
    external_id: str
    title: str
    status: str | None
    status_code: str | None
    description: str | None
    buyer_name: str | None
    buyer_code: str | None
    published_at: str | None
    closing_at: str | None
    estimated_amount: str | None
    currency: str | None
    official_url: str
    items: tuple[TenderItem, ...]


def _text(value: Any) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


class MercadoPublicoClient:
    def __init__(
        self,
        *,
        ticket: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.ticket = ticket
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def get_by_id(self, external_id: str) -> PublicTender:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.get(
                    _API_URL,
                    params={"codigo": external_id, "ticket": self.ticket},
                    headers={"Accept": "application/json"},
                )
        except httpx.TimeoutException as exc:
            raise IntegrationFailure(
                integration="mercado_publico",
                code="source_timeout",
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise IntegrationFailure(
                integration="mercado_publico",
                code="source_unavailable",
                retryable=True,
            ) from exc

        if response.status_code in {401, 403}:
            raise IntegrationFailure(
                integration="mercado_publico",
                code="source_ticket_invalid",
                retryable=False,
            )
        if response.status_code == 429:
            raise IntegrationFailure(
                integration="mercado_publico",
                code="source_rate_limited",
                retryable=True,
            )
        if response.is_error:
            raise IntegrationFailure(
                integration="mercado_publico",
                code="source_unavailable",
                retryable=response.status_code >= 500,
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise IntegrationFailure(
                integration="mercado_publico",
                code="source_invalid_response",
                retryable=False,
            ) from exc

        if not isinstance(payload, dict):
            raise IntegrationFailure(
                integration="mercado_publico",
                code="source_invalid_response",
                retryable=False,
            )
        records = payload.get("Listado")
        if not isinstance(records, list):
            raise IntegrationFailure(
                integration="mercado_publico",
                code="source_invalid_response",
                retryable=False,
            )
        if not records:
            raise IntegrationFailure(
                integration="mercado_publico",
                code="tender_not_found",
                retryable=False,
            )
        record = records[0]
        if not isinstance(record, dict):
            raise IntegrationFailure(
                integration="mercado_publico",
                code="source_invalid_response",
                retryable=False,
            )

        title = _text(record.get("Nombre"))
        returned_id = _text(record.get("CodigoExterno"))
        if not title or returned_id != external_id:
            raise IntegrationFailure(
                integration="mercado_publico",
                code="source_invalid_response",
                retryable=False,
            )

        buyer = record.get("Comprador")
        buyer = buyer if isinstance(buyer, dict) else {}
        dates = record.get("Fechas")
        dates = dates if isinstance(dates, dict) else {}
        item_group = record.get("Items")
        item_group = item_group if isinstance(item_group, dict) else {}
        source_items = item_group.get("Listado")
        if not isinstance(source_items, list):
            source_items = []
        items = tuple(
            TenderItem(
                name=_text(item.get("NombreProducto")),
                description=_text(item.get("Descripcion")),
                quantity=_text(item.get("Cantidad")),
                unit=_text(item.get("UnidadMedida")),
            )
            for item in source_items[:25]
            if isinstance(item, dict)
        )
        code = returned_id
        return PublicTender(
            external_id=code,
            title=title,
            status=_text(record.get("Estado")),
            status_code=_text(record.get("CodigoEstado")),
            description=_text(record.get("Descripcion")),
            buyer_name=_text(buyer.get("NombreOrganismo")),
            buyer_code=_text(buyer.get("CodigoOrganismo")),
            published_at=_text(dates.get("FechaPublicacion")),
            closing_at=_text(dates.get("FechaCierre") or record.get("FechaCierre")),
            estimated_amount=_text(record.get("MontoEstimado")),
            currency=_text(record.get("Moneda")),
            official_url=f"{_TENDER_URL}{quote(code, safe='')}",
            items=items,
        )
