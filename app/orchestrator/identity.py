"""Identity, authentication, and RBAC.

This module is a thin wrapper over ``app.dependencies`` for cases
where the orchestrator needs to verify permissions **outside** of an
HTTP request (e.g., from a Celery worker).

Authentication modes supported:
  - ``sso``     — corporate SSO (SAML or OIDC), via the ``sso_provider``
                  and ``sso_subject`` columns on ``users``.
  - ``local``   — email + password (hashed with passlib).
  - ``service`` — service accounts for machine-to-machine auth.

RBAC uses a simple role → permission table. A user may have many
roles; a permission is granted if any of the user's roles grants it.
"""

from typing import Iterable


# Permission codes — kept as constants so callers can't typo strings.
PERM_TASK_CREATE = "task:create"
PERM_TASK_CANCEL = "task:cancel"
PERM_REVIEW_SUGGESTION = "review:suggestion"
PERM_AUDIT_READ = "audit:read"
PERM_USER_MANAGE = "user:manage"
PERM_TEMPLATE_EDIT = "template:edit"


class PermissionDeniedError(Exception):
    """Raised when the current actor lacks a required permission."""


def has_permission(role_permissions: Iterable[str], required: str) -> bool:
    """Return True if ``required`` is in the actor's granted permissions."""
    return required in set(role_permissions)


def check_permission(role_permissions: Iterable[str], required: str) -> None:
    """Raise :class:`PermissionDeniedError` if the actor lacks the permission."""
    if not has_permission(role_permissions, required):
        raise PermissionDeniedError(
            f"actor lacks permission {required!r}"
        )