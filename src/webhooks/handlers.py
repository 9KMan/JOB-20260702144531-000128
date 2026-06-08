"""Standalone webhook blueprint kept for backwards compatibility with the
``/webhooks/<source>`` path. The v1 router is the canonical entry point.
"""
from fastapi import APIRouter

from src.api.v1.webhooks import router as v1_router

router = APIRouter(prefix="/webhooks", tags=["webhooks-legacy"])
router.include_router(v1_router)
