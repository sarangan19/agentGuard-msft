# AgentGuard — Implementation Progress

Last updated: 2026-03-18

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
| 2 | Multi-turn attack detection | Day 1 | Done | Sliding window in session_state, ascending+cumulative≥80 boost in run_pipeline() |
| 3 | Canary token injection | Day 1 | Not started | |
| 4 | Policy-as-YAML engine | Day 1 | Not started | Scaffold now — no dependencies |
| 5 | HIPAA mode | Day 1 | Not started | Depends on Change 4 |
| 6 | Legal privilege mode | Day 1 | Not started | Depends on Changes 4 & 5 |
| 7 | Compliance report export | Day 1 | Not started | |
| 8 | Fine-tuned local model | — | Dropped | Verbal mention in presentation only. No code paths, no env flag. |

### Phase 2 — Production Architecture (begins after Phase 1 is done and tested)

| # | Component | Status | Notes |
|---|-----------|--------|-------|
| A | FastAPI API server | Not started | `server.py` — wraps `AgentGuardMiddleware` with HTTP endpoints |
| B | Simulated agents (Pearson Hardman) | Not started | 4 agents: donna-agent, research-bot-001, research-bot-002, billing-agent |
| C | Simulated agents (Memorial General) | Not started | 3 agents: clinical-doc-agent, billing-agent, pharmacy-agent. After B is complete. |
| D | HTML dashboard migration | Not started | Replaces Streamlit. Static files served from FastAPI. Domain switcher dropdown. |

---

## Statuses
- **Not started** — untouched
- **In progress** — actively being worked on
- **Done** — implemented and tested
- **Blocked** — waiting on something external
- **Dropped** — consciously removed from scope
- **Skipped** — consciously deferred

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
**Status:** Not started
**Files:** `privacy_layer.py`, `app.py`
**What to do:** Add `inject_canary(text, domain)` and `check_canary_leak(agent_output, canary_token)` to `PrivacyLayer`. Domain-specific formats: finance → `canary-{token}@agentguard-sentinel.io`, legal → `MATTER-CANARY-{token}`, healthcare → `MRN-CANARY-{token}`. Wire into `run_pipeline()` — inject before agent call, check after. Store result in audit record and decision history.

---

## Change 4 — Policy-as-YAML Engine
**Status:** Not started
**Files:** New `policy_engine.py`, new `agentguard_finance.yaml`, new `agentguard_hipaa.yaml`, new `agentguard_lawfirm.yaml`
**What to do:** Build `PolicyEngine` class that loads a YAML file and evaluates requests against per-agent rules. Support generic, legal (matter-scoped), and healthcare (HIPAA minimum necessary) evaluation paths. Return structured `policy_decision` dict with `allowed`, `reason`, `override_tier`, `score_boost`, and domain-specific `flags`. Dynamic reload on domain switch (no restart). Use realistic data from `SCENARIOS.md` for YAML configs.

---

## Change 5 — HIPAA Mode
**Status:** Not started
**Files:** `privacy_layer.py`
**What to do:** Add `HEALTHCARE_PATTERNS` list with regex for MRN, ICD-10, CPT, NPI, DEA, insurance ID, date of birth. Extend `detect_and_anonymize()` with optional `domain` parameter — when `domain="healthcare"`, run healthcare patterns additively on top of primary detection. Tag results in metadata as `healthcare_phi_detected` and `phi_types`.

---

## Change 6 — Legal Privilege Mode
**Status:** Not started
**Files:** `privacy_layer.py`, `policy_engine.py`
**What to do:** Add `LEGAL_PATTERNS` list (matter references, Bates numbers, bar IDs, privilege markers) to `privacy_layer.py`. Add `_evaluate_legal()` to `PolicyEngine` — enforce cross-matter firewall, block external access per policy, detect bulk document export attempts, flag privilege contamination with `score_boost=50`.

---

## Change 7 — Compliance Report Export
**Status:** Not started
**Files:** `app.py`
**What to do:** Add "Compliance Report" section to Streamlit dashboard. Read live data from `decision_history`. Support three deployment profiles (TechCorp Finance, Pearson Hardman Legal, Memorial General Healthcare) — each generating a domain-appropriate report in the format from `SCENARIOS.md`. PDF export via `fpdf2` with download button, graceful fallback if not installed.

---

## Change 8 — Fine-Tuned Local Model
**Status:** Dropped
**Notes:** Removed from scope. No code paths, no `AGENTGUARD_LOCAL_MODEL` env flag, no `models/` directory. Will be mentioned verbally in the Round 2 presentation as a roadmap item only. Remove any existing scaffolding if found.

---

## Phase 2A — FastAPI API Server
**Status:** Not started — begins after Changes 2–7 are done and tested
**Files:** New `server.py`
**What to do:** Thin HTTP wrapper around `AgentGuardMiddleware`. Endpoints: `POST /intercept`, `POST /confirm`, `GET /status/{id}`, `GET /` (serves HTML dashboard). Auto-generated `/docs` via FastAPI.

---

## Phase 2B — Simulated Agents (Pearson Hardman)
**Status:** Not started — begins after Phase 2A
**Files:** New `simulations/pearson_hardman/` directory
**What to do:** Hybrid simulation — scripted dramatic moments + AI-generated routine traffic. 4 agents: donna-agent, research-bot-001, research-bot-002, billing-agent. Must include these scripted moments:
- research-bot-001 cross-matter access to MATTER-2024-002 → BLOCK, score 98
- donna-agent canary token detection → BLOCK, canary_triggered in Cosmos DB
- billing-agent bulk export attempt → BLOCK

---

## Phase 2C — Simulated Agents (Memorial General)
**Status:** Not started — begins after Phase 2B is complete
**Files:** New `simulations/memorial_general/` directory
**What to do:** 3 agents: clinical-doc-agent, billing-agent, pharmacy-agent. Must include: clinical-doc-agent accessing psychiatric records outside treating specialist context → BLOCK, special category protection logged.

---

## Phase 2D — HTML Dashboard Migration
**Status:** Not started — begins after Phase 2A
**Files:** Static HTML/CSS/JS files served from FastAPI
**What to do:** Replace Streamlit dashboard with the existing HTML dashboard (`page_dashboard_themes.html` as base). Domain switcher dropdown triggers policy engine reload. Real-time Cosmos DB reads. Compliance report export. One server, one URL, no separate Streamlit process.

---

## Ideas & Notes Log
| Date | Topic | File |
|------|-------|------|
| 2026-03-17 | Initial strategy — market fit, LLM fine-tuning, legal/healthcare pivot | `STRATEGY_NOTES.MD` |
| 2026-03-17 | Full implementation plan (all 8 changes, detailed) | `PLAN.MD` |
| 2026-03-17 | End-use scenarios — Pearson Hardman (legal) and Memorial General (healthcare) — realistic demo data, YAML configs, example prompts, compliance report formats | `SCENARIOS.md` |
| 2026-03-18 | Architecture brainstorm — demo to production, FastAPI layer, simulated agents, Streamlit → HTML migration, locked decisions | `STRATEGY_NOTES.MD` (see memory file) |
