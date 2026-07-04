# JOB-128-REWORK — Follow-up Note (2026-07-03)

**Origin:** Bug-investigation session in `tuinui` on 2026-07-03.

**Status of JOB-20260702144531-000128:** No code was ever delivered. Plan files exist in
`~/.hermes/jobs/JOB-20260702144531-000128/job.json` and in
`/home/deploy/squad/build-worker/JOB-20260702144531-000128/.planning/phases/*`,
but no source code has been committed anywhere — neither locally nor pushed to GitHub.

**Operator decision (2026-07-03 session):** File as a Bug-211 sub-family follow-up and stop.
Mark job as REWORK, no further automation runs without human review.

## Bugs to file (when bug tracker is reachable)

1. **`gsd-build.py --rebuild` wave-loop bug.**
   - File: `/home/deploy/.hermes/scripts/gsd-build.py` line 175:
     `status = "pending" if rebuild else ("complete" if is_complete else "pending")`.
   - When `rebuild=True`, every per-wave re-discovery (line 503) marks all plans
     pending again, so waves 4+ re-run phases that already completed.
   - Reproduction: `python3 gsd-build.py JOB-... --rebuild` on any 6-plan job.
   - Expected: rebuild forces pending at initial discovery only; once a plan
     finishes its second time, it stays complete in subsequent re-discoveries.
   - Suggested fix: snapshot `rebuild` semantics so it only applies during the
     initial `discover_plans(worker_dir, rebuild=True)` call, not the re-discovery.

2. **`gsd-execute-plan.py` produces no persistent source.**
   - File: `/home/deploy/.hermes/scripts/gsd-execute-plan.py` (not audited in this session).
   - Evidence: Phase 1 and Phase 2's `app/`, `src/`, `alembic/` Python sources never
     landed on disk in a way that survived `git reset --hard`. The 17 `.pyc` files
     in `__pycache__/` directories prove Python *did* compile the imports, so the
     files existed transiently; they were never committed, and after reset they
     disappeared. Either:
     a) The executor writes files to a temp dir and only commits on success — and
        success-path commit isn't running.
     b) The executor writes to disk but a downstream cleanup step wipes them.
     c) The executor is bypassing the worker_dir entirely and writing somewhere
        else (`/tmp`? `~/.gsd/`?). Needs a code-reading pass to confirm.

3. **Watchdog auto-finalize-on-stale policy is wrong.**
   - Pattern: when a build stalls >2hr with no log, the watchdog flips state to
     APPROVED. This treats "no progress" as "successful completion."
   - For Job-128 this happened on 2026-07-02 19:31:45 with `state: BUILDING → APPROVED`,
     but the build had produced no actual deliverables.
   - For the 2026-07-03 rebuild the same flipped pattern could re-fire on a fresh
     build that hits the empty-log pathology.
   - Suggested fix: a stalled build should transition to `STALLED_BUILD` for human
     review, not `APPROVED`. Auto-finalize should require at least one SUMMARY file
     and one source-file commit before considering the build complete.

## Telegram-message dispatch bugs (already partially identified)

1. `cto-approve` verb has no parser regex.
   - File: `/home/deploy/.hermes/scripts/telegram_poll_commands.py` line 112-114.
   - `A_RE = re.compile(r'^(a|approve|approved|yes|y)\b', re.IGNORECASE)` — does not
     match `cto-approve`, so this script never parses the verb. The agent session
     gets the message as plain text and emits a 32-char conversational reply without
     invoking `approve-dispatch.py`. (Note: this script is the cron poller; the live
     gateway's primary path goes through the LLM agent, which is why the agent
     replied rather than failing silently.)
   - Fix: either widen the regex to include `cto-approve`, or document that this
     command is supposed to be handled by a separate `cto-review-handler.py approve`
     invocation, not the Telegram poller.

2. `a JOB-...` on post-build APPROVED doesn't take the short-circuit.
   - File: `/home/deploy/.hermes/scripts/approve-dispatch.py` line 705-707:
     `current_state in ("IN_REVIEW", "REVIEW", "REVIEW_READY")`.
   - After a build has been auto-finalized to APPROVED, sending `a JOB-...` falls
     through to the pre-build path (spawn plan-generation subagents, transition to
     PLANNING_REVIEW) instead of `finalize_post_build`. This will re-run the entire
     pipeline against an already-built job.
   - Fix: either add `"APPROVED"` to the match tuple (with a check that
     `build_issue_id` exists and all phases have a SUMMARY), or refuse `a` on
     post-build APPROVED with a prompt to use `c` (confirm) or `s` (skip) instead.

## What is NOT a bug, despite appearances

- `tg_bot.py` (in this `tuinui/` repo) is a stand-alone long-poller that would
  409-conflict with the live Hermes gateway on the same bot token. We did not
  start it; if you do, you'll recreate the 409 storm from the 2026-06-30
  incident. Fix is either (a) own bot token from @BotFather, or (b) fold the
  four handlers into `hermes-agent/plugins/platforms/telegram/adapter.py`
  via the gateway's existing dispatch.
- The Telegram 409 Conflict incident note at
  `/home/deploy/tuinui/deploy-notes/2026-06-30-telegram-409-fix.md` is the canonical
  diagnostic for that class of problem; this session did not reproduce it.
