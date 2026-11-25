from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Lightweight liveness endpoint."""
    return {"status": "ok"}
