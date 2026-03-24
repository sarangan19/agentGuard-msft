"""
policy_engine.py
----------------
Policy-as-YAML engine for AgentGuard.

Loads a YAML configuration file that describes per-agent permissions, forbidden
entity types, approval rules, and domain-specific scoring overrides.

Evaluation paths:
  - generic  : entity access control + approval rules
  - legal     : generic + cross-matter firewall + privilege contamination detection
  - healthcare: generic + HIPAA minimum-necessary + special category protection

Returns a structured `policy_decision` dict on every evaluate() call:
  {
      "allowed":         bool,
      "reason":          str,
      "override_tier":   str | None,   # force this tier regardless of risk score
      "score_boost":     int,          # add to effective risk score (0 = no boost)
      "flags":           dict,         # domain-specific flags (e.g. cross_matter, bulk_export)
  }

Dynamic reload: call reload() or re-instantiate; no server restart needed.
"""

import os
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Tier ordering for ceiling enforcement ──────────────────────────────────────
_TIER_ORDER = {"auto": 0, "soft": 1, "hard": 2, "block": 3}


class PolicyEngine:
    """
    Evaluate requests against per-agent YAML policy rules.

    Usage:
        engine = PolicyEngine("agentguard_lawfirm.yaml")
        decision = engine.evaluate(
            agent_id="research-bot-001",
            request_text="Pull documents for MATTER-2024-002",
            entity_types=["MATTER_REF"],
        )
    """

    def __init__(self, policy_path: Optional[str] = None):
        self.policy_path = policy_path
        self.policy: dict = {}
        if policy_path and os.path.isfile(policy_path):
            self._load(policy_path)
        elif policy_path:
            logger.warning("PolicyEngine: file not found — %s. Running with no restrictions.", policy_path)

    # ── Public API ─────────────────────────────────────────────────────────────

    def reload(self):
        """Re-read the YAML file from disk. Call when domain changes at runtime."""
        if self.policy_path and os.path.isfile(self.policy_path):
            self._load(self.policy_path)

    def get_domain(self) -> str:
        """Return the domain declared in the loaded YAML (default: 'finance')."""
        return self.policy.get("domain", "finance")

    def get_deployment(self) -> str:
        """Return the deployment label declared in the YAML."""
        return self.policy.get("deployment", "unknown")

    def evaluate(
        self,
        agent_id: str,
        request_text: str,
        entity_types: Optional[list] = None,
    ) -> dict:
        """
        Run the full policy evaluation pipeline for this request.

        Returns a policy_decision dict.
        """
        if not self.policy:
            return _no_restriction_decision()

        domain = self.get_domain()
        entity_types = entity_types or []

        # Run generic checks first
        decision = self._evaluate_generic(agent_id, request_text, entity_types)

        # Layer in domain-specific checks — they can only make things stricter
        if domain == "legal":
            decision = self._evaluate_legal(agent_id, request_text, entity_types, decision)
        elif domain == "healthcare":
            decision = self._evaluate_healthcare(agent_id, request_text, entity_types, decision)

        return decision

    def check_entity_access(self, entity_type: str, agent_id: str) -> str:
        """
        Returns 'allow', 'deny', or 'redact'.
        Convenience method for single-entity checks.
        """
        agent_policy = self.policy.get("agents", {}).get(agent_id, {})
        forbidden = [e.lower() for e in agent_policy.get("forbidden_entities", [])]
        allowed   = [e.lower() for e in agent_policy.get("allowed_entities", [])]
        et = entity_type.lower()
        if et in forbidden:
            return "deny"
        if allowed and et not in allowed:
            return "redact"
        return "allow"

    def get_max_tier(self, agent_id: str) -> str:
        """Return the ceiling tier for this agent. Default: 'block' (no ceiling)."""
        agent_policy = self.policy.get("agents", {}).get(agent_id, {})
        return agent_policy.get("max_risk_tier", "block")

    def requires_approval(self, action: str, risk_score: int, agent_id: str) -> bool:
        """Return True if this action always requires human approval."""
        agent_policy = self.policy.get("agents", {}).get(agent_id, {})
        for rule in agent_policy.get("requires_approval_for", []):
            if rule.get("action") == action:
                if rule.get("always"):
                    return True
                if risk_score >= rule.get("above_risk", 101):
                    return True
        return False

    # ── Private — evaluation paths ─────────────────────────────────────────────

    def _check_scope_violation(
        self,
        agent_id: str,
        request_text: str,
        agent_policy: dict,
    ) -> "dict | None":
        """
        Detect requests that fall entirely outside the agent's defined role.

        Reads `out_of_scope_actions` from the agent's YAML policy. Each entry
        defines an action name, a human-readable description, a role_description
        (what the agent IS for), and a list of regex patterns that signal the
        out-of-scope intent.

        Returns a blocking decision dict if a violation is detected, None otherwise.
        """
        scope_rules = agent_policy.get("out_of_scope_actions", [])
        if not scope_rules:
            return None

        for rule in scope_rules:
            patterns = rule.get("patterns", [])
            for pattern in patterns:
                if re.search(pattern, request_text, re.IGNORECASE):
                    action      = rule.get("action", "unknown_action")
                    description = rule.get("description", action.replace("_", " "))
                    role_desc   = rule.get("role_description", "its defined scope")
                    reason = (
                        f"{agent_id} is not authorised to {description} — "
                        f"this agent is scoped to {role_desc} only."
                    )
                    decision = _no_restriction_decision()
                    decision["allowed"]        = False
                    decision["override_tier"]  = "block"
                    decision["score_boost"]    = 90
                    decision["reason"]         = reason
                    decision["flags"]["agent_scope_violation"]  = True
                    decision["flags"]["scope_violation_action"] = action
                    return decision

        return None

    def _evaluate_generic(
        self,
        agent_id: str,
        request_text: str,
        entity_types: list,
    ) -> dict:
        """Generic entity-access + approval-rule checks."""
        decision = _no_restriction_decision()
        agent_policy = self.policy.get("agents", {}).get(agent_id, {})
        if not agent_policy:
            return decision

        # Scope violation check: is this action outside the agent's role entirely?
        # Runs before entity checks — role boundary is the outermost constraint.
        scope_violation = self._check_scope_violation(agent_id, request_text, agent_policy)
        if scope_violation:
            return scope_violation

        # Entity access check: any denied entity → immediate block
        for et in entity_types:
            access = self.check_entity_access(et, agent_id)
            if access == "deny":
                decision["allowed"] = False
                decision["override_tier"] = "block"
                decision["score_boost"] = 100
                decision["reason"] = (
                    f"Entity type '{et}' is forbidden for agent '{agent_id}'"
                )
                decision["flags"]["forbidden_entity"] = et
                return decision

        # Bulk export detection (applies to all domains)
        if _looks_like_bulk_export(request_text):
            bulk_action = agent_policy.get("bulk_export", agent_policy.get("bulk_access", ""))
            if bulk_action == "block":
                decision["allowed"] = False
                decision["override_tier"] = "block"
                decision["score_boost"] = 60
                decision["reason"] = f"Bulk export attempt blocked by policy for agent '{agent_id}'"
                decision["flags"]["bulk_export"] = True
                return decision
            elif bulk_action in ("soft_confirm", "soft"):
                decision["score_boost"] = max(decision["score_boost"], 20)
                decision["flags"]["bulk_export"] = True
                decision["reason"] = "Bulk access requires soft confirmation"

        return decision

    def _evaluate_legal(
        self,
        agent_id: str,
        request_text: str,
        entity_types: list,
        base_decision: dict,
    ) -> dict:
        """
        Legal domain overlay:
        - Cross-matter firewall: block access to matters outside agent scope
        - Privilege contamination: flag when two different matters appear together
        - External access rules
        """
        decision = dict(base_decision)
        decision["flags"] = dict(base_decision.get("flags", {}))

        if not base_decision["allowed"]:
            return decision  # already blocked

        agent_policy = self.policy.get("agents", {}).get(agent_id, {})
        allowed_matters  = agent_policy.get("matters", [])
        forbidden_matters = agent_policy.get("forbidden_matters", [])
        external_access  = agent_policy.get("external_access", "")

        # Detect matter references in the request text
        matter_refs = _extract_matter_refs(request_text)

        # Cross-matter firewall: any reference to a forbidden matter
        for matter in matter_refs:
            if matter in forbidden_matters:
                decision["allowed"] = False
                decision["override_tier"] = "block"
                decision["score_boost"] = 100
                decision["reason"] = (
                    f"Cross-matter access blocked: agent '{agent_id}' is not scoped to {matter}"
                )
                decision["flags"]["cross_matter_access"] = matter
                decision["flags"]["privilege_contamination"] = True
                return decision

        # Privilege contamination: references span two different active matters
        if len(matter_refs) >= 2 and allowed_matters:
            in_scope     = [m for m in matter_refs if m in allowed_matters]
            out_of_scope = [m for m in matter_refs if m not in allowed_matters]
            if in_scope and out_of_scope:
                decision["allowed"] = False
                decision["override_tier"] = "block"
                decision["score_boost"] = 100
                decision["reason"] = (
                    f"Privilege contamination: request mixes matter scopes "
                    f"({', '.join(in_scope)} ↔ {', '.join(out_of_scope)})"
                )
                decision["flags"]["privilege_contamination"] = True
                decision["flags"]["contaminated_matters"] = out_of_scope
                return decision

        # Privilege marker special category — ATTORNEY-CLIENT and WORK PRODUCT force BLOCK
        # Check both raw text (regex) and entity types detected by the privacy layer
        privilege_in_types = "PRIVILEGE_MARKER" in [et.upper() for et in entity_types]
        privilege_hits = re.findall(
            r"\b(?:ATTORNEY[-\s]CLIENT|WORK\s+PRODUCT|PRIVILEGED\s+AND\s+CONFIDENTIAL|ATTORNEY[-\s]EYES[-\s]ONLY)\b",
            request_text, re.IGNORECASE,
        )
        if privilege_hits or privilege_in_types:
            _markers = list({m.upper().replace(" ", "-") for m in privilege_hits}) if privilege_hits else ["PRIVILEGE_MARKER"]
            decision["allowed"] = False
            decision["override_tier"] = "block"
            decision["score_boost"] = 100
            decision["reason"] = (
                f"Privilege marker detected: {_markers[0]} content cannot be forwarded externally"
            )
            decision["flags"]["privilege_marker_detected"] = True
            decision["flags"]["privilege_markers"] = _markers
            return decision

        # External send rules
        if _looks_like_external_send(request_text):
            if external_access == "block":
                decision["allowed"] = False
                decision["override_tier"] = "block"
                decision["score_boost"] = 80
                decision["reason"] = f"External send blocked by policy for agent '{agent_id}'"
                decision["flags"]["external_send_blocked"] = True
                return decision
            elif external_access == "hard_confirm":
                decision["override_tier"] = _stricter_tier(decision.get("override_tier"), "hard")
                decision["score_boost"] = max(decision["score_boost"], 40)
                decision["flags"]["external_send"] = True

        return decision

    def _evaluate_healthcare(
        self,
        agent_id: str,
        request_text: str,
        entity_types: list,
        base_decision: dict,
    ) -> dict:
        """
        Healthcare domain overlay:
        - Special category protection: psychiatric & HIV records
        - Minimum necessary: flag access beyond declared entity scope
        - External send controls
        """
        decision = dict(base_decision)
        decision["flags"] = dict(base_decision.get("flags", {}))

        if not base_decision["allowed"]:
            # If the generic check blocked on a forbidden entity, classify it as a
            # HIPAA minimum-necessary violation so compliance reports track it correctly.
            if "forbidden_entity" in decision["flags"]:
                decision["flags"]["minimum_necessary_violation"] = True
            return decision

        agent_policy = self.policy.get("agents", {}).get(agent_id, {})
        special_override = agent_policy.get("special_category_override", "")
        external_send    = agent_policy.get("external_send", "")

        # Special category PHI detection
        special_refs = _extract_special_category_refs(request_text)
        if special_refs:
            # Only attending/treating specialist can override — otherwise block
            if not special_override or special_override in ("attending_physician_only", "treating_specialist_only"):
                decision["allowed"] = False
                decision["override_tier"] = "block"
                decision["score_boost"] = 100
                decision["reason"] = (
                    f"Special category PHI protection: access to "
                    f"{', '.join(special_refs)} requires treating specialist authorisation"
                )
                decision["flags"]["special_category_protection"] = True
                decision["flags"]["special_refs"] = special_refs
                return decision

        # Minimum necessary: check for entity types that exceed agent scope
        forbidden_et = [e.lower() for e in agent_policy.get("forbidden_entities", [])]
        for et in entity_types:
            if et.lower() in forbidden_et:
                decision["allowed"] = False
                decision["override_tier"] = "block"
                decision["score_boost"] = 80
                decision["reason"] = (
                    f"HIPAA minimum necessary violation: entity type '{et}' "
                    f"exceeds scope for agent '{agent_id}'"
                )
                decision["flags"]["minimum_necessary_violation"] = True
                decision["flags"]["excess_entity"] = et
                return decision

        # External send controls
        if _looks_like_external_send(request_text):
            if external_send == "hard_confirm":
                decision["override_tier"] = _stricter_tier(decision.get("override_tier"), "hard")
                decision["score_boost"] = max(decision["score_boost"], 40)
                decision["flags"]["external_send"] = True

        return decision

    # ── Private — YAML loader ──────────────────────────────────────────────────

    def _load(self, path: str):
        import yaml
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.policy = yaml.safe_load(f) or {}
            logger.info("PolicyEngine: loaded %s (domain=%s)", path, self.policy.get("domain", "generic"))
        except Exception as exc:
            logger.error("PolicyEngine: failed to load %s — %s", path, exc)
            self.policy = {}


# ── Helper functions ───────────────────────────────────────────────────────────

def _no_restriction_decision() -> dict:
    return {
        "allowed": True,
        "reason": "No policy restriction",
        "override_tier": None,
        "score_boost": 0,
        "flags": {},
    }


def _stricter_tier(current: Optional[str], candidate: str) -> str:
    """Return whichever tier is stricter (higher in the _TIER_ORDER)."""
    if current is None:
        return candidate
    if _TIER_ORDER.get(candidate, 0) > _TIER_ORDER.get(current, 0):
        return candidate
    return current


def _looks_like_bulk_export(text: str) -> bool:
    """Heuristic: does this request look like a bulk export attempt?"""
    patterns = [
        r"\ball\s+(records|files|documents|clients|patients|matters)\b",
        r"\bexport\s+(all|full|entire|complete)\b",
        r"\bdownload\s+(all|full|entire|complete)\b",
        r"\bfull\s+(client\s+list|patient\s+list|matter\s+list)\b",
        r"\bbulk\s+(export|download|retrieve|access)\b",
        r"\blast\s+\d+\s+days?\b.*\bexport\b",
        r"\bexport\b.*\blast\s+\d+\s+days?\b",
    ]
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in patterns)


def _looks_like_external_send(text: str) -> bool:
    """Heuristic: does this request involve sending data outside the organisation?"""
    patterns = [
        r"\bsend\b.*@",
        r"\bforward\b.*@",
        r"\bemail\b.*@",
        r"@\w+\.(com|org|net|io|co)\b",
        r"\bexternal\s+(email|recipient|address)\b",
        r"\boutside\s+(the\s+firm|the\s+hospital|the\s+org)\b",
    ]
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in patterns)


def _extract_matter_refs(text: str) -> list:
    """Extract MATTER-YYYY-NNN references from text."""
    return list(set(re.findall(r"\bMATTER-\d{4}-\d{3}\b", text, re.IGNORECASE)))


def _extract_special_category_refs(text: str) -> list:
    """
    Detect references to special category PHI that require elevated protection.
    Covers psychiatric, HIV, and substance abuse patient identifiers.
    """
    # Check for the specific high-sensitivity MRNs defined in scenarios.md
    sensitive_mrns = {"MRN-002391", "MRN-003712"}
    found = []
    for mrn in sensitive_mrns:
        if mrn in text:
            found.append(mrn)

    # Also check for keyword patterns
    patterns = [
        r"\bpsychiatric\s+(record|medication|history|note)\b",
        r"\bHIV\s+(status|diagnosis|treatment|medication)\b",
        r"\bsubstance\s+abuse\b",
        r"\bmental\s+health\s+record\b",
    ]
    text_lower = text.lower()
    for p in patterns:
        if re.search(p, text_lower):
            found.append(re.search(p, text_lower).group())

    return list(set(found)) if found else []


# ── Module-level singleton helpers ─────────────────────────────────────────────

# Maps deployment profile label → YAML filename
DEPLOYMENT_PROFILES = {
    "TechCorp Finance":           "agentguard_finance.yaml",
    "Pearson Hardman Legal":      "agentguard_lawfirm.yaml",
    "Memorial General Healthcare": "agentguard_hipaa.yaml",
}

_engine_instance: Optional["PolicyEngine"] = None


def get_policy_engine(policy_path: Optional[str] = None) -> "PolicyEngine":
    """Return a module-level singleton PolicyEngine, optionally reloading."""
    global _engine_instance
    if _engine_instance is None or (policy_path and _engine_instance.policy_path != policy_path):
        _engine_instance = PolicyEngine(policy_path)
    return _engine_instance
