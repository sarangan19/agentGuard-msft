"""
reputation_tracker.py
---------------------
Tracks per-agent reputation scores across a session.

Reputation is a 0-100 score that adjusts dynamically based on the agent's
request history. Higher reputation → more trust → lower effective risk.

Trust levels:
    80-100  → trusted      (green)
    50-79   → normal       (blue)
    25-49   → cautious     (yellow)
    0-24    → untrusted    (red)
"""

from dataclasses import dataclass, field
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
    score: float = 75.0          # start at normal-trust level
    request_count: int = 0
    block_count: int = 0
    auto_count: int = 0
    history: list = field(default_factory=list)


class ReputationTracker:
    """
    In-session reputation store. Scores are kept in memory and
    intended to be stored in st.session_state for Streamlit persistence.

    Usage:
        tracker = ReputationTracker()
        tracker.update_score("financial_agent", "hard")
        level = tracker.get_trust_level("financial_agent")
    """

    def __init__(self):
        self._agents: dict[str, ReputationEntry] = {}

    # ── Public API ────────────────────────────────────────────

    def get_score(self, agent_id: str) -> float:
        """Return current reputation score (0-100) for the agent."""
        return self._get_or_create(agent_id).score

    def update_score(self, agent_id: str, tier: str) -> float:
        """
        Apply a tier-based delta to the agent's score.
        Returns the new score.
        """
        entry = self._get_or_create(agent_id)
        delta = _TIER_DELTAS.get(tier, 0)
        entry.score = max(0.0, min(100.0, entry.score + delta))
        entry.request_count += 1
        if tier == "block":
            entry.block_count += 1
        elif tier == "auto":
            entry.auto_count += 1
        entry.history.append({"tier": tier, "score_after": round(entry.score, 1)})
        # Keep history bounded
        if len(entry.history) > 50:
            entry.history = entry.history[-50:]
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
                    "auto_count": entry.auto_count,
                }
        # Fallback (score < 0, shouldn't happen)
        return {
            "level": "untrusted",
            "color": "#dc3545",
            "label": "Untrusted",
            "score": 0.0,
            "request_count": entry.request_count,
            "block_count": entry.block_count,
            "auto_count": entry.auto_count,
        }

    def get_all_agents(self) -> list[dict]:
        """Return trust info for all tracked agents."""
        return [self.get_trust_level(aid) | {"agent_id": aid} for aid in self._agents]

    def reset(self, agent_id: Optional[str] = None):
        """Reset one agent or all agents."""
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
            self._agents[agent_id] = ReputationEntry(agent_id=agent_id)
        return self._agents[agent_id]
