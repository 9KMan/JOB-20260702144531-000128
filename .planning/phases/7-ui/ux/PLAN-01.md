# Phase 7: UI/UX

## Phase Goal
Define the user interface approach. Two-tier:
1. **Server-side rendered (Jinja2 + vanilla JS)** for the admin pages (dashboard, templates, ingest runs, audit log, users). These are operator-facing, low-interaction, low-traffic.
2. **React (minimal SPA)** for the review queue — operators work through large lists of suggestions, and the in-place approve/reject/edit interactions need real reactivity.

No client-side framework for the admin pages. The dashboard doesn't need a SPA — it needs to render fast and survive without JavaScript for the first paint.

## Layout

```
+----------------------------------------------------------+
|  [Logo] Automation Platform       [User] admin@example.com |
+----------------------------------------------------------+
| Sidebar  |  Main content area                            |
| -------- |                                             |
| Dashbd   |  (page-specific content)                    |
| Templates|                                             |
| Ingest   |                                             |
| Review   |                                             |
| Audit    |                                             |
| Users    |                                             |
+----------------------------------------------------------+
```

Sidebar is fixed-width (220px), main content area is fluid. Color palette:
- Primary: `#2563eb` (blue) — used for buttons, links, active nav
- Success: `#10b981` — approve buttons, "completed" badges
- Warn: `#f59e0b` — "pending review" badges, warnings
- Error: `#ef4444` — reject buttons, "failed" badges
- Background: `#f8fafc` — neutral light gray
- Card: `#ffffff` — white with 1px border
- Text: `#0f172a` (heading), `#475569` (body), `#94a3b8` (muted)

## Pages

### `/admin` — Dashboard

- Stats grid (4 cards): Tasks Today, Pending Review, Active Templates, Active Users
- Recent activity list (last 10 audit events)
- Quick links: "Upload CSV", "Create Template", "Review Queue"

### `/admin/templates` — Template list

- Table: name, version, status (draft/active/archived), last edited, actions
- Top right: "New Template" button → /admin/templates/new
- Per-row: "Edit", "Activate" (if draft), "Archive" (if active), "View History"

### `/admin/templates/:id` — Template detail

- Header: name, current version, status badge
- Tabs: Rules, Prompt, History, Audit
- Rules tab: JSON editor (Monaco editor or CodeMirror) + "Save as Draft" / "Validate" / "Activate" buttons
- Prompt tab: markdown text editor for the LLM prompt (when rules don't fire)
- History tab: list of all versions, diff viewer
- Audit tab: who changed what when

### `/admin/ingest` — Ingest runs

- Table: source, started_at, duration, status (running/success/failed), rows_ingested, rows_failed
- Per-row: "View Errors" (if any), "Re-run"
- Top right: "New Ingest" → upload form (CSV file picker, source name field)

### `/admin/ingest/:id` — Ingest run detail

- Header: source, status, totals
- Tabs: Rows (paginated), Errors (if any), Audit
- Per-row: input → cleaned preview, suggestion (if generated)

### `/admin/review` — Review queue (REACT SPA)

This is the only page that needs real interactivity:
- Paginated list of pending Suggestions (50 per page)
- Per row: input data, suggestion, confidence, "Approve" / "Reject" / "Edit" / "Skip"
- Bulk select: "Approve all with confidence > 0.9"
- Keyboard shortcuts: `A` = approve, `R` = reject, `E` = edit, `J/K` = next/prev
- Filter sidebar: by template, by confidence range, by date

State: server-side pagination + per-row optimistic update on action. No client-side store; refetch the page after each batch of actions.

### `/admin/audit` — Audit log

- Read-only table: timestamp, user, action, resource, status
- Filter row: date range, user, action type, resource type
- Per-row: "View Diff" (modal showing before/after state)
- Export button (CSV download of current filter)

### `/admin/users` — User management

- Table: email, sso_provider, role, last_login, is_active
- Top right: "Invite User" (generates an invite link; user SSO-logs-in and is auto-linked)
- Per-row: "Edit Role", "Deactivate"

## Components (Jinja2 partials)

```file:app/ui/templates/base.html
{# Sidebar layout — shared across all admin pages. #}
```

```file:app/ui/templates/_components/badge.html
{# State badge — colored pill. #}
```

```file:app/ui/templates/_components/data_table.html
{# Generic table with sort + pagination. #}
```

```file:app/ui/templates/_components/pagination.html
{# Page navigation. #}
```

```file:app/ui/templates/_components/filter_bar.html
{# Filter form row above tables. #}
```

```file:app/ui/templates/_components/audit_diff_modal.html
{# Before/after JSON diff viewer. #}
```

## React app (review queue only)

```file:app/ui/static/review.jsx
// Single-file React app for the review queue.
// Loaded only on /admin/review via <script type="module">.
// No build step; uses React from CDN (esm.sh).
```

The React app calls three endpoints:
- `GET /api/review/pending?page=N` — paginated queue
- `POST /api/review/:id/resolve` — approve/reject
- `PATCH /api/review/:id` — edit suggestion before approval

State is held in `useState` per page; we re-fetch after each action batch. No Redux, no React Query — a 200-line component is plenty for this UI.

## Styling

```file:app/ui/static/admin.css
/* Minimal CSS — vanilla, no Tailwind, no preprocessor. */

/* Sidebar layout */
body {
  display: grid;
  grid-template-columns: 220px 1fr;
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* Cards, tables, badges, buttons — see Job-127 admin.css for the full pattern. */
```

All styles in a single ~10KB CSS file. No utility framework. Colors via CSS variables. BEM naming.

## Accessibility

- All interactive elements are `<button>` or `<a>`, never `<div onclick>`.
- Forms have explicit `<label>` for every input.
- Color is never the only indicator — badges include text labels.
- Keyboard navigation works everywhere; focus rings are visible.
- Tab order matches visual order.
- Tables have `<th scope="col">` for screen readers.

## What we explicitly do NOT do

- No dark mode toggle (light theme only for MVP).
- No internationalization (English only).
- No drag-and-drop reordering.
- No infinite scroll (pagination is fine).
- No real-time push (no WebSocket; refresh-by-click is acceptable for an internal tool).
- No animations beyond simple CSS transitions on hover.