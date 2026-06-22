"""SEMrush connector for Composio + LangGraph integration."""

import os
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool


def _get_composio_client():
    """Get the Composio client instance."""
    try:
        from composio import Composio
        return Composio()
    except ImportError:
        raise ImportError(
            "Composio client not installed. Install with: pip install composio-langchain"
        )


def _get_semrush_toolset():
    """Get the SEMrush toolset from Composio."""
    client = _get_composio_client()
    return client.get_toolset("semrush")


@tool
def get_semrush_organic_keywords(
    domain: str,
    database: str = "us",
    limit: int = 100,
) -> Dict[str, Any]:
    """Get organic keywords for a domain from SEMrush.

    Args:
        domain: The domain to get keywords for (e.g., 'example.com').
        database: The database to query (e.g., 'us', 'uk', 'de'). Default: 'us'.
        limit: Maximum number of keywords to return (default: 100).

    Returns:
        Dictionary containing the organic keywords data.
    """
    toolset = _get_semrush_toolset()

    try:
        result = toolset.execute(
            action_name="get_organic_keywords",
            params={
                "domain": domain,
                "database": database,
                "limit": limit,
            },
        )
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_semrush_domain_analytics(
    domain: str,
    database: str = "us",
) -> Dict[str, Any]:
    """Get domain analytics from SEMrush.

    Args:
        domain: The domain to get analytics for (e.g., 'example.com').
        database: The database to query (e.g., 'us', 'uk', 'de'). Default: 'us'.

    Returns:
        Dictionary containing the domain analytics data.
    """
    toolset = _get_semrush_toolset()

    try:
        result = toolset.execute(
            action_name="get_domain_analytics",
            params={
                "domain": domain,
                "database": database,
            },
        )
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
