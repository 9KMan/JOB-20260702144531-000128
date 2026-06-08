"""Aggregate router for API v1."""
from fastapi import APIRouter

from src.api.v1 import dashboards, datasets, health, metrics, webhooks

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(datasets.router)
api_router.include_router(dashboards.router)
api_router.include_router(metrics.router)
api_router.include_router(webhooks.router)
