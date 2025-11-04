# ABOUTME: Health check endpoint for monitoring and status
# ABOUTME: Returns system status, version, database, and LLM provider availability

import os
import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy import text

from ...db import create_db_engine

logger = logging.getLogger(__name__)

router = APIRouter()


def check_database_connection() -> str:
    """
    Check database connectivity.

    Returns:
        "connected" if database is accessible, "error" otherwise
    """
    try:
        engine = create_db_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return "error"


def check_llm_providers() -> Dict[str, str]:
    """
    Check which LLM providers are configured.

    Returns:
        Dict mapping provider name to availability status
    """
    providers = {}

    # Check for API keys in environment
    if os.getenv("OPENAI_API_KEY"):
        providers["openai"] = "available"
    else:
        providers["openai"] = "unavailable"

    if os.getenv("ANTHROPIC_API_KEY"):
        providers["anthropic"] = "available"
    else:
        providers["anthropic"] = "unavailable"

    if os.getenv("GOOGLE_API_KEY"):
        providers["google"] = "available"
    else:
        providers["google"] = "unavailable"

    return providers


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.

    Returns system status, version, database connectivity,
    and LLM provider availability.

    Returns:
        Dict containing:
        - status: "healthy" or "degraded"
        - version: Application version
        - database: Database connection status
        - llm_providers: Dict of provider availability

    Example:
        GET /api/health

        Response:
        {
            "status": "healthy",
            "version": "1.0.0",
            "database": "connected",
            "llm_providers": {
                "openai": "available",
                "anthropic": "available",
                "google": "unavailable"
            }
        }
    """
    # Check database
    db_status = check_database_connection()

    # Check LLM providers
    llm_providers = check_llm_providers()

    # Determine overall status
    # System is healthy if database is connected
    # LLM providers are optional (can work without them)
    status = "healthy" if db_status == "connected" else "degraded"

    return {
        "status": status,
        "version": "1.0.0",
        "database": db_status,
        "llm_providers": llm_providers
    }
