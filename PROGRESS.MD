# AgentGuard — Implementation Progress

Last updated: 2026-03-25

---

## Task Execution Rules
Before starting any task from this file, read `TASK_MANAGER.md`.

- Execute **one task at a time**
- **Stop after each task** and post a status report
- **Wait for user approval** before moving to the next task
- **Update this file** (status + notes) before posting the status report

---

## Status Overview

### Phase 1 — Middleware Changes (Changes 2–7, doing today)

| # | Change | Priority | Status | Notes |
|---|--------|----------|--------|-------|
| 1 | Wire real AI agent (`live_agent.py` → `app.py`) | Day 1 | Done | Swapped import + shape normalization adapter in `run_pipeline()` |
| 2 | Multi-turn attack detection | Day 1 | Done | Sliding window in session_state; trigger: cumulative > 80 AND ≥ 2 scores above 40 (ascending check removed — LLM scores non-deterministic); window cleared on agent switch |
| 3 | Canary token injection | Day 1 | Done | inject_canary() + check_canary_leak() in privacy_layer.py; wired into run_pipeline(); logged to Cosmos |
| 4 | Policy-as-YAML engine | Day 1 | Done | policy_engine.py + 3 YAML configs; wired into run_pipeline(); sidebar deployment profile selector |
| 5 | HIPAA mode | Day 1 | Done | HEALTHCARE_REGEX_PATTERNS + prompt addon in privacy_layer.py; domain passed from pipeline |
| 6 | Legal privilege mode | Day 1 | Done | LEGAL_REGEX_PATTERNS + prompt addon in privacy_layer.py; policy_engine._evaluate_legal() already complete |
| 7 | Compliance report export | Day 1 | Done | `_build_compliance_report()` + `_make_pdf_bytes()` in app.py; reads Cosmos DB live data filtered by policy_deployment; TXT + PDF download; fpdf2 added to requirements.txt |
| 8 | Fine-tuned local model | — | Dropped | Verbal mention in presentation only. No code paths, no env flag. |

### Phase 2 — Production Architecture (begins after Phase 1 is done and tested)

| # | Component | Status | Notes |
|---|-----------|--------|-------|
| A | FastAPI API server | Done | `server.py` with full REST+SSE endpoints; HTML dashboard served from static/ |
| B | Simulated agents (Pearson Hardman) | Done | 4 agents fully wired; 4 scripted events (T+25/50/75/100s); keyboard shortcuts 1-4; live SVG animations |
| C | Simulated agents (Memorial General) | Done | 4 agents; 1 scripted event (pharmacy-agent, T+25s); domain switcher in sim controls |
| D | HTML dashboard migration | Done | Full 5-zone simulation grid in #page-agents; CSS sim styles; /sim/generate endpoint |

---

## Statuses
- **Not started** — untouched
- **In progress** — actively being worked on
- **Done** — implemented and tested
- **Blocked** — waiting on something external
- **Dropped** — consciously removed from scope
- **Skipped** — consciously deferred

---

## Standalone — Dashboard Visual Overhaul
**Status:** Done
**Files:** `static/index.html`, `static/dashboard.css`, `static/dashboard.js`
**What was done:** Complete visual redesign. Deep navy palette (#080d1a bg), DM Sans + DM Mono fonts replacing Saira Condensed + Chivo Mono. Stat cards with CSS mini bar charts + icon circles + badges. Overview middle row restructured to 3-col: Pipeline Integrity donut | Live Feed | Decision Distribution bubbles. Gradient background replaced with solid color. Audit log: client-side caching (8s TTL) + clickable row expand with detail panel. Reputation leaderboard: 15s cache. Escalations: click-to-expand detail view with back button. ACTION BLOCKED animation removed. Pipeline result boxes redesigned. Cosmos DB record renders as a table. All element IDs preserved.

---

## Change 1 — Wire Real AI Agent
**Status:** Done
**Files:** `app.py`, `live_agent.py`
**What was done:** Replaced `SimpleFinancialAgent` import with `get_live_agent` from `live_agent.py`. Added shape normalization adapter in `run_pipeline()` to map `LiveAgent.process_request()` output to the pipeline contract. Extended cache-busting guard to check `agent_id`. Added `self.agent_id = "live-financial-agent"` to `LiveAgent.__init__()`.

---

## Standalone — Agent Reputation Persistence
**Status:** Done
**Files:** `reputation_tracker.py`, `azure_services.py`, `app.py`
**What was done:** Reputation scores now load from Cosmos DB on first agent access and persist on every score change. Added `get_reputation()` and `upsert_reputation()` to `CosmosDBService`. Rewrote `ReputationTracker` to accept `cosmos_service`, load via `_load_from_cosmos()` in `_get_or_create()`, and persist via `_persist()` after every `update_score()`. Cosmos doc: `id=rep_{agent_id}`, `session_id=__reputation__`, contains score, trust level, decision counts, and last 10 score changes. Added `escalation_count` tracking.

---

## Change 2 — Multi-Turn Attack Detection
**Status:** Done
**Files:** `app.py`
**What to do:** Add `conversation_context` to `st.session_state` (sliding window of last 5 messages). In `run_pipeline()`, compute cumulative score across the window. If scores are ascending and cumulative total ≥ 80, apply a boost of up to +40 and recalculate tier.

---

## Change 3 — Canary Token Injection
**Status:** Done
**Files:** `privacy_layer.py`, `app.py`
**What to do:** Add `inject_canary(text, domain)` and `check_canary_leak(agent_output, canary_token)` to `PrivacyLayer`. Domain-specific formats: finance → `canary-{token}@agentguard-sentinel.io`, legal → `MATTER-CANARY-{token}`, healthcare → `MRN-CANARY-{token}`. Wire into `run_pipeline()` — inject before agent call, check after. Store result in audit record and decision history.

---

## Change 4 — Policy-as-YAML Engine
**Status:** Done
**Files:** New `policy_engine.py`, new `agentguard_finance.yaml`, new `agentguard_hipaa.yaml`, new `agentguard_lawfirm.yaml`, `app.py`, `requirements.txt`
**What was done:** Built `PolicyEngine` class with `evaluate()` method supporting three evaluation paths: generic (entity access + bulk export), legal (cross-matter firewall + privilege contamination), healthcare (HIPAA minimum necessary + special category PHI). Three YAML configs created with realistic per-agent rules from SCENARIOS.md. Added `pyyaml` to requirements.txt. Wired into `run_pipeline()`: domain now read from policy engine (replaces hardcoded `domain="finance"`), policy score boosts and tier overrides applied after multi-turn detection. Policy fields logged to Cosmos DB audit record. Added sidebar deployment profile dropdown with dynamic reload.

---

## Change 5 — HIPAA Mode
**Status:** Done
**Files:** `privacy_layer.py`, `app.py`
**What was done:** Added `_HEALTHCARE_REGEX_PATTERNS` (MRN, ICD_CODE, NPI_NUMBER, DEA_NUMBER, INSURANCE_ID, DATE_OF_SERVICE, MEDICATION) and `_HEALTHCARE_PROMPT_ADDON` to `privacy_layer.py`. Extended `detect_and_anonymize()` with `domain` parameter — when `domain="healthcare"`, Azure prompt receives HIPAA instructions and regex patterns run additively. Azure results supplemented with regex catch (belt-and-suspenders for PHI). Metadata tagged with `healthcare_phi_detected` and `phi_types`. Domain read from policy engine at top of `run_pipeline()` and passed to privacy layer.

---

## Change 6 — Legal Privilege Mode
**Status:** Done
**Files:** `privacy_layer.py`, `policy_engine.py`
**What was done:** Added `_LEGAL_REGEX_PATTERNS` (MATTER_REF, BATES_NUMBER, BAR_ID, PRIVILEGE_MARKER) and `_LEGAL_PROMPT_ADDON` to `privacy_layer.py`. When `domain="legal"`, legal patterns run additively and metadata tagged with `legal_entities_detected`, `legal_types`, `privilege_markers_detected`. Policy engine `_evaluate_legal()` (cross-matter firewall, privilege contamination, external access blocking) was already implemented in Change 4.

---

## Change 7 — Compliance Report Export
**Status:** Done
**Files:** `app.py`, `requirements.txt`
**What was done:** Added `_build_compliance_report(profile, cosmos_records)` — reads up to 500 Cosmos DB records, filters by `policy_deployment` key matching the active profile, computes stats (total, auto, escalated, blocked, canary triggers, policy flag counts, PII total). Three domain-specific report formats: TechCorp Finance (SOC 2 framing), Pearson Hardman (bar association / privilege protection framing per SCENARIOS.md), Memorial General (HIPAA OCR framing per SCENARIOS.md). Added `_make_pdf_bytes()` using fpdf2 (lazy import). Added Compliance Report section to dashboard with `st.code()` display + TXT download button + PDF download button with graceful ImportError fallback. Added `fpdf2>=2.7.0` to requirements.txt.

---

## Change 8 — Fine-Tuned Local Model
**Status:** Dropped
**Notes:** Removed from scope. No code paths, no `AGENTGUARD_LOCAL_MODEL` env flag, no `models/` directory. Will be mentioned verbally in the Round 2 presentation as a roadmap item only. Remove any existing scaffolding if found.

---

## Phase 2A — FastAPI API Server
**Status:** Done
**Files:** `server.py`, `pipeline.py`, `static/`
**What was done:** Full FastAPI server with REST + SSE endpoints. Serves HTML/CSS/JS dashboard from `static/`. Key endpoints: `POST /intercept` (SSE streaming pipeline), `POST /confirm`, `POST /profile`, `POST /agent`, `GET /activity`, `GET /metrics`, `GET /escalations`, `GET /reputation`, `GET /health`, `GET /compliance/report`, `GET /session/stats`, `POST /sim/generate`. `pipeline.py` is the shared pipeline called by both `app.py` and `server.py`.

---

## Phase 2B — Simulated Agents (Pearson Hardman)
**Status:** Done
**Files:** `static/dashboard.js`, `static/dashboard.css`, `static/index.html`
**What was done:** Client-driven simulation loop. 4 agents (donna, research-001, research-002, billing) in 2×2 grid with animated SVG lines. 4 scripted events at T+25/50/75/100s. Keyboard shortcuts 1–4 fire scripted events on demand. Routine traffic via `/sim/generate` with canned fallback. Max 2 simultaneous requests (`SIM.activeCount`). Speech bubbles show request text per agent before line animation. Judge panel ("Try It Yourself") with textarea + agent dropdown + queue.

---

## Phase 2C — Simulated Agents (Memorial General)
**Status:** Done
**Files:** `static/dashboard.js`
**What was done:** 4 agents (clinical-doc, scheduling, billing, pharmacy). 1 scripted event at T+25s (pharmacy-agent → psychiatric + substance abuse records → BLOCK). Domain switcher resets sim and repopulates all agent UI.

---

## Phase 2D — HTML Dashboard Migration
**Status:** Done
**Files:** `static/index.html`, `static/dashboard.css`, `static/dashboard.js`
**What was done:** Full HTML/CSS/JS dashboard served from FastAPI. All pages: Overview, Demo Pipeline, Audit Log, Escalations, Analytics, Compliance, Architecture, Agent Reputation, Agent Simulation. Domain switcher posts to `/profile`, reloads YAML with no server restart.

---

## Standalone — Phase 1 End-to-End Audit Fixes
**Status:** Done
**Files:** `risk_scorer.py`, `app.py`, `reputation_tracker.py`, `privacy_layer.py`
**Findings and fixes applied:**
- **F1** `risk_scorer.py:175` — `_RISK_SYSTEM_PROMPT` hardcoded "financial AI agent" for all domains. Replaced with `_RISK_SYSTEM_PROMPT_BASE` + `_RISK_DOMAIN_ADDONS` dict. Domain addon now appended per domain (finance, legal, healthcare). `score()` and `_azure_score()` accept `domain` param; `run_pipeline()` passes `domain=_pipeline_domain`.
- **F2** `app.py:1541` — Step 4 status message hardcoded "financial agent". Fixed to show active `selected_agent_id`.
- **F3** `app.py` audit record — 6 required Cosmos fields missing or named differently. Added `pii_entities_detected`, `prefilter_hit`, `azure_content_safety`, `cumulative_boost`, `result_status` (AUTO-EXECUTE/SOFT CONFIRM/HARD CONFIRM/BLOCKED), `cosmos_logged: True` to the audit record before `log_decision()`. Legacy field names kept for dashboard backwards-compat.
- **F4** `reputation_tracker.py` — `auto_count` not persisted to Cosmos. Added `total_auto` to `_persist()` doc and restored in `_load_from_cosmos()`.
- **F5** `privacy_layer.py` — `inject_canary()` default domain was `"finance"` not `"generic"`. Fixed.
- **F6** (noted, not fixed) `middleware.py` terminal path doesn't pass domain to `detect_and_anonymize()` and has no policy engine. Acceptable for demo — Streamlit is the primary path.

---

## Standalone — Agent Picker + Pipeline Agent ID Fixes
**Status:** Done
**Files:** `app.py`, `policy_engine.py`, `agentguard_finance.yaml`
**What was done:**
- Added `PROFILE_AGENTS` constant in `app.py` mapping each deployment profile to its ordered list of selectable agents.
- Added `selected_agent_id` session state var; initialized to profile default, reset on profile switch via `_on_profile_change()`.
- Added agent picker dropdown (selectbox) in demo tab below the "Request Input" header. Populates dynamically from `PROFILE_AGENTS` for the active profile. Default: donna-agent (legal), clinical-doc-agent (healthcare), live-financial-agent (finance).
- Fixed `run_pipeline()` to use `st.session_state.selected_agent_id` instead of `PROFILE_AGENT_MAP` — agent ID now flows correctly into policy engine, reputation tracker, and Cosmos DB record.
- Renamed `dash_financial_agent` → `live-financial-agent` in `agentguard_finance.yaml` so YAML policy lookup resolves for TechCorp Finance.
- Updated `PROFILE_AGENT_MAP` defaults to match real agent IDs (`live-financial-agent`, `donna-agent`, `clinical-doc-agent`).
- Fixed privilege marker detection in `_evaluate_legal()`: now checks BOTH the raw text (regex) AND `entity_types` list for "PRIVILEGE_MARKER" (backup for when privacy layer has already detected it). Expanded regex to also cover PRIVILEGED AND CONFIDENTIAL and ATTORNEY-EYES-ONLY. Reason message updated to match user-facing format.
- Fixed `_evaluate_healthcare()` early-return path: when `_evaluate_generic()` blocks on a `forbidden_entity`, `minimum_necessary_violation: True` is now set in `policy_flags` before returning — compliance report tracks this as a distinct metric.

---

## Standalone — Live Activity Table + Decision Log Columns
**Status:** Done
**Files:** `app.py`
**What was done:** Rewrote `_render_live_activity()` Cosmos DB table with 14 new columns: Time, Agent, Domain, Deployment, Status, Risk Score, MT Boost, Pre-filter, Content Safety, Canary, Policy Flags, PII Detected, Rep Score, Trust. Added `_DEPLOYMENT_LABELS` and `_FLAG_LABELS` dicts to humanize raw values. Used canonical field names with legacy fallbacks (`pii_entities_detected` / `entity_count`, etc.). Added `mt_boost` field to `decision_history` append so Decision Log table can also display MT Boost.

---

## Standalone — Escalation Table Fix + Confirm Button Wiring
**Status:** Done
**Files:** `app.py`, `azure_services.py`
**What was done:** Root cause: `_render_escalations()` filtered on `r.get("intervention_confirmed")` which was never set — confirm buttons only called `st.success()`. Fix: changed filter to `r.get("tier") in ("soft", "hard")` so all requests requiring human review appear immediately. Added `confirm_decision(record_id, session_id, justification="")` to `CosmosDBService` — fetches existing Cosmos record, stamps `intervention_confirmed=True` + `intervention_timestamp` + `justification`, re-upserts. Wired both soft-confirm and hard-confirm buttons to call it. Escalation table now shows Confirmed (Yes/Pending), Tier, Policy Reason columns.

---

## Standalone — Multi-Turn Detection Robustness Fixes
**Status:** Done
**Files:** `app.py`
**What was done:** Three fixes to make MT detection reliable in demo conditions: (1) Removed `_ascending` requirement — Azure LLM risk scores are non-deterministic; slight score variation (e.g. 72→68→80) silently breaks ascending check. (2) Lowered cumulative threshold from 120 → 80 so two medium-risk prompts reliably trigger. (3) Lowered `_above_40` requirement from 3 → 2. (4) `_on_agent_change()` now calls `ctx_map.pop(new_agent, None)` to clear the MT window for the newly selected agent — prevents stale accumulated scores leaking when switching agents.

---

## Standalone — Out-of-Scope Action Detection
**Status:** Done
**Files:** `policy_engine.py`, `agentguard_hipaa.yaml`, `agentguard_lawfirm.yaml`, `app.py`
**What was done:** Added `_check_scope_violation()` to `PolicyEngine` — reads `out_of_scope_actions` list from agent YAML, matches regex patterns against request text, returns BLOCK decision (score_boost=90) with `agent_scope_violation: True` and `scope_violation_action` in policy_flags. Reason string format: `"{agent_id} is not authorised to {description} — this agent is scoped to {role_description} only."` Called first in `_evaluate_generic()` before entity checks. Added `out_of_scope_actions` to: scheduling-agent (financial transactions, clinical record modification), billing-agent HIPAA (external emails, treatment plan access), pharmacy-agent (billing claims, scheduling), billing-agent legal (case strategy, client communications, audit trail modification). Updated `risk_reasoning` in audit record to use `policy_decision["reason"]` when `agent_scope_violation` flag is set.

---

## Standalone — Agent Simulation Page (Phase 2B/2C)
**Status:** Done — 2026-03-25
**Files:** `server.py`, `static/index.html`, `static/dashboard.css`, `static/dashboard.js`
**What was done:** Full live agent simulation page replacing the static placeholder. 5-zone layout: control bar, 2×2 agent grid with SVG overlay, center middleware node, live feed panel, stats bar. `POST /sim/generate` endpoint generates AI prompts per agent/domain. Callout overlay for scripted dramatic events. `navigateTo('agents')` calls `simInit()`.

---

## Standalone — Sim: Speech Bubbles + Judge Panel
**Status:** Done — 2026-03-25
**Files:** `static/index.html`, `static/dashboard.css`, `static/dashboard.js`
**What was done:**
- **Speech bubbles** (`#sim-bubble-{pos}`): each agent card shows the most recent request text (90 char truncated). Set before line animation so judges read the prompt before seeing the result. Cleared 1.5s after completion.
- **Judge panel** ("Try It Yourself"): textarea + agent dropdown + Send button below live feed. `runJudgeRequest()` runs in parallel to auto-sim — does not touch `SIM.activeCount`. Multiple judge sends queue via `SIM.judgeQueue`, drained in order after each completes.

---

## Standalone — Sim: Speed + Concurrency Fixes
**Status:** Done — 2026-03-25
**Files:** `static/dashboard.js`
**What was done:**
- Removed `activeRequest` gate from `simTick` — sim now fires on every interval regardless of in-flight requests (was causing 25s+ gaps between prompts).
- Added `SIM.activeCount` to cap simultaneous auto-sim pipeline calls at 2. `simTick` skips if `activeCount >= 2`.
- Judge requests use separate `SIM.judgeRunning` + `SIM.judgeQueue` — fully independent of auto-sim concurrency.
- Fixed judge panel: `min-height:0` on `.sim-feed-list` prevents flex overflow hiding the judge panel; textarea spans full panel width; dropdown uses plain text (no ZWJ emoji, which were invisible in Windows OS dropdowns).

---

## Ideas & Notes Log
| Date | Topic | File |
|------|-------|------|
| 2026-03-17 | Initial strategy — market fit, LLM fine-tuning, legal/healthcare pivot | `STRATEGY_NOTES.MD` |
| 2026-03-17 | Full implementation plan (all 8 changes, detailed) | `PLAN.MD` |
| 2026-03-17 | End-use scenarios — Pearson Hardman (legal) and Memorial General (healthcare) — realistic demo data, YAML configs, example prompts, compliance report formats | `SCENARIOS.md` |
| 2026-03-18 | Architecture brainstorm — demo to production, FastAPI layer, simulated agents, Streamlit → HTML migration, locked decisions | `STRATEGY_NOTES.MD` (see memory file) |
