"""HTTP API routers for the Internal Automation Platform.

Each submodule corresponds to a domain area:
  - tasks    — task lifecycle (enqueue, status, cancel)
  - agents   — agent registration and heartbeats
  - runs     — run / execution records
  - review   — review queue for human-in-the-loop approval
"""