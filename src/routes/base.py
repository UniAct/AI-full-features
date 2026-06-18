"""
Base routes module for application health checks and metadata.
"""

from fastapi import APIRouter, Depends
from helpers.config import get_settings, Settings

base_router = APIRouter(
    prefix="/api/v1",
    tags=["api_v1"],
)


@base_router.get("/")
async def welcome(app_settings: Settings = Depends(get_settings)):
    """
    Returns application metadata and a welcome message.
    """
    return {
        "app_name": app_settings.APP_NAME,
        "app_version": app_settings.APP_VERSION
    }

