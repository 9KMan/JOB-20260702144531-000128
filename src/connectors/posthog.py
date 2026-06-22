"""PostHog connector for Composio + LangGraph integration."""

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


def _get_posthog_toolset():
    """Get the PostHog toolset from Composio."""
    client = _get_composio_client()
    return client.get_toolset("posthog")


@tool
def get_posthog_events(
    project_id: str,
    after: Optional[str] = None,
    before: Optional[str] = None,
    limit: int = 100,
    event: Optional[str] = None,
) -> Dict[str, Any]:
    """Get events from PostHog.

    Args:
        project_id: The PostHog project ID.
        after: ISO timestamp to get events after.
        before: ISO timestamp to get events before.
        limit: Maximum number of events to return (default: 100).
        event: Filter by event name.

    Returns:
        Dictionary containing the list of events.
    """
    toolset = _get_posthog_toolset()

    params: Dict[str, Any] = {
        "project_id": project_id,
        "limit": limit,
    }
    if after:
        params["after"] = after
    if before:
        params["before"] = before
    if event:
        params["event"] = event

    try:
        result = toolset.execute(action_name="get_events", params=params)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_posthog_feature_flags(
    key: str,
    distinct_id: str,
) -> Dict[str, Any]:
    """Get feature flags for a distinct user ID from PostHog.

    Args:
        key: The feature flag key to evaluate.
        distinct_id: The distinct user ID to get flags for.

    Returns:
        Dictionary containing the feature flag evaluations.
    """
    toolset = _get_posthog_toolset()

    try:
        result = toolset.execute(
            action_name="get_feature_flags",
            params={
                "key": key,
                "distinct_id": distinct_id,
            },
        )
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
