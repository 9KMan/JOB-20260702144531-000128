"""HubSpot connector for Composio + LangGraph integration."""

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


def _get_hubspot_toolset():
    """Get the HubSpot toolset from Composio."""
    client = _get_composio_client()
    return client.get_toolset("hubspot")


@tool
def get_hubspot_contacts(
    limit: int = 100,
    after: Optional[str] = None,
    properties: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Get contacts from HubSpot.

    Args:
        limit: Maximum number of contacts to return (default: 100, max: 100).
        after: Cursor for pagination (use 'after' from previous response).
        properties: List of contact properties to include.

    Returns:
        Dictionary containing the list of contacts and pagination info.
    """
    toolset = _get_hubspot_toolset()

    params: Dict[str, Any] = {"limit": min(limit, 100)}
    if after:
        params["after"] = after
    if properties:
        params["properties"] = properties

    try:
        result = toolset.execute(action_name="get_contacts", params=params)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_hubspot_deals(
    limit: int = 100,
    stage: Optional[str] = None,
    properties: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Get deals from HubSpot.

    Args:
        limit: Maximum number of deals to return (default: 100, max: 100).
        stage: Filter by deal stage (e.g., 'appointmentscheduled').
        properties: List of deal properties to include.

    Returns:
        Dictionary containing the list of deals and pagination info.
    """
    toolset = _get_hubspot_toolset()

    params: Dict[str, Any] = {"limit": min(limit, 100)}
    if stage:
        params["stage"] = stage
    if properties:
        params["properties"] = properties

    try:
        result = toolset.execute(action_name="get_deals", params=params)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_hubspot_tickets(
    limit: int = 100,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """Get tickets from HubSpot.

    Args:
        limit: Maximum number of tickets to return (default: 100, max: 100).
        status: Filter by ticket status (e.g., 'OPEN', 'CLOSED').

    Returns:
        Dictionary containing the list of tickets and pagination info.
    """
    toolset = _get_hubspot_toolset()

    params: Dict[str, Any] = {"limit": min(limit, 100)}
    if status:
        params["status"] = status

    try:
        result = toolset.execute(action_name="get_tickets", params=params)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
