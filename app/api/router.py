from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import approvals, browser, content, health, social, tasks

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(tasks.router)
api_router.include_router(approvals.router)
api_router.include_router(browser.router)
api_router.include_router(content.router)
api_router.include_router(social.router)
