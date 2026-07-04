"""Configuration loader for the ``app/`` plane.

Re-exports the settings object defined in :mod:`src.config` so that
production code can ``from app.config import settings`` without
knowing about the data-layer location.
"""

from src.config import Settings, get_settings

__all__ = ["Settings", "get_settings", "settings"]


def _module_settings() -> Settings:
    """Lazy accessor — calling ``settings`` returns a cached Settings."""
    return get_settings()


settings = _module_settings()