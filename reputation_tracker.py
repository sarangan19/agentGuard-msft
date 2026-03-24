"""
reputation_tracker.py
---------------------
Tracks per-agent reputation scores, persisted to Azure Cosmos DB.

Reputation is a 0-100 score that adjusts dynamically based on the agent's
request history. Higher reputation → more trust → lower effective risk.

Trust levels:
    80-100  → trusted      (green)
    50-79   → normal       (blue)
    25-49   → cautious     (yellow)
    0-24    → untrusted    (red)

Persistence:
    On first access for an agent, the score is loaded from Cosmos DB.
    On every score change, the updated document is written back immediately.
    Documents live in the same container as audit logs, identified by
    id="rep_{agent_id}" and session_id="__reputation__".
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ── Tier deltas applied after each decision ───────────────────
_TIER_DELTAS = {
    "auto":  +3,    # safe request boosts reputation slightly
    "soft":  -2,    # borderline request — small penalty
    "hard":  -8,    # high-risk request — notable penalty
    "block": -20,   # blocked/attack — major reputation hit
}

_TRUST_LEVELS = [
    (80, "trusted",   "#28a745", "Trusted Agent"),
    (50, "normal",    "#0078d4", "Normal Trust"),
    (25, "cautious",  "#ffc107", "Proceed with Caution"),
    (0,  "untrusted", "#dc3545", "Untrusted — Elevated Review"),
]


@dataclass
class ReputationEntry:
    agent_id: str
    score: float = 75.0
    request_count: int = 0
    block_count: int = 0
    escalation_count: int = 0
    auto_count: int = 0
    history: list = field(default_factory=list)          # in-memory: {tier, score_after}
    cosmos_history: list = field(default_factory=list)   # persisted: last 10 score changes


class ReputationTracker:
    """
    Per-agent reputation store with Cosmos DB persistence.

    Scores are initialised from Cosmos DB on first access. Every score
    change is written back to Cosmos immediately.

    Usage:
        tracker = ReputationTracker(cosmos_service=services["cosmos"])
        tracker.update_score("donna-agent", "hard")
        level = tracker.get_trust_level("donna-agent")
    """

    def __init__(self, cosmos_service=None):
        self._agents: dict[str, ReputationEntry] = {}
        self._cosmos = cosmos_service

    # ── Public API ────────────────────────────────────────────

    def get_score(self, agent_id: str) -> float:
        """Return current reputation score (0-100) for the agent."""
        return self._get_or_create(agent_id).score

    def update_score(self, agent_id: str, tier: str) -> float:
        """
        Apply a tier-based delta to the agent's score.
        Persists the updated document to Cosmos DB immediately.
        Returns the new score.
        """
        entry = self._get_or_create(agent_id)
        previous_score = round(entry.score, 1)
        delta = _TIER_DELTAS.get(tier, 0)
        entry.score = max(0.0, min(100.0, entry.score + delta))
        entry.request_count += 1

        if tier == "block":
            entry.block_count += 1
        elif tier in ("soft", "hard"):
            entry.escalation_count += 1
        elif tier == "auto":
            entry.auto_count += 1

        # In-memory history (bounded at 50)
        entry.history.append({"tier": tier, "score_after": round(entry.score, 1)})
        if len(entry.history) > 50:
            entry.history = entry.history[-50:]

        # Cosmos-formatted history (last 10, newest first)
        history_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous_score": previous_score,
            "new_score": round(entry.score, 1),
            "reason": tier,
        }
        entry.cosmos_history.insert(0, history_entry)
        if len(entry.cosmos_history) > 10:
            entry.cosmos_history = entry.cosmos_history[:10]

        # Persist immediately
        self._persist(entry)

        return entry.score

    def get_trust_level(self, agent_id: str) -> dict:
        """
        Return a dict describing the current trust level:
        {
            "level": "trusted" | "normal" | "cautious" | "untrusted",
            "color": hex string,
            "label": human-readable label,
            "score": float,
            "request_count": int,
            "block_count": int,
            "escalation_count": int,
            "cosmos_history": list of last 10 score changes,
        }
        """
        entry = self._get_or_create(agent_id)
        score = entry.score
        for threshold, level, color, label in _TRUST_LEVELS:
            if score >= threshold:
                return {
                    "level": level,
                    "color": color,
                    "label": label,
                    "score": round(score, 1),
                    "request_count": entry.request_count,
                    "block_count": entry.block_count,
                    "escalation_count": entry.escalation_count,
                    "auto_count": entry.auto_count,
                    "cosmos_history": entry.cosmos_history,
                }
        return {
            "level": "untrusted",
            "color": "#dc3545",
            "label": "Untrusted",
            "score": 0.0,
            "request_count": entry.request_count,
            "block_count": entry.block_count,
            "escalation_count": entry.escalation_count,
            "auto_count": entry.auto_count,
            "cosmos_history": entry.cosmos_history,
        }

    def get_all_agents(self) -> list[dict]:
        """Return trust info for all tracked agents."""
        return [self.get_trust_level(aid) | {"agent_id": aid} for aid in self._agents]

    def reset(self, agent_id: Optional[str] = None):
        """Reset one agent or all agents (in-memory only — does not delete Cosmos docs)."""
        if agent_id:
            self._agents.pop(agent_id, None)
        else:
            self._agents.clear()

    def get_recent_block_rate(self, agent_id: str, window: int = 5) -> float:
        """
        Return the fraction of the last `window` requests that were blocked.
        Returns 0.0 if the agent has no history yet.
        """
        entry = self._get_or_create(agent_id)
        if not entry.history:
            return 0.0
        recent = entry.history[-window:]
        blocked = sum(1 for h in recent if h["tier"] == "block")
        return blocked / len(recent)

    # ── Private ───────────────────────────────────────────────

    def _get_or_create(self, agent_id: str) -> ReputationEntry:
        if agent_id not in self._agents:
            self._agents[agent_id] = self._load_from_cosmos(agent_id)
        return self._agents[agent_id]

    def _load_from_cosmos(self, agent_id: str) -> ReputationEntry:
        """
        Try to load reputation from Cosmos DB.
        Falls back to a fresh ReputationEntry (score=75) if not found.
        """
        if self._cosmos is not None:
            doc = self._cosmos.get_reputation(agent_id)
            if doc is not None:
                entry = ReputationEntry(agent_id=agent_id)
                entry.score = float(doc.get("current_score", 75.0))
                entry.request_count = int(doc.get("total_decisions", 0))
                entry.block_count = int(doc.get("total_blocks", 0))
                entry.escalation_count = int(doc.get("total_escalations", 0))
                entry.auto_count = int(doc.get("total_auto", 0))
                entry.cosmos_history = doc.get("score_history", [])
                return entry
        return ReputationEntry(agent_id=agent_id)

    def _persist(self, entry: ReputationEntry):
        """Write the current reputation state to Cosmos DB."""
        if self._cosmos is None:
            return
        trust_label = "normal"
        for threshold, level, _, _ in _TRUST_LEVELS:
            if entry.score >= threshold:
                trust_label = level
                break
        doc = {
            "id": f"rep_{entry.agent_id}",
            "session_id": "__reputation__",
            "doc_type": "agent_reputation",
            "agent_id": entry.agent_id,
            "current_score": round(entry.score, 1),
            "trust_level": trust_label,
            "total_decisions": entry.request_count,
            "total_blocks": entry.block_count,
            "total_escalations": entry.escalation_count,
            "total_auto": entry.auto_count,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "score_history": entry.cosmos_history,
        }
        self._cosmos.upsert_reputation(doc)
