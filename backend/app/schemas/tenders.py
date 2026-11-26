from pydantic import BaseModel


class TenderItemResponse(BaseModel):
    name: str | None
    description: str | None
    quantity: str | None
    unit: str | None


class TenderDetailResponse(BaseModel):
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
    items: list[TenderItemResponse]
