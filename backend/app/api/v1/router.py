from fastapi import APIRouter

from app.api.v1 import audit, auth, companies, company, health, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(company.router)
api_router.include_router(users.router)
api_router.include_router(audit.router)
