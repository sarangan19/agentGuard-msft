"""
server.py
---------
AgentGuard FastAPI server.
Serves the HTML dashboard and exposes REST + SSE endpoints for the pipeline.

Run with:
    uvicorn server:app --host 0.0.0.0 --port 8000 --reload
"""

import json
import logging
import os
import queue
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── SSE support ───────────────────────────────────────────────────────────────
try:
    from sse_starlette.sse import EventSourceResponse
    _SSE_AVAILABLE = True
except ImportError:
    _SSE_AVAILABLE = False
    logger.warning("sse-starlette not installed — POST /intercept will return JSON instead of SSE")

# ── App init ──────────────────────────────────────────────────────────────────
app = FastAPI(title="AgentGuard", version="2.1.0", docs_url="/docs")

STATIC_DIR = Path(__file__).parent / "static"

# ── Service singletons ────────────────────────────────────────────────────────
from azure_services import get_openai_service, get_cosmos_service, get_content_safety_service
from live_agent import get_live_agent
from privacy_layer import get_privacy_layer
from risk_scorer import get_risk_scorer
from policy_engine import PolicyEngine, DEPLOYMENT_PROFILES
from reputation_tracker import ReputationTracker
from pipeline import (
    run_pipeline,
    PROFILE_AGENT_MAP,
    PROFILE_AGENTS,
    SCENARIOS,
    TIER_CONFIG,
    _COST_PER_REQUEST,
    build_compliance_report,
    make_pdf_bytes,
)
# DEPLOYMENT_PROFILES is imported from policy_engine above

_services: dict = {}


def _load_services() -> dict:
    return {
        "openai":          get_openai_service(),
        "cosmos":          get_cosmos_service(),
        "content_safety":  get_content_safety_service(),
        "privacy":         get_privacy_layer(),
        "risk_scorer":     get_risk_scorer(),
        "agent":           get_live_agent(),
    }


def get_services() -> dict:
    global _services
    if not _services:
        _services = _load_services()
    return _services


# ── Session management ────────────────────────────────────────────────────────
_sessions: dict[str, dict] = {}


def _make_session(sid: str) -> dict:
    svcs = get_services()
    default_profile = "TechCorp Finance"
    yaml_path = DEPLOYMENT_PROFILES[default_profile]
    return {
        "id":                   sid,
        "conversation_context": {},
        "decision_history":     [],
        "policy_engine":        PolicyEngine(yaml_path),
        "reputation_tracker":   ReputationTracker(cosmos_service=svcs["cosmos"]),
        "deployment_profile":   default_profile,
        "selected_agent_id":    PROFILE_AGENT_MAP[default_profile],
        "azure_call_count":     0,
        "total_cost":           0.0,
    }


def get_session(sid: str) -> dict:
    if sid not in _sessions:
        _sessions[sid] = _make_session(sid)
    return _sessions[sid]


# ── Label helpers (mirrors app.py _DEPLOYMENT_LABELS / _FLAG_LABELS) ─────────
_DEPLOYMENT_LABELS = {
    "techcorp_finance":  "TechCorp Finance",
    "pearson_hardman":   "Pearson Hardman",
    "memorial_general":  "Memorial General",
}

_FLAG_LABELS = {
    "cross_matter_access":       "Cross-Matter",
    "privilege_contamination":   "Priv. Contam.",
    "privilege_marker_detected": "Priv. Marker",
    "bulk_export":               "Bulk Export",
    "minimum_necessary_violation": "Min. Nec.",
    "special_category_protection": "Special Cat.",
    "canary_triggered":          "Canary",
    "agent_scope_violation":     "Scope Violation",
}


def _normalise_record(r: dict) -> dict:
    """Normalise Cosmos record field names and add display helpers."""
    flags = r.get("policy_flags") or {}
    if isinstance(flags, str):
        try:
            flags = json.loads(flags)
        except Exception:
            flags = {}

    flag_labels = [_FLAG_LABELS[k] for k in flags if k in _FLAG_LABELS and flags[k]]

    return {
        **r,
        "pii_entities_detected": r.get("pii_entities_detected", r.get("entity_count", 0)),
        "prefilter_hit":         r.get("prefilter_hit", r.get("prefilter_triggered", False)),
        "deployment_label":      _DEPLOYMENT_LABELS.get(r.get("policy_deployment", ""), r.get("policy_deployment", "—")),
        "flag_labels":           flag_labels,
        "policy_flags":          flags,
    }


# ── Request/Response models ───────────────────────────────────────────────────

class InterceptRequest(BaseModel):
    prompt: str
    agent_id: Optional[str] = None
    session_id: str


class ConfirmRequest(BaseModel):
    record_id: str
    session_id: str
    justification: Optional[str] = ""


class ProfileRequest(BaseModel):
    session_id: str
    profile: str


class AgentRequest(BaseModel):
    session_id: str
    agent_id: str


# ── Static files + root ───────────────────────────────────────────────────────

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return HTMLResponse(content=index.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>AgentGuard</h1><p>static/index.html not found.</p>", status_code=404)


# ── 2a: Read-only endpoints ───────────────────────────────────────────────────

@app.get("/health")
async def health():
    svcs = get_services()
    openai_ok  = svcs["openai"].client  is not None
    cosmos_ok  = svcs["cosmos"].container is not None
    cs_ok      = svcs["content_safety"].client is not None
    return {
        "openai":         {"connected": openai_ok,  "deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")},
        "cosmos":         {"connected": cosmos_ok},
        "content_safety": {"connected": cs_ok},
    }


@app.get("/profiles")
async def profiles(session_id: Optional[str] = Query(None)):
    current = "TechCorp Finance"
    if session_id and session_id in _sessions:
        current = _sessions[session_id]["deployment_profile"]
    return {
        "profiles": list(DEPLOYMENT_PROFILES.keys()),
        "current":  current,
    }


@app.get("/scenarios")
async def scenarios():
    return {"scenarios": SCENARIOS}


@app.get("/agents")
async def agents(session_id: str = Query(...)):
    sess = get_session(session_id)
    profile = sess["deployment_profile"]
    agent_list = PROFILE_AGENTS.get(profile, [])
    return {
        "agents":   agent_list,
        "selected": sess["selected_agent_id"],
    }


# ── 2b: Cosmos DB read endpoints ─────────────────────────────────────────────

@app.get("/activity")
async def activity(limit: int = Query(20)):
    svcs = get_services()
    raw  = svcs["cosmos"].get_recent_decisions(limit=limit)
    records = [_normalise_record(r) for r in raw]

    summary = {}
    if records:
        latest = records[0]
        summary = {
            "latest_source":     latest.get("source", "—"),
            "latest_action":     latest.get("agent_action") or latest.get("original_text", "")[:60],
            "latest_risk_score": latest.get("risk_score", 0),
        }

    return {"records": records, "summary": summary}


@app.get("/metrics")
async def metrics():
    svcs    = get_services()
    records = svcs["cosmos"].get_recent_decisions(limit=200)

    total     = len(records)
    blocked   = sum(1 for r in records if r.get("tier") == "block")
    escalated = sum(1 for r in records if r.get("tier") in ("soft", "hard"))
    auto      = sum(1 for r in records if r.get("tier") == "auto")
    pii       = sum(r.get("pii_entities_detected", r.get("entity_count", 0)) for r in records)
    dash      = sum(1 for r in records if r.get("source") == "dashboard")
    terminal  = sum(1 for r in records if r.get("source") == "terminal")

    return {
        "total":                total,
        "blocked":              blocked,
        "escalated":            escalated,
        "auto":                 auto,
        "pii_entities_masked":  pii,
        "source_breakdown":     {"dashboard": dash, "terminal": terminal},
    }


@app.get("/escalations")
async def escalations(agent_filter: Optional[str] = Query(None)):
    svcs    = get_services()
    records = svcs["cosmos"].get_recent_decisions(limit=100)
    esc     = [r for r in records if r.get("tier") in ("soft", "hard")]
    esc     = [_normalise_record(r) for r in esc]

    if agent_filter:
        f = agent_filter.lower()
        esc = [r for r in esc if f in (r.get("agent_id") or "").lower()]

    return {"escalations": esc}


@app.get("/reputation")
async def reputation():
    svcs    = get_services()
    records = svcs["cosmos"].get_recent_decisions(limit=200)

    # Collect unique agent IDs seen in Cosmos
    agent_ids = list({r.get("agent_id") for r in records if r.get("agent_id")})

    # Use a temporary reputation tracker to query scores
    tracker = ReputationTracker(cosmos_service=svcs["cosmos"])
    result  = []
    for aid in agent_ids:
        info    = tracker.get_trust_level(aid)
        history = info.get("cosmos_history", [])
        result.append({
            "agent_id":    aid,
            "score":       info["score"],
            "trust_level": info["label"],
            "trust_color": info["color"],
            "decisions":   info.get("total_requests", 0),
            "blocks":      info.get("block_count", 0),
            "escalations": info.get("escalation_count", 0),
            "history":     history[-10:],
        })

    result.sort(key=lambda x: x["score"])
    return {"agents": result}


# ── 2c: Session management ────────────────────────────────────────────────────

@app.post("/profile")
async def switch_profile(body: ProfileRequest):
    if body.profile not in DEPLOYMENT_PROFILES:
        raise HTTPException(status_code=400, detail=f"Unknown profile: {body.profile}")

    svcs     = get_services()
    sess     = get_session(body.session_id)
    yaml_path = DEPLOYMENT_PROFILES[body.profile]

    sess["deployment_profile"]   = body.profile
    sess["policy_engine"]        = PolicyEngine(yaml_path)
    sess["selected_agent_id"]    = PROFILE_AGENT_MAP[body.profile]
    sess["conversation_context"] = {}  # clear MT windows on profile switch

    return {
        "profile": body.profile,
        "domain":  sess["policy_engine"].get_domain(),
        "agents":  PROFILE_AGENTS.get(body.profile, []),
    }


@app.post("/agent")
async def switch_agent(body: AgentRequest):
    sess    = get_session(body.session_id)
    profile = sess["deployment_profile"]
    allowed = PROFILE_AGENTS.get(profile, [])

    if body.agent_id not in allowed:
        raise HTTPException(status_code=400, detail=f"Agent {body.agent_id!r} not in profile {profile!r}")

    # Clear the MT window for the newly selected agent (mirrors _on_agent_change)
    ctx = sess.get("conversation_context", {})
    ctx.pop(body.agent_id, None)

    sess["selected_agent_id"] = body.agent_id
    return {"agent_id": body.agent_id}


# ── 2d: Pipeline endpoint (SSE streaming) ────────────────────────────────────

@app.post("/intercept")
async def intercept(body: InterceptRequest):
    svcs = get_services()
    sess = get_session(body.session_id)

    agent_id = body.agent_id or sess["selected_agent_id"]

    # Enforce input length
    prompt = body.prompt.strip()[:2000]
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    step_queue: queue.Queue = queue.Queue()

    def _step_cb(step_num: int, name: str, data: dict):
        step_queue.put({"step": step_num, "name": name, "status": "complete", "data": data})

    def _run():
        try:
            result = run_pipeline(
                prompt=prompt,
                session_id=body.session_id,
                agent_id=agent_id,
                policy_engine=sess["policy_engine"],
                reputation_tracker=sess["reputation_tracker"],
                conversation_context=sess["conversation_context"],
                services=svcs,
                step_callback=_step_cb,
            )
            sess["azure_call_count"] += 1
            sess["total_cost"] = round(sess["total_cost"] + _COST_PER_REQUEST, 6)
            sess["decision_history"].append(result)
            step_queue.put({"step": "final", "name": "result", "status": "complete", "data": result})
        except Exception as exc:
            logger.exception("Pipeline error")
            step_queue.put({"step": "error", "name": "error", "status": "error", "data": {"message": str(exc)}})
        finally:
            step_queue.put(None)  # sentinel

    threading.Thread(target=_run, daemon=True).start()

    if _SSE_AVAILABLE:
        import asyncio

        async def _event_gen():
            loop = asyncio.get_event_loop()
            while True:
                item = await loop.run_in_executor(None, step_queue.get)
                if item is None:
                    break
                yield {"data": json.dumps(item, default=str)}

        return EventSourceResponse(_event_gen())
    else:
        # Fallback: block until pipeline completes, return JSON
        import asyncio
        loop = asyncio.get_event_loop()
        items = []
        while True:
            item = await loop.run_in_executor(None, step_queue.get)
            if item is None:
                break
            items.append(item)
        final = next((i for i in items if i.get("step") == "final"), None)
        return {"steps": items, "result": final["data"] if final else None}


# ── 2e: Escalation confirmation ───────────────────────────────────────────────

@app.post("/confirm")
async def confirm(body: ConfirmRequest):
    svcs = get_services()
    ok   = svcs["cosmos"].confirm_decision(
        record_id=body.record_id,
        session_id=body.session_id,
        justification=body.justification or "",
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to confirm decision in Cosmos DB")
    return {
        "success":      True,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }


# ── 2f: Compliance report ─────────────────────────────────────────────────────

@app.get("/compliance/report")
async def compliance_report(
    session_id: str = Query(...),
    format: str = Query("txt"),
):
    svcs    = get_services()
    sess    = get_session(session_id)
    profile = sess["deployment_profile"]
    records = svcs["cosmos"].get_recent_decisions(limit=500)
    text    = build_compliance_report(profile, records)

    if format == "pdf":
        try:
            pdf_bytes = make_pdf_bytes(text, profile)
            filename  = f"agentguard_compliance_{profile.lower().replace(' ', '_')}.pdf"
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except ImportError:
            raise HTTPException(status_code=501, detail="fpdf2 not installed — PDF export unavailable")

    filename = f"agentguard_compliance_{profile.lower().replace(' ', '_')}.txt"
    return Response(
        content=text.encode("utf-8"),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Session stats (sidebar cost/calls) ───────────────────────────────────────

@app.get("/session/stats")
async def session_stats(session_id: str = Query(...)):
    sess = get_session(session_id)
    return {
        "azure_call_count": sess["azure_call_count"],
        "total_cost":       sess["total_cost"],
        "session_id":       session_id,
    }


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
