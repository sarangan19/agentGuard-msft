import os
import sys
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.append(_ROOT)

from azure_services import get_content_safety_service, get_cosmos_service
from privacy_layer import get_privacy_layer
from reputation_tracker import ReputationTracker
from risk_scorer import get_risk_scorer

from .exceptions import InterventionRequired, SecurityException

DEPARTMENT_MAP = {
    "transfer_funds": "Finance Operations",
    "delete_records": "Data Governance",
    "email_report": "Communications Compliance",
}

class AgentGuardMiddleware:
    def __init__(self, config=None, verbose=True):
        load_dotenv()
        self.config = config or {}
        self.verbose = verbose

        self.privacy = get_privacy_layer()
        self.risk_scorer = get_risk_scorer()
        self.content_safety = get_content_safety_service()
        self.cosmos = get_cosmos_service()
        self.reputation = ReputationTracker()

        self.session_id = self.config.get("session_id") or f"terminal-{str(uuid.uuid4())[:8]}"
        self.agent_id = self.config.get("agent_id") or "terminal-agent"

        self._print("[AgentGuard] ✓ Terminal middleware initialized", "green")

    def intercept_message(self, message):
        privacy_result = self.privacy.detect_and_anonymize(message)
        count = privacy_result.get("entity_count", 0)
        if count > 0:
            self._print(f"[AgentGuard] 🔒 Privacy check: Anonymized {count} PII entities", "yellow")
        else:
            self._print("[AgentGuard] ✓ Privacy check: No PII detected", "green")
        return privacy_result["anonymized_text"], privacy_result.get("mapping", {})

    def validate_action(self, action, context=None, agent_id=None):
        context = context or {}
        agent_id = agent_id or self.agent_id

        original_text = context.get("original_text") or context.get("message") or ""
        anonymized_text = context.get("anonymized_text") or ""
        metadata = context.get("metadata") or {}

        self._print(f"[AgentGuard] 🛡️ Validating action: {action}", "blue")

        cs_result = self.content_safety.analyze(original_text)
        cs_blocked = cs_result.get("blocked", False)
        if cs_result.get("available", False):
            self._print("[AgentGuard] ✓ Content Safety available", "green")
        else:
            self._print("[AgentGuard] ⚠️ Content Safety unavailable", "yellow")

        risk = self.risk_scorer.score(
            original_text=original_text,
            anonymized_text=anonymized_text,
            metadata=metadata,
            content_safety_blocked=cs_blocked,
        )

        tier = risk.tier
        self._print(f"[AgentGuard] 📊 Risk score: {risk.total}/100 ({tier})", "blue")

        trust = self.reputation.get_trust_level(agent_id)
        trust_level = trust.get("level", "normal")
        recent_block_rate = self.reputation.get_recent_block_rate(agent_id)

        audit_record = {
            "id": str(uuid.uuid4()),
            "session_id": self.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_id,
            "original_text": original_text[:500],
            "anonymized_text": anonymized_text[:500],
            "entity_count": metadata.get("entity_count", context.get("entity_count", 0)),
            "detection_method": metadata.get("detection_method"),
            "prefilter_triggered": risk.prefilter_triggered,
            "prefilter_patterns": risk.prefilter_patterns,
            "content_safety_blocked": cs_blocked,
            "risk_score": risk.total,
            "tier": tier,
            "risk_factors": risk.factors,
            "risk_reasoning": risk.reasoning,
            "agent_action": action,
            "scored_by": risk.scored_by,
            "source": "terminal",
            "trust_level": trust_level,
            "recent_block_rate": round(recent_block_rate, 2),
        }

        if cs_blocked:
            audit_record["tier"] = "block"
            audit_record["risk_reasoning"] = "Azure Content Safety blocked request."
            self._log_to_cosmos(audit_record)
            raise SecurityException("Blocked by Azure Content Safety", risk.total, "block", risk.prefilter_patterns, risk.reasoning)

        if tier == "block" or trust_level == "untrusted" and recent_block_rate >= 0.6:
            self._print("[AgentGuard] 🚨 BLOCKED action", "red")
            self._log_to_cosmos(audit_record)
            raise SecurityException("High risk action blocked", risk.total, tier, risk.prefilter_patterns, risk.reasoning)

        if tier in ("soft", "hard"):
            self._print("[AgentGuard] ⚠️ Intervention required", "yellow")
            raise InterventionRequired(
                "Confirmation required",
                risk.total,
                tier,
                risk.reasoning,
                self.confirm_action,
                audit_record=audit_record,
            )

        self._print("[AgentGuard] ✓ Action approved", "green")
        self.reputation.update_score(agent_id, tier)
        self._log_to_cosmos(audit_record)
        return audit_record

    def confirm_action(self, audit_record, justification, action=None):
        audit_record = dict(audit_record)
        action_name = action or audit_record.get("agent_action") or "unknown_action"
        department = DEPARTMENT_MAP.get(action_name, "Security Review")
        audit_record["justification"] = justification
        audit_record["intervention_confirmed"] = True
        audit_record["status"] = "escalated"
        audit_record["department"] = department
        audit_record["escalated_at"] = datetime.now(timezone.utc).isoformat()
        self._print("[AgentGuard] ✓ Justification recorded", "green")
        self._log_to_cosmos(audit_record)
        return audit_record

    def restore_privacy(self, response, entity_map):
        restored = self.privacy.de_anonymize(response, entity_map)
        scan = self.privacy.scan_output(restored)
        leaks = scan.get("leaks_found", 0)
        if leaks > 0:
            self._print(f"[AgentGuard] ⚠️ Output contained {leaks} PII leak(s); redacted", "yellow")
            return scan.get("sanitized_output", restored)
        return restored

    def _log_to_cosmos(self, record):
        try:
            return self.cosmos.log_decision(record)
        except Exception as exc:
            self._print(f"[AgentGuard] ⚠️ Cosmos logging failed: {exc}", "yellow")
            self._write_local_fallback(record)
            return False

    def _write_local_fallback(self, record):
        try:
            path = os.path.join(os.getcwd(), "terminal_decisions.log")
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(f"{record}\n")
        except Exception:
            pass

    def _print(self, message, color=None):
        if not self.verbose:
            return

        colors = {
            "green": "\033[92m",
            "yellow": "\033[93m",
            "red": "\033[91m",
            "blue": "\033[94m",
        }
        reset = "\033[0m"
        color_key = color if isinstance(color, str) else ""
        prefix = colors.get(color_key, "")
        suffix = reset if prefix else ""
        sys.stdout.write(f"{prefix}{message}{suffix}\n")
