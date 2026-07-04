"""Template + TemplateVersion models (src/ plane mirror).

Re-exports the canonical models from :mod:`app.models.template`.
"""

from app.models.template import Template, TemplateVersion

__all__ = ["Template", "TemplateVersion"]
