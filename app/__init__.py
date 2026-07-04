"""Canonical application package for the Internal Automation Platform.

The ``app/`` plane contains the production HTTP API, orchestration
logic, schemas, observability hooks, and UI assets. The ``src/`` plane
provides the data-model layer (SQLAlchemy models, async database
session, config) that the ``app/`` plane consumes.
"""

__version__ = "1.0.0"