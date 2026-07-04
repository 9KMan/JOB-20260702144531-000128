"""Template version management.

A *template* is a declarative mapping from one input shape to one
output shape. Templates evolve over time — each edit creates a new
``template_version`` row with ``status='draft'``; a manual promotion
flips it to ``status='active'``. Only one active version per template
exists at any time.
"""

from typing import Optional


class TemplateNotFoundError(Exception):
    """Raised when a template or template version cannot be located."""


def latest_active_version(template_id: str, all_versions: list[dict]) -> Optional[dict]:
    """Return the active version of ``template_id``, or None.

    ``all_versions`` is the list of version rows for the template,
    each with keys ``version``, ``status`` (``active`` / ``draft`` /
    ``archived``), and ``payload``.
    """
    actives = [v for v in all_versions if v.get("status") == "active"]
    if not actives:
        return None
    actives.sort(key=lambda v: v["version"], reverse=True)
    return actives[0]


def validate_template_payload(payload: dict) -> list[str]:
    """Return a list of validation errors; empty list = valid.

    A valid template payload declares:
      - ``inputs``: a list of source field names
      - ``outputs``: a list of target field names
      - ``rules``: a non-empty list of mapping rules
    """
    errors: list[str] = []
    if "inputs" not in payload or not isinstance(payload["inputs"], list):
        errors.append("payload.inputs must be a list")
    if "outputs" not in payload or not isinstance(payload["outputs"], list):
        errors.append("payload.outputs must be a list")
    if "rules" not in payload or not isinstance(payload.get("rules"), list):
        errors.append("payload.rules must be a non-empty list")
    elif len(payload["rules"]) == 0:
        errors.append("payload.rules must be a non-empty list")
    return errors