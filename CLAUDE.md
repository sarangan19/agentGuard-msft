# AgentGuard — Claude Code Instructions

## Always Do This First
Before starting any work session, read `PROGRESS.MD` to understand what has been completed, what is in progress, and what is next. Do not assume the state of the codebase — check the file.

Read `TASK_MANAGER.md` before executing any task from a task list. The rules in that file govern how tasks are executed — one at a time, with a status report after each, waiting for user approval before proceeding to the next.

After completing any change, update the corresponding entry in `PROGRESS.MD` — change the status from "Not started" → "In progress" → "Done", and add any relevant notes.

## Project Context
AgentGuard is a security middleware layer for AI-to-AI communication. It intercepts requests between AI agents, scores risk, enforces privacy, and provides an audit trail. It was built for the Microsoft AI Unlocked Hackathon (India), and has advanced to Round 2.

The product is being repositioned toward regulated industries — healthcare (HIPAA) and legal (attorney-client privilege). The core technology stays the same; the framing, entity types, and output formats change per domain.

## Implementation Plan
Full details for all 8 planned changes are in `PLAN.MD`. Read it before touching any file it references. Do not implement changes not in `PLAN.MD` unless the user explicitly asks.

## Priority Order
Changes 1–4 and 8 are resolved. Remaining order: **5 → 6 → 7**
- Change 5 (HIPAA mode) — depends on Change 4
- Change 6 (legal privilege mode) — must be built, no longer optional
- Change 7 (compliance report export) — last middleware change before Phase 2
- Change 8 (local model) — **DROPPED**. No code, no env flag. Verbal mention in presentation only. Remove any scaffolding if found.

## Run the App
```bash
# Streamlit (original — always works as fallback)
streamlit run app.py

# FastAPI dashboard (Phase 2 — primary for demos)
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

## Ideas & New Conversations
Whenever the user proposes a new idea, asks a strategic question, or starts a new topic that produces useful output:
- Save it to a new `.MD` file with a descriptive name (e.g., `IDEA_canary_tokens.MD`, `STRATEGY_healthcare.MD`)
- Add a row to the Ideas & Notes Log table in `PROGRESS.MD` pointing to that file
- Do not clutter `PLAN.MD` or `PROGRESS.MD` with raw brainstorming — keep them clean and action-oriented

## File Reference Map
| File | Purpose |
|------|---------|
| `CLAUDE.md` | This file. Instructions for Claude Code. |
| `TASK_MANAGER.md` | Task execution rules — one task at a time, status report format, approval gate. |
| `PROGRESS.MD` | Live progress tracker. Update after every change. |
| `PLAN.MD` | Full implementation plan with code-level detail for all 8 changes. |
| `STRATEGY_NOTES.MD` | Strategic context — market fit, pivot rationale, regulated industries |
| `scenarios.md` | End-use scenarios — Pearson Hardman (legal) and Memorial General (healthcare) |
| **Runtime** | |
| `app.py` | Streamlit app — original dashboard, always-working fallback |
| `server.py` | FastAPI server — serves `static/` and all REST+SSE endpoints |
| `pipeline.py` | Shared pipeline logic — single source of truth, zero Streamlit imports |
| `live_agent.py` | Live agent (Azure OpenAI) — called by pipeline for agent dispatch step |
| **Static dashboard** | |
| `static/index.html` | HTML dashboard — layout and page structure |
| `static/dashboard.css` | Dashboard styles |
| `static/dashboard.js` | Dashboard logic — API client, polling, SSE stream handler, all page rendering |
| **Policy & config** | |
| `policy_engine.py` | YAML policy engine — loads deployment config, evaluates per-agent rules |
| `agentguard_finance.yaml` | TechCorp Finance policy config (`dash_financial_agent`) |
| `agentguard_lawfirm.yaml` | Pearson Hardman policy config (`dash_law_agent`) |
| `agentguard_hipaa.yaml` | Memorial General policy config (`dash_med_agent`) |

## Code Conventions
- Do not remove existing functionality. All changes are additive or optional-path replacements with fallbacks.
- Do not break the existing 5 demo scenarios. Test them mentally against any change before committing.
- Every new risk event must produce a Cosmos DB audit record. Never skip the audit trail.
- Keep the `risk_scorer.py` interface stable — `_azure_score()` and `_heuristic_score()` must continue to work regardless of what new scoring paths are added.
- The `PrivacyLayer` anonymization format `[ENTITY_TYPE_X]` is relied on downstream. Do not change the placeholder format.

## Round 2 Architecture (locked 2026-03-18)
Phase 2 is IN PROGRESS. `server.py`, `pipeline.py`, and `static/` all exist and are functional.
- **Phase 2:** FastAPI server (`server.py`) serves the HTML/CSS/JS dashboard from `static/`. One process, one URL.
- `pipeline.py` is the shared pipeline — both `app.py` and `server.py` call it. Never duplicate pipeline logic in either caller.
- Domain switching: profile dropdown in HTML dashboard posts to `/profile`, reloads YAML — no server restart.
- Simulated agents: hybrid (scripted dramatic moments + AI-generated routine traffic). Build Pearson Hardman (4 agents) completely before Memorial General (3 agents).
- See PROGRESS.MD Phase 2A–2D for full details and the 4 non-negotiable scripted moments.

## Do Not
- Do not hardcode new agent permissions directly in `middleware.py`. Use `policy_engine.py`.
- Do not send real PHI or privileged legal content to any external API in healthcare or legal mode.
- Do not create new UI tabs for internal configuration details like YAML files. Judges need to see outcomes, not config.
- Do not implement any task from PROGRESS.MD or PLAN.MD without the user explicitly asking. Read TASK_MANAGER.md — user approval gates every task.
- Do not duplicate pipeline logic in `app.py` or `server.py` — `pipeline.py` is the single source of truth for the pipeline.

## Codebase Patterns
- `_wrap_fragment(fn)()` — required pattern for any new auto-refreshing Streamlit section. Without it the panel won't update on the configured interval.
- `CosmosDBService` in `azure_services.py` has multiple identical `# ──` separator comment lines — always include extra surrounding context when using the Edit tool on that file to avoid ambiguous matches.
- `ReputationTracker` must be initialised with `cosmos_service=services["cosmos"]` — it has no Cosmos access otherwise and silently falls back to in-memory only.
- Standalone changes outside the numbered plan (e.g. bug fixes, ad-hoc features) go into PROGRESS.MD as `## Standalone — [name]` sections, not appended to existing change entries.
- `PROFILE_AGENT_MAP` in `app.py` maps deployment profile label → dash agent ID (`dash_financial_agent`, `dash_law_agent`, `dash_med_agent`). Use this — never hardcode agent IDs in pipeline code.
- `conversation_context` in session state is a `dict[agent_id, list[int]]`, not a list. Each agent has its own independent sliding window. Trigger: cumulative > 80 AND ≥ 2 scores above 40. No ascending requirement — LLM scores are non-deterministic so strict ordering was unreliable.
- `get_recent_decisions()` filters with `IS_DEFINED(c.tier)` to exclude reputation documents. Any new Cosmos document type that shouldn't appear in the live activity table must not have a `tier` field, or the query must be extended.
- Every Cosmos audit record includes a top-level `domain` field (`finance`, `legal`, `healthcare`). New pipeline paths must set this field.
- Escalations table (`_render_escalations()`) filters on `r.get("tier") in ("soft", "hard")` — NOT `intervention_confirmed`. Confirmed=Yes only appears after the user clicks the confirm button, which calls `CosmosDBService.confirm_decision()`.
- `CosmosDBService.confirm_decision(record_id, session_id, justification="")` — fetches the existing audit record, stamps `intervention_confirmed=True` + `intervention_timestamp`, re-upserts. Requires both `record_id` and `session_id` (partition key).
- `_on_agent_change()` clears the MT sliding window (`conversation_context`) for the newly selected agent. Intentional — prevents stale boost from a prior conversation leaking into a fresh agent selection.
- `out_of_scope_actions` YAML schema: `action` (snake_case key), `description` (verb phrase used in reason string), `role_description` (what the agent IS for), `patterns` (list of Python-compatible regex strings, matched case-insensitively). Checked first in `_evaluate_generic()` before entity access checks.
- `agent_scope_violation: True` in `policy_flags` means the request was outside the agent's role entirely (not just a forbidden entity). When set, `risk_reasoning` in the audit record uses `policy_decision["reason"]` instead of the pre-filter pattern label.
- `fpdf2` is installed (`requirements.txt`). Compliance report PDF export uses it via `_make_pdf_bytes()` in `app.py`. Import lazily inside the function so missing install degrades gracefully.
- `pipeline.py` step callbacks fire as `_cb(step_num, name, data)` in order 1→5: (1) intercept, (2) pii_detection, (3) risk_scoring, (4) agent_dispatch, (5) cosmos_audit. These step numbers map directly to HTML `step-1` through `step-5` in `static/index.html`. Do not renumber them.
- SSE client in `dashboard.js` (`API.streamPipeline`) uses `fetch()` + `ReadableStream`, NOT `EventSource` (EventSource only supports GET). `sse-starlette` sends `\r\n\r\n` as the event delimiter — the client normalises with `buffer.replace(/\r\n/g, '\n')` before splitting on `\n\n`. Do not remove this normalisation.
- Feed detail expand/collapse in `dashboard.js` uses CSS class `.open` on `.feed-detail` (max-height transition), NOT `display:none/block`. The `renderOverviewFeed()` function preserves open panels by checking `querySelectorAll('.feed-detail.open')` before re-rendering. Do not revert to display toggling.
- `--lime` in `dashboard.css` is aliased to `--teal` (`#2dd4bf`) for backward compat — JS-generated classes use `var(--lime)`. Do NOT redefine `--lime` back to lime-green; it must stay teal.
- Dashboard fonts: **DM Sans** (body/display) + **DM Mono** (code/mono). Any new inline `font-family` references in JS should use these, not Saira Condensed or Chivo Mono.
- `dashboard.js` module-level caches: `_auditCache` (8s TTL via `AUDIT_CACHE_TTL`), `_repCache` (15s TTL via `REP_CACHE_TTL`), `_escalationsCache`. Call `invalidateAuditCache()` after any new pipeline write to force fresh audit data.
- Audit table now has **8 columns** (added expand-arrow column as `td:first-child`). `toggleAuditRow(idx, rowEl)` handles row expand/collapse using `display:none` on `.audit-expand-row` elements.
- Escalations page has two views: `#esc-list-view` (default) and `#esc-detail-view` (shown on row click). `escBack()` resets to list view; `navigateTo('escalations')` calls `escBack()` automatically.
- Overview donut IDs (populated by `updateStatCards()`): `donut-total`, `donut-auto-val`, `donut-esc-val`, `donut-block-val`. Bubble IDs: `bub-auto`, `bub-soft`, `bub-hard`, `bub-block`.
- Python file reads on Windows: always `open(file, encoding='utf-8')` — cp1252 codec fails on special chars present in `static/index.html`.
