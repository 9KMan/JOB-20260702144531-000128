"""Google Ads connector for Composio + LangGraph integration."""

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


def _get_google_ads_toolset():
    """Get the Google Ads toolset from Composio."""
    client = _get_composio_client()
    return client.get_toolset("google_ads")


@tool
def get_google_ads_campaigns(customer_id: str) -> Dict[str, Any]:
    """Get all campaigns for a Google Ads customer.

    Args:
        customer_id: The Google Ads customer ID (e.g., '123-456-7890').

    Returns:
        Dictionary containing the list of campaigns.
    """
    toolset = _get_google_ads_toolset()

    try:
        result = toolset.execute(action_name="get_campaigns", params={"customer_id": customer_id})
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_google_ads_performance_report(
    customer_id: str,
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:
    """Get a performance report for a Google Ads customer.

    Args:
        customer_id: The Google Ads customer ID (e.g., '123-456-7890').
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.

    Returns:
        Dictionary containing the performance report data.
    """
    toolset = _get_google_ads_toolset()

    try:
        result = toolset.execute(
            action_name="get_performance_report",
            params={
                "customer_id": customer_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
