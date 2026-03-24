# AgentGuard — UI Overhaul Plan

## Context

Phase 1 middleware (Changes 2-7) is complete. This plan migrates the dashboard from Streamlit to FastAPI + static HTML/CSS/JS. The reference design is `page_dashboard_v2.html` — same dark theme, card styles, sidebar navigation, typography. **No deviation from that design language.**

`app.py` stays untouched as a fallback. All new code goes into new files.

---

## Locked Decisions

| Decision | Answer |
|----------|--------|
| Backend | FastAPI server (`server.py`) — build first, then wire dashboard |
| Streamlit | Keep `app.py` untouched as fallback |
| Real-time | JS `setInterval` polling REST API every 3-5s |
| Pipeline animation | Server streams step results via SSE — each step lights up as it completes |
| Domain switcher | Sidebar dropdown, same position as Streamlit |
| Scope | Everything from Streamlit + four-agent visual demo (separate page) |
| Design language | `page_dashboard_v2.html` — no deviation |
| Build order | FastAPI → wire dashboard pages → four-agent demo last |

---

## File Structure

```
server.py              — FastAPI app, all REST endpoints
pipeline.py            — Extracted pipeline logic (copied from app.py, zero Streamlit deps)
static/
  index.html           — Main dashboard (evolved from page_dashboard_v2.html)
  dashboard.js         — All JavaScript (extracted + rewritten for real API)
  dashboard.css        — All CSS (extracted from HTML, unchanged)
```

New deps in `requirements.txt`: `fastapi>=0.110.0`, `uvicorn>=0.27.0`, `sse-starlette>=1.6.0`

---

## Build Order

### Step 1: `pipeline.py` — Extract Pipeline Logic

Copy `run_pipeline()` from `app.py` (lines 888-1124) into a standalone module with zero Streamlit imports.

**Signature:**
```python
def run_pipeline(
    prompt: str,
    session_id: str,
    agent_id: str,
    policy_engine: PolicyEngine,
    reputation_tracker: ReputationTracker,
    conversation_context: dict,   # agent_id -> list[int], mutated in place
    services: dict,               # cosmos, privacy, risk_scorer, content_safety, agent
    step_callback=None,           # callable(step_num, step_name, step_data) for SSE
) -> dict:
```

**Step callback points (5 steps):**
1. After `detect_and_anonymize()` → `{entity_count, pii_found, detection_method}`
2. After `content_safety.analyze()` → `{cs_blocked, cs_scores}`
3. After risk scoring + multi-turn + policy engine → `{risk_score, tier, multi_turn_boost, policy_flags, attack_vectors}`
4. After agent call + canary check → `{agent_action, canary_triggered, agent_reasoning, deanonymized_reasoning}`
5. After `cosmos.log_decision()` → `{cosmos_logged, record_id}`

Copy these helpers inline: `_tier_from_score()`, `TIER_CONFIG`, `_COST_PER_REQUEST`.

Also copy/export: `DEPLOYMENT_PROFILES`, `PROFILE_AGENTS`, `PROFILE_AGENT_MAP`, `SCENARIOS` constants.

**Return dict**: Same shape as current `app.py` return (lines 1075-1124).

**Critical files to read:**
- `app.py:888-1124` — run_pipeline
- `app.py:69-113` — constants (PROFILE_AGENT_MAP, PROFILE_AGENTS, SCENARIOS)
- `app.py:143-180` — TIER_CONFIG, _tier_from_score

---

### Step 2: `server.py` — FastAPI Server

Build endpoints in dependency order:

#### 2a. Read-only endpoints (no pipeline)

| Endpoint | Method | Response |
|----------|--------|----------|
| `GET /health` | — | `{openai: {connected, deployment}, cosmos: {connected}, content_safety: {connected}}` |
| `GET /profiles` | — | `{profiles: [...], current: "..."}` |
| `GET /scenarios` | — | `{scenarios: {name: {prompt, expected_tier, expected_score_range, description}}}` |
| `GET /agents` | `?session_id=X` | `{agents: [...], selected: "..."}` |

#### 2b. Cosmos DB read endpoints (polling targets)

| Endpoint | Method | Response |
|----------|--------|----------|
| `GET /activity` | `?limit=20` | `{records: [...], summary: {latest_source, latest_action, latest_risk_score}}` |
| `GET /metrics` | — | `{total, blocked, escalated, auto, pii_entities_masked, source_breakdown}` |
| `GET /escalations` | `?agent_filter=` | Array of records with `tier in (soft, hard)` + `intervention_confirmed` status |
| `GET /reputation` | — | `{agents: [{agent_id, score, trust_level, decisions, blocks, history}]}` |

Field normalization: same logic as `_render_live_activity()` in `app.py` (canonical names with legacy fallbacks, deployment labels, flag labels).

#### 2c. Session management

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `POST /profile` | Switch profile | `{session_id, profile}` | `{profile, domain, agents}` |
| `POST /agent` | Switch agent | `{session_id, agent_id}` | `{agent_id}` — clears MT window |

In-memory session dict keyed by session ID:
```python
sessions[sid] = {
    "conversation_context": {},
    "decision_history": [],
    "policy_engine": PolicyEngine(yaml_path),
    "reputation_tracker": ReputationTracker(cosmos_service=...),
    "deployment_profile": "TechCorp Finance",
    "selected_agent_id": "live-financial-agent",
}
```

Session ID: generated client-side (JS `crypto.randomUUID()`), stored in `localStorage`, sent via `X-Session-ID` header.

#### 2d. Pipeline endpoint (SSE streaming)

| Endpoint | Method | Request |
|----------|--------|---------|
| `POST /intercept` | Run pipeline | `{prompt, agent_id?, session_id}` |

Returns SSE stream. Each event:
```json
{"step": 1, "name": "pii_detection", "status": "complete", "data": {...}}
...
{"step": "final", "name": "result", "status": "complete", "data": {full result dict}}
```

Implementation: spawn `run_pipeline()` in a thread with a `step_callback` that pushes to a `queue.Queue`. Async generator reads from queue and yields SSE events via `EventSourceResponse`.

JS client uses `fetch()` + `ReadableStream` (not `EventSource`, which only supports GET).

#### 2e. Escalation confirmation

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `POST /confirm` | Confirm escalation | `{record_id, session_id, justification?}` | `{success, confirmed_at}` |

Calls `services["cosmos"].confirm_decision(record_id, session_id, justification)`.

#### 2f. Compliance report

| Endpoint | Method | Response |
|----------|--------|----------|
| `GET /compliance/report` | `?format=txt&session_id=X` | `text/plain` body |
| `GET /compliance/report` | `?format=pdf&session_id=X` | `application/pdf` body |

Copies `_build_compliance_report()` and `_make_pdf_bytes()` logic from `app.py`.

#### 2g. Static file serving

```python
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return HTMLResponse(open("static/index.html").read())
```

---

### Step 3: `static/dashboard.css` — Extract CSS

Extract lines 11-1210 from `page_dashboard_v2.html` into `static/dashboard.css`. No changes to the CSS itself.

---

### Step 4: `static/index.html` — Restructure HTML

Take the HTML body from `page_dashboard_v2.html` (lines 1212-1841). Changes:

1. Replace inline `<style>` with `<link rel="stylesheet" href="/static/dashboard.css">`
2. Replace inline `<script>` with `<script src="/static/dashboard.js"></script>`
3. **Add sidebar elements:**
   - Deployment profile dropdown (below logo, above nav)
   - Azure health indicators (in sidebar footer)
4. **Add new nav items:**
   - "Reputation" under Security group
   - "Agent Simulation" under Monitor group (four-agent demo shell)
5. **Add new pages:**
   - `page-reputation` — agent leaderboard + history table
   - `page-agents` — four-agent visual demo (shell with mock layout)
6. **Modify demo pipeline page:**
   - Add agent picker dropdown above preset buttons
   - Add text area for custom prompts (not just presets)
   - Add results section below pipeline steps: risk bar, tier badge, PII table, agent reasoning, escalation buttons
7. **Modify escalations page:**
   - Add confirm/justify buttons to escalation rows
   - Add agent filter input
8. **Modify audit page:**
   - Expand table to 14 columns matching Streamlit live activity
9. **Modify compliance page:**
   - Wire TXT + PDF download buttons to `/compliance/report` endpoints
   - Add domain-specific report sections

---

### Step 5: `static/dashboard.js` — Full Rewrite

Replace all mock data and simulation with real API calls.

#### 5a. API client + session

```javascript
const API = {
  sessionId: localStorage.getItem('ag_session') || crypto.randomUUID().slice(0,8),
  async get(path) { ... },
  async post(path, body) { ... },
  async streamPipeline(prompt, agentId, onStep) { ... }  // fetch + ReadableStream for SSE
};
```

#### 5b. Polling infrastructure

```javascript
setInterval(async () => {
  const [activity, metrics, health, escalations] = await Promise.all([
    API.get('/activity?limit=20'),
    API.get('/metrics'),
    API.get('/health'),
    API.get('/escalations')
  ]);
  updateOverview(activity, metrics);
  updateSidebar(metrics, health);
  updateEscalations(escalations);
}, 4000);
```

#### 5c. Page-by-page wiring

| Page | Data Source | Key Changes |
|------|-----------|-------------|
| Overview | `GET /activity`, `GET /metrics` | Replace `DECISIONS` array with API data; stat cards show real counts |
| Demo Pipeline | `POST /intercept` (SSE) | Real pipeline execution; steps light up from server events; results rendered from API response |
| Audit Log | `GET /activity?limit=100` | 14-column table with real Cosmos data; tier filter buttons work |
| Escalations | `GET /escalations` | Real escalation records; confirm/justify buttons call `POST /confirm` |
| Analytics | `GET /metrics`, `GET /activity` | Chart.js charts wired to computed aggregates from real data |
| Reputation | `GET /reputation` | New page — agent table + score history |
| Compliance | `GET /compliance/report` | Download buttons hit real endpoints |
| Architecture | — | Static content, no changes |
| Agent Simulation | — | Shell with mock data (wired in Phase 2B) |

#### 5d. Demo pipeline — SSE streaming

```javascript
async function runDemoPipeline() {
  const prompt = document.getElementById('demo-prompt').value;
  const agentId = document.getElementById('agent-picker').value;

  await API.streamPipeline(prompt, agentId, (event) => {
    if (event.step === 'final') { showFinalResult(event.data); return; }
    // Light up step card
    activateStep(event.step, event.data);
    // Update step-specific UI (PII chips, risk ring, tier badge)
    updateStepUI(event.step, event.data);
  });
}
```

#### 5e. Escalation workflow

```javascript
async function confirmEscalation(recordId, justification) {
  const result = await API.post('/confirm', {
    record_id: recordId,
    justification: justification || ''
  });
  if (result.success) showToast('Escalation confirmed');
}
```

#### 5f. Profile/agent switching

```javascript
async function switchProfile(profile) {
  const result = await API.post('/profile', { profile });
  // Update agent picker options
  updateAgentPicker(result.agents);
  // Update domain display
  updateDomainDisplay(result.domain);
  showToast(`Switched to ${profile}`);
}
```

---

### Step 6: Four-Agent Visual Demo (Shell)

New page `page-agents` with:
- 4 agent boxes in a grid/flow layout
- Central "AgentGuard Middleware" node
- Animated connection lines between agents and middleware
- Each agent box shows: name, role, status indicator (idle/active/blocked), last action, rep score
- A "Run Simulation" button (disabled with "Coming in Phase 2" label for now)
- Mock data populating the agent cards

This is the visual shell. Real agent simulation gets wired in Phase 2B (Pearson Hardman) and Phase 2C (Memorial General).

---

## Verification Checklist

- [ ] `python -c "from pipeline import run_pipeline; print('OK')"` — no Streamlit imports
- [ ] `uvicorn server:app --port 8000` starts without errors
- [ ] `GET /health` returns service status
- [ ] `GET /activity` returns Cosmos records
- [ ] `POST /intercept` with scenario 1 prompt → SSE stream of 5 steps + final result
- [ ] `POST /profile` switches to Pearson Hardman → domain becomes "legal"
- [ ] `POST /confirm` stamps `intervention_confirmed` in Cosmos
- [ ] `GET /compliance/report?format=txt` returns real compliance report
- [ ] Browser: `http://localhost:8000/` renders dashboard with real data
- [ ] Browser: Demo pipeline animates steps in real-time from server
- [ ] Browser: Escalation confirm/justify buttons work
- [ ] Browser: Profile dropdown reloads agents and domain
- [ ] Parity: Same 5 scenarios produce matching audit records in both Streamlit and FastAPI

---

## What This Does NOT Include

- WebSocket push (polling is sufficient for demo)
- Authentication/authorization
- Docker/deployment config
- Real agent simulation (Phase 2B/2C)
- Production session management (in-memory dict is fine for demo)

---

## Run Commands

```bash
# Streamlit (fallback)
streamlit run app.py

# FastAPI (new)
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```
