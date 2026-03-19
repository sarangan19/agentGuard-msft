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
Changes 1 and 8 are resolved. Remaining order: **2 → 3 → 4 → 5 → 6 → 7**
- Change 2 (multi-turn detection) — first
- Change 3 (canary tokens) — demo moment
- Change 4 (policy-as-YAML) — foundation for 5 and 6
- Change 5 (HIPAA mode) — depends on Change 4
- Change 6 (legal privilege mode) — must be built, no longer optional
- Change 7 (compliance report export) — last middleware change before Phase 2
- Change 8 (local model) — **DROPPED**. No code, no env flag. Verbal mention in presentation only. Remove any scaffolding if found.

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
| `IMPLEMENTATION_PLAN.md` | Earlier planning doc — superseded by `PLAN.MD` for Round 2 |
| `DEMO_GUIDE.md` | Demo walkthrough and scenario guide |
| `scenarios.md` | Test scenarios |
| `fix_list.md` | Known bugs and fixes |

## Code Conventions
- Do not remove existing functionality. All changes are additive or optional-path replacements with fallbacks.
- Do not break the existing 5 demo scenarios. Test them mentally against any change before committing.
- Every new risk event must produce a Cosmos DB audit record. Never skip the audit trail.
- Keep the `risk_scorer.py` interface stable — `_azure_score()` and `_heuristic_score()` must continue to work regardless of what new scoring paths are added.
- The `PrivacyLayer` anonymization format `[ENTITY_TYPE_X]` is relied on downstream. Do not change the placeholder format.

## Round 2 Architecture (locked 2026-03-18)
Phase 1 (middleware changes 2–7) must be complete and tested before Phase 2 begins.
- **Phase 2 target:** FastAPI server (`server.py`) replaces Streamlit as the runtime. HTML/CSS/JS dashboard served as static files from FastAPI. One process, one URL.
- Domain switching: dropdown in HTML dashboard triggers dynamic YAML reload — no server restart.
- Simulated agents: hybrid (scripted dramatic moments + AI-generated routine traffic). Build Pearson Hardman (4 agents) completely before Memorial General (3 agents).
- See PROGRESS.MD Phase 2A–2D for full details and the 4 non-negotiable scripted moments.

## Do Not
- Do not hardcode new agent permissions directly in `middleware.py`. Use `policy_engine.py` once it exists.
- Do not send real PHI or privileged legal content to any external API in healthcare or legal mode.
- Do not create new UI tabs for internal configuration details like YAML files. Judges need to see outcomes, not config.
- Do not implement any task from PROGRESS.MD or PLAN.MD without the user explicitly asking. Read TASK_MANAGER.md — user approval gates every task.
- Do not start Phase 2 (FastAPI, simulated agents, dashboard migration) until all middleware changes (2–7) are done and tested.

## Codebase Patterns
- `_wrap_fragment(fn)()` — required pattern for any new auto-refreshing Streamlit section. Without it the panel won't update on the configured interval.
- `CosmosDBService` in `azure_services.py` has multiple identical `# ──` separator comment lines — always include extra surrounding context when using the Edit tool on that file to avoid ambiguous matches.
- `ReputationTracker` must be initialised with `cosmos_service=services["cosmos"]` — it has no Cosmos access otherwise and silently falls back to in-memory only.
- Standalone changes outside the numbered plan (e.g. bug fixes, ad-hoc features) go into PROGRESS.MD as `## Standalone — [name]` sections, not appended to existing change entries.
