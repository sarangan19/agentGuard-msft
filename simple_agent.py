"""
simple_agent.py
---------------
Mock financial AI agent for AgentGuard.

Simulates the behaviour of a Semantic Kernel / AutoGen financial agent:
  - Parses user intent from anonymized text
  - Selects an action from its plugin catalogue
  - Returns a structured decision dict with action, parameters, and confidence

This agent deliberately operates on ANONYMIZED text — it never sees real PII.
The privacy layer strips PII before the request reaches the agent, and
de-anonymizes the response afterwards.
"""

import re
import logging
from typing import Optional
from azure_services import get_openai_service

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# AVAILABLE FINANCIAL PLUGINS (simulated)
# ─────────────────────────────────────────────────────────────
# Each plugin entry: { action, description, risk_level, sample_params }
FINANCIAL_PLUGINS = {
    "get_expenses": {
        "description": "Retrieve expense reports for a time period",
        "risk_level": "low",
        "sample_result": {
            "total": "$1,245,000",
            "breakdown": {"Travel": "$120K", "Software": "$340K", "Personnel": "$785K"},
            "period": "Q4 2024",
        },
    },
    "generate_report": {
        "description": "Generate and format a financial summary report",
        "risk_level": "low",
        "sample_result": {
            "report_id": "RPT-2024-Q4-001",
            "pages": 12,
            "format": "PDF",
            "status": "generated",
        },
    },
    "email_report": {
        "description": "Send a financial report to specified recipients",
        "risk_level": "medium",
        "sample_result": {
            "recipients": ["[EMAIL_A]", "[EMAIL_B]"],
            "subject": "Q4 Financial Report",
            "status": "queued",
            "message_id": "MSG-20240228-0042",
        },
    },
    "transfer_funds": {
        "description": "Initiate a fund transfer to a payee",
        "risk_level": "high",
        "sample_result": {
            "transfer_id": "TXN-2024-0089",
            "amount": "[AMOUNT_A]",
            "recipient": "[PERSON_A]",
            "status": "pending_approval",
            "estimated_settlement": "2 business days",
        },
    },
    "delete_records": {
        "description": "Permanently delete financial records matching criteria",
        "risk_level": "critical",
        "sample_result": {
            "records_matched": 2847,
            "status": "REQUIRES_AUTHORIZATION",
            "warning": "This action is irreversible",
        },
    },
    "query_records": {
        "description": "Query financial records with filters",
        "risk_level": "low",
        "sample_result": {
            "records_found": 156,
            "fields": ["date", "amount", "category", "vendor"],
            "format": "JSON",
        },
    },
}


# ─────────────────────────────────────────────────────────────
# INTENT RESOLUTION (keyword-based, no AI cost)
# ─────────────────────────────────────────────────────────────
_INTENT_PATTERNS = [
    ("transfer_funds",  re.compile(r"\b(transfer|wire|send|pay)\b.*(fund|money|\[AMOUNT)", re.IGNORECASE)),
    ("delete_records",  re.compile(r"\b(delete|remove|purge|wipe|drop)\b.*(record|data|file)", re.IGNORECASE)),
    ("email_report",    re.compile(r"\b(email|send|forward|mail)\b.*(report|summary|document)", re.IGNORECASE)),
    ("get_expenses",    re.compile(r"\b(show|get|retrieve|display|fetch|view)\b.*(expense|spend|cost|Q[1-4]|quarter)", re.IGNORECASE)),
    ("generate_report", re.compile(r"\b(generate|create|produce|make|build)\b.*(report|summary|analysis)", re.IGNORECASE)),
    ("query_records",   re.compile(r"\b(query|search|find|list|look\s+up)\b.*(record|data|transaction)", re.IGNORECASE)),
]


def _resolve_intent(text: str) -> str:
    """Return the best matching action name based on keyword patterns."""
    for action, pattern in _INTENT_PATTERNS:
        if pattern.search(text):
            return action
    # Generic fallback
    if re.search(r"\b(expense|cost|budget|spending)\b", text, re.IGNORECASE):
        return "get_expenses"
    return "query_records"


# ─────────────────────────────────────────────────────────────
# CONFIDENCE ESTIMATION
# ─────────────────────────────────────────────────────────────
def _estimate_confidence(text: str, action: str) -> float:
    """
    Heuristic confidence based on how many action-related keywords appear.
    Returns 0.0-1.0.
    """
    pattern_idx = next((i for i, (a, _) in enumerate(_INTENT_PATTERNS) if a == action), -1)
    if pattern_idx == -1:
        return 0.65
    _, pattern = _INTENT_PATTERNS[pattern_idx]
    if pattern.search(text):
        # Count matching words for higher confidence
        words = len(re.findall(r"\w+", text))
        return min(0.97, 0.72 + (words / 200))
    return 0.65


# ═══════════════════════════════════════════════════════════════
# SIMPLE FINANCIAL AGENT
# ═══════════════════════════════════════════════════════════════

class SimpleFinancialAgent:
    """
    Mock financial agent that simulates Semantic Kernel / AutoGen behaviour.

    Contract:
      Input:  anonymized_text (str)  — PII has been replaced with placeholders
      Output: decision dict          — action, params, confidence, simulated result
    """

    def __init__(self):
        self.openai_svc = get_openai_service()

    # ----------------------------------------------------------
    def process(self, anonymized_text: str, metadata: Optional[dict] = None) -> dict:
        """
        Process the anonymized request and return a structured decision.

        Returns:
        {
            "action":          str,
            "plugin":          str,
            "parameters":      dict,
            "confidence":      float,
            "simulated_result": dict,
            "reasoning":       str,
            "risk_level":      str,
        }
        """
        metadata = metadata or {}

        # Resolve intent
        action = _resolve_intent(anonymized_text)
        plugin_info = FINANCIAL_PLUGINS.get(action, FINANCIAL_PLUGINS["query_records"])
        confidence = _estimate_confidence(anonymized_text, action)

        # Build parameters dict from anonymized text
        params = self._extract_params(anonymized_text, action)

        # Simulated result (what the plugin *would* return if executed)
        simulated_result = dict(plugin_info["sample_result"])

        reasoning = self._build_reasoning(anonymized_text, action, plugin_info, metadata)

        return {
            "action": action,
            "plugin": f"FinancialPlugin.{action}",
            "parameters": params,
            "confidence": round(confidence, 2),
            "simulated_result": simulated_result,
            "reasoning": reasoning,
            "risk_level": plugin_info["risk_level"],
            "plugin_description": plugin_info["description"],
        }

    # ----------------------------------------------------------
    def _extract_params(self, text: str, action: str) -> dict:
        """Extract placeholder-safe parameters from anonymized text."""
        params: dict = {}

        # Time period detection
        period_match = re.search(r"\b(Q[1-4]\s*\d{4}|\d{4}\s*Q[1-4]|fiscal\s+\d{4}|\d{4})\b", text, re.IGNORECASE)
        if period_match:
            params["period"] = period_match.group()

        # Placeholder detection (anonymized entities)
        placeholders = re.findall(r"\[[A-Z_]+_[A-Z]+\]", text)
        if placeholders:
            if action in ("transfer_funds", "email_report"):
                for ph in placeholders:
                    if "AMOUNT" in ph:
                        params["amount"] = ph
                    elif "PERSON" in ph or "EMAIL" in ph:
                        params.setdefault("recipient", ph)
                    elif "ORG" in ph:
                        params.setdefault("payee", ph)
            elif action == "delete_records":
                params["scope"] = "all" if "all" in text.lower() else "filtered"
                for ph in placeholders:
                    if "AMOUNT" in ph or "DATE" in ph:
                        params["filter"] = ph

        # Recipient list for email
        if action == "email_report":
            emails = re.findall(r"\[EMAIL_[A-Z]+\]", text)
            persons = re.findall(r"\[PERSON_[A-Z]+\]", text)
            recipients = emails + persons
            if recipients:
                params["recipients"] = recipients

        return params

    # ----------------------------------------------------------
    def _build_reasoning(self, text: str, action: str, plugin_info: dict, metadata: dict) -> str:
        """Generate a human-readable reasoning string for the UI."""
        base = f"Matched intent '{action}' → {plugin_info['description']}."
        if metadata.get("contains_financial_amount"):
            base += " Request involves a financial amount."
        if metadata.get("person_count", 0) > 0:
            base += f" {metadata['person_count']} person(s) identified."
        if metadata.get("contains_email"):
            base += " External email recipient detected."
        return base


# ─────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────
_agent_instance: Optional[SimpleFinancialAgent] = None

def get_agent() -> SimpleFinancialAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = SimpleFinancialAgent()
    return _agent_instance
