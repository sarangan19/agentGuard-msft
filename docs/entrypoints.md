# AgentGuard — Entry Points

## What Runs What

| Command | Runtime | URL | Use |
|---------|---------|-----|-----|
| `streamlit run app.py` | Streamlit | `http://localhost:8501` | Original demo, always-working fallback |
| `uvicorn server:app --host 0.0.0.0 --port 8000 --reload` | FastAPI | `http://localhost:8000` | Phase 2 dashboard — primary for demos |

## Architecture Map

```
app.py          ← Streamlit UI (self-contained, reads pipeline.py)
server.py       ← FastAPI server (serves static/ + REST/SSE endpoints)
  └─ pipeline.py   ← Shared pipeline logic (zero Streamlit imports)
       ├─ azure_services.py   (OpenAI, Cosmos DB, Content Safety)
       ├─ privacy_layer.py    (PII detection + anonymisation + canary)
       ├─ risk_scorer.py      (heuristic + Azure scoring)
       ├─ policy_engine.py    (YAML-driven per-agent policy)
       ├─ reputation_tracker.py
       └─ live_agent.py       (agent dispatch via Azure OpenAI)

static/
  index.html    ← Dashboard layout + page structure
  dashboard.css ← Styles
  dashboard.js  ← API client, polling, SSE stream, all page rendering
```

## Deployment Profiles

| Profile | YAML | Dash agent ID |
|---------|------|--------------|
| TechCorp Finance | `agentguard_finance.yaml` | `dash_financial_agent` |
| Pearson Hardman Legal | `agentguard_lawfirm.yaml` | `dash_law_agent` |
| Memorial General Healthcare | `agentguard_hipaa.yaml` | `dash_med_agent` |

Profile is selected via the sidebar dropdown in either UI. Switching reloads the YAML — no restart needed.

## FastAPI Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Serves `static/index.html` |
| GET | `/health` | Azure service connection status |
| GET | `/profiles` | Available deployment profiles |
| GET | `/agents?session_id=` | Agents for current profile |
| GET | `/scenarios` | Pre-built demo scenarios |
| GET | `/activity` | Recent Cosmos DB decisions |
| GET | `/metrics` | Aggregate stats |
| GET | `/escalations` | Pending soft/hard escalations |
| GET | `/reputation` | Per-agent trust scores |
| POST | `/intercept` | Run pipeline — streams SSE step events |
| POST | `/profile` | Switch deployment profile |
| POST | `/agent` | Switch active agent |
| POST | `/confirm` | Confirm an escalation decision |
| GET | `/compliance/report` | Download compliance report (txt or pdf) |
| GET | `/session/stats` | Session cost + call count |

## Pipeline Step Numbers

Steps 1–5 map to `step-1` through `step-5` in `static/index.html`:

| Step | Name | What happens |
|------|------|-------------|
| 1 | intercept | Request captured |
| 2 | pii_detection | PII detected and anonymised |
| 3 | risk_scoring | Risk scored, multi-turn checked, policy evaluated |
| 4 | agent_dispatch | Canary injected, agent called, canary checked |
| 5 | cosmos_audit | Audit record written to Cosmos DB |
