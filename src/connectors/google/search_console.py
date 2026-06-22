"""Google Search Console connector for Composio + LangGraph integration."""

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


def _get_search_console_toolset():
    """Get the Search Console toolset from Composio."""
    client = _get_composio_client()
    return client.get_toolset("google_search_console")


@tool
def get_search_analytics(
    site_url: str,
    start_date: str,
    end_date: str,
    dimensions: Optional[List[str]] = None,
    row_limit: int = 1000,
) -> Dict[str, Any]:
    """Get search analytics data from Google Search Console.

    Args:
        site_url: The site URL (e.g., 'sc-domain:example.com' or 'https://example.com/').
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        dimensions: List of dimensions to group by (e.g., ['query', 'page', 'country']).
        row_limit: Maximum number of rows to return (default: 1000).

    Returns:
        Dictionary containing the search analytics data.
    """
    toolset = _get_search_console_toolset()

    params = {
        "site_url": site_url,
        "start_date": start_date,
        "end_date": end_date,
        "row_limit": row_limit,
    }

    if dimensions:
        params["dimensions"] = dimensions

    try:
        result = toolset.execute(action_name="search_analytics", params=params)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_search_console_sites() -> Dict[str, Any]:
    """Get the list of sites the user has access to in Search Console.

    Returns:
        Dictionary containing the list of sites.
    """
    toolset = _get_search_console_toolset()

    try:
        result = toolset.execute(action_name="list_sites", params={})
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
