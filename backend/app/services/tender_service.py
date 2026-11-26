from __future__ import annotations

from dataclasses import asdict

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.integrations.contracts import IntegrationFailure
from app.integrations.procurement.mercado_publico import MercadoPublicoClient


async def get_public_tender(external_id: str) -> dict:
    settings = get_settings()
    ticket = settings.procurement_api_ticket
    if ticket is None or not ticket.get_secret_value().strip():
        raise AppError(
            status_code=503,
            code="procurement_ticket_missing",
            message="Mercado Público API is not configured",
        )

    client = MercadoPublicoClient(
        ticket=ticket.get_secret_value(),
        timeout_seconds=settings.procurement_source_timeout_seconds,
    )
    try:
        tender = await client.get_by_id(external_id)
    except IntegrationFailure as exc:
        status_by_code = {
            "tender_not_found": 404,
            "source_timeout": 504,
            "source_ticket_invalid": 503,
            "source_rate_limited": 503,
            "source_invalid_response": 502,
            "source_unavailable": 502,
        }
        messages = {
            "tender_not_found": "No se encontró una licitación con ese código.",
            "source_timeout": "Mercado Público no respondió a tiempo. Intenta nuevamente.",
            "source_ticket_invalid": "La conexión con Mercado Público no está autorizada.",
            "source_rate_limited": "Mercado Público limitó temporalmente las consultas.",
            "source_invalid_response": "Mercado Público devolvió una respuesta no válida.",
            "source_unavailable": "No fue posible consultar Mercado Público.",
        }
        raise AppError(
            status_code=status_by_code.get(exc.code, 502),
            code=exc.code,
            message=messages.get(exc.code, "No fue posible consultar Mercado Público."),
        ) from exc
    return asdict(tender)
