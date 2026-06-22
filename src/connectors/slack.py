"""Slack connector for Composio + LangGraph integration."""

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


def _get_slack_toolset():
    """Get the Slack toolset from Composio."""
    client = _get_composio_client()
    return client.get_toolset("slack")


@tool
def send_slack_message(
    channel: str,
    text: str,
    thread_ts: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a message to a Slack channel.

    Args:
        channel: The channel ID or name to send the message to.
        text: The message text to send.
        thread_ts: Optional timestamp of the parent message to thread the message under.

    Returns:
        Dictionary containing the message result.
    """
    toolset = _get_slack_toolset()

    params: Dict[str, Any] = {
        "channel": channel,
        "text": text,
    }
    if thread_ts:
        params["thread_ts"] = thread_ts

    try:
        result = toolset.execute(action_name="send_message", params=params)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def list_slack_channels(limit: int = 100) -> Dict[str, Any]:
    """List all channels in the Slack workspace.

    Args:
        limit: Maximum number of channels to return (default: 100).

    Returns:
        Dictionary containing the list of channels.
    """
    toolset = _get_slack_toolset()

    try:
        result = toolset.execute(action_name="list_channels", params={"limit": limit})
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
