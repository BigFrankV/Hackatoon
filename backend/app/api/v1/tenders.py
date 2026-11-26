from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.dependencies.permissions import require_permissions
from app.models.user import User
from app.schemas.tenders import TenderDetailResponse
from app.services import tender_service

router = APIRouter(prefix="/tenders", tags=["tenders"])


@router.get("/{external_id}", response_model=TenderDetailResponse)
async def get_tender_by_id(
    external_id: Annotated[
        str,
        Path(
            min_length=5,
            max_length=40,
            pattern=r"^\d+-\d+-[A-Za-z0-9]+$",
        ),
    ],
    _: User = Depends(require_permissions("tenders.read")),
) -> TenderDetailResponse:
    result = await tender_service.get_public_tender(external_id)
    return TenderDetailResponse(**result)
