"""
risk_scorer.py
--------------
Two-stage security pipeline for AgentGuard:

Stage 1 — Regex Pre-filter  (zero latency, zero cost)
    Catches known injection patterns and high-risk keywords before any AI call.

Stage 2 — AI Risk Scorer   (Azure OpenAI, ~1-2s)
    Contextual risk assessment returning a 0-100 score with 4-factor breakdown.
    Heuristic fallback if Azure is unavailable.

Intervention tier mapping:
    0-30  → AUTO      (green)   auto-execute
    31-60 → SOFT      (yellow)  soft confirm
    61-85 → HARD      (orange)  hard confirm + justification
    86+   → BLOCK     (red)     blocked + escalated
"""

import re
import json
import logging
import unicodedata
from dataclasses import dataclass, field
from typing import Optional
from azure_services import get_openai_service

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# INPUT NORMALIZER  (runs before every pre-filter check)
# ═══════════════════════════════════════════════════════════════

# Leetspeak / character-substitution map.
# Attackers use these to bypass naive regex: "1gn0r3 @ll pr3v10us"
_LEET_MAP = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a",
    "5": "s", "7": "t", "!": "i", "$": "s", "@": "a",
})

# Zero-width and invisible Unicode characters used to break patterns:
# zero-width space, zero-width non-joiner, zero-width joiner,
# BOM, soft hyphen, word joiner, left-to-right mark, right-to-left mark
_INVISIBLE_CHARS = re.compile(
    r"[\u200b\u200c\u200d\ufeff\u00ad\u2060\u200e\u200f]"
)


def _normalize_text(text: str) -> str:
    """
    Normalize input text to defeat common obfuscation techniques:

    1. NFKD unicode decomposition  — maps lookalike chars (cyrillic о → o, etc.)
    2. ASCII encoding              — strips remaining non-ASCII after decomposition
    3. Strip invisible characters  — zero-width spaces, soft hyphens, BOM, etc.
    4. Leetspeak substitution      — 0→o, 1→i, 3→e, @→a, $→s, 4→a, 5→s, 7→t
    5. Collapse whitespace         — "i g n o r e" → "ignore"
    6. Lowercase

    The ORIGINAL text is preserved everywhere else in the pipeline.
    Only the pre-filter uses this normalized copy.
    """
    # Step 1: NFKD decompose (ﬁ → fi, ｉ → i, ０ → 0, cyrillic lookalikes → latin)
    normalized = unicodedata.normalize("NFKD", text)
    # Step 2: Encode to ASCII, dropping unmappable chars
    normalized = normalized.encode("ascii", errors="ignore").decode("ascii")
    # Step 3: Strip invisible / zero-width characters
    normalized = _INVISIBLE_CHARS.sub("", normalized)
    # Step 4: Leetspeak substitution
    normalized = normalized.translate(_LEET_MAP)
    # Step 5: Collapse multiple whitespace to single space
    normalized = re.sub(r"\s+", " ", normalized).strip()
    # Step 6: Lowercase (pre-filter already uses re.IGNORECASE but normalizing is cleaner)
    return normalized.lower()


# ═══════════════════════════════════════════════════════════════
# STAGE 1: REGEX PRE-FILTER
# ═══════════════════════════════════════════════════════════════

# Patterns that indicate prompt-injection or extremely dangerous operations.
# Each tuple: (label, compiled regex)
# NOTE: These run against NORMALIZED text (lowercase, no leetspeak, no invisible chars).
_PREFILTER_PATTERNS = [
    # ── Prompt injection / jailbreak — direct commands ────────────────────
    ("prompt_injection",   re.compile(r"\bignore\s+(all\s+)?(previous|prior|above|earlier)\b", re.IGNORECASE)),
    ("prompt_injection",   re.compile(r"\bdisregard\s+(all\s+)?(previous|prior|above|instructions)\b", re.IGNORECASE)),
    ("prompt_injection",   re.compile(r"\bforget\s+(all\s+)?(previous|prior|above|instructions)\b", re.IGNORECASE)),
    ("prompt_injection",   re.compile(r"\bact\s+as\s+(if\s+you\s+are|a\s+different)\b", re.IGNORECASE)),
    ("prompt_injection",   re.compile(r"\byou\s+are\s+now\s+(?!a\s+financial)", re.IGNORECASE)),
    ("prompt_injection",   re.compile(r"\bnew\s+instructions?\b", re.IGNORECASE)),
    # ── Spaced-character obfuscation (e.g. "i g n o r e  a l l") ──────────
    # These catch attackers who insert spaces between each character to evade word-level patterns.
    ("prompt_injection",   re.compile(r"(?<!\w)i\s*g\s*n\s*o\s*r\s*e(?!\w)", re.IGNORECASE)),
    ("prompt_injection",   re.compile(r"(?<!\w)d\s*i\s*s\s*r\s*e\s*g\s*a\s*r\s*d(?!\w)", re.IGNORECASE)),
    ("prompt_injection",   re.compile(r"(?<!\w)f\s*o\s*r\s*g\s*e\s*t(?!\w)", re.IGNORECASE)),
    # ── Prompt injection — semantic rephrasings ────────────────────────────
    ("prompt_injection",   re.compile(r"\bset\s+aside\s+(your|the|all)?\s*(previous|earlier|prior|above|old)?\s*(rules?|guidelines?|instructions?|constraints?|policies)\b", re.IGNORECASE)),
    ("prompt_injection",   re.compile(r"\b(previous|prior|earlier)\s+(rules?|instructions?|guidelines?|constraints?)\s+(no\s+longer|don'?t|do\s+not|doesn'?t)\s+apply\b", re.IGNORECASE)),
    ("prompt_injection",   re.compile(r"\boverride\s+(your|the|system|all)\s*(instructions?|rules?|constraints?|guidelines?|policies)\b", re.IGNORECASE)),
    ("prompt_injection",   re.compile(r"\byour\s+(previous|prior|original|initial|system)\s+(instructions?|rules?|guidelines?|prompt)\b", re.IGNORECASE)),
    ("prompt_injection",   re.compile(r"\bpretend\s+(you\s+are|to\s+be|you'?re)\b", re.IGNORECASE)),
    ("prompt_injection",   re.compile(r"\bimagine\s+you\s+(are|have\s+no)\b", re.IGNORECASE)),
    ("prompt_injection",   re.compile(r"\bfrom\s+now\s+on\s+(you|ignore|act|behave|respond)\b", re.IGNORECASE)),
    # ── Mode/role override ─────────────────────────────────────────────────
    ("mode_override",      re.compile(r"\bswitch\s+(to|into)\s+(admin|unrestricted|unlimited|debug|god|developer?|root|maintenance)\s*mode\b", re.IGNORECASE)),
    ("mode_override",      re.compile(r"\b(admin|developer?|debug|god|maintenance|unrestricted)\s+mode\s*(enabled?|activated?|on)\b", re.IGNORECASE)),
    ("mode_override",      re.compile(r"\byou\s+(have\s+no\s+restrictions?|are\s+unrestricted|can\s+do\s+anything)\b", re.IGNORECASE)),
    # ── Bypass / disable safety ────────────────────────────────────────────
    ("safety_bypass",      re.compile(r"\b(bypass|skip|circumvent|disable|turn\s+off|deactivate)\s+(security|safety|filter|guard|check|restriction|policy|policies)\b", re.IGNORECASE)),
    ("safety_bypass",      re.compile(r"\bwithout\s+(any|the)?\s*(checks?|verification|approval|authorization|restrictions?|oversight)\b", re.IGNORECASE)),
    ("safety_bypass",      re.compile(r"\b(do\s+not|don'?t|never)\s+(log|audit|track|record|report|flag)\s+(this|anything|it)\b", re.IGNORECASE)),
    ("safety_bypass",      re.compile(r"\bdelete\s+(all\s+)?(audit|log|logs?|trail|history|records?)\b", re.IGNORECASE)),
    # ── Suspicious fund transfers ──────────────────────────────────────────
    ("suspicious_transfer", re.compile(r"\btransfer\b.{0,60}\$[\d,]*[5-9]\d{2},\d{3}", re.IGNORECASE)),  # $500K+
    ("suspicious_transfer", re.compile(r"\btransfer\b.{0,60}\$[\d,]+[Mm]\b", re.IGNORECASE)),             # $1M+
    ("suspicious_transfer", re.compile(r"\bwire\s+(funds?|money|payment|transfer)\b", re.IGNORECASE)),
    # ── Mass destructive operations ────────────────────────────────────────
    ("destructive_op",     re.compile(r"\bdelete\s+all\b", re.IGNORECASE)),
    ("destructive_op",     re.compile(r"\bdrop\s+(table|database|all)\b", re.IGNORECASE)),
    ("destructive_op",     re.compile(r"\btruncate\s+(table|all)\b", re.IGNORECASE)),
    ("destructive_op",     re.compile(r"\bpurge\s+all\b", re.IGNORECASE)),
    # ── Privilege escalation ───────────────────────────────────────────────
    ("privilege_escalation", re.compile(r"\bgrant\s+(admin|root|superuser|all\s+privileges)\b", re.IGNORECASE)),
    ("privilege_escalation", re.compile(r"\belevate\s+(privileges?|permissions?|access)\b", re.IGNORECASE)),
    # ── External exfiltration ──────────────────────────────────────────────
    ("exfiltration",       re.compile(r"\bsend\s+.{0,40}@[a-z0-9.\-]+\.[a-z]{2,}\b", re.IGNORECASE)),
    ("exfiltration",       re.compile(r"\bexport\s+all\b", re.IGNORECASE)),
]

@dataclass
class PreFilterResult:
    triggered: bool
    matched_patterns: list[str] = field(default_factory=list)
    matched_texts: list[str] = field(default_factory=list)

def run_prefilter(text: str) -> PreFilterResult:
    """
    Run all regex pre-filter patterns against the input text.

    Matches against BOTH:
    - The normalized text (catches leetspeak, unicode lookalikes, obfuscation)
    - The original text (catches exact patterns that normalization might alter)

    Returns immediately after collecting all matches (does not short-circuit
    on first match — we want to surface all triggered patterns for the audit log).
    """
    normalized = _normalize_text(text)
    matched_patterns = []
    matched_texts = []
    seen_labels = set()  # deduplicate same label triggered by both original+normalized

    for label, pattern in _PREFILTER_PATTERNS:
        # Check normalized first (catches obfuscation)
        m = pattern.search(normalized)
        if not m:
            # Fallback: check original (catches patterns that normalization might mangle)
            m = pattern.search(text)
        if m:
            key = (label, m.group().lower()[:40])
            if key not in seen_labels:
                matched_patterns.append(label)
                matched_texts.append(m.group())
                seen_labels.add(key)

    triggered = len(matched_patterns) > 0
    return PreFilterResult(triggered=triggered, matched_patterns=matched_patterns, matched_texts=matched_texts)


# ═══════════════════════════════════════════════════════════════
# STAGE 2: AI RISK SCORER
# ═══════════════════════════════════════════════════════════════

_RISK_SYSTEM_PROMPT = """You are a security risk assessment engine for a financial AI agent.
Score the following action request on a scale of 0-100 based on these 4 factors (each 0-25):

1. data_sensitivity   — Does it involve PII, financial data, credentials?
2. reversibility      — How difficult is it to undo this action? (25 = irreversible)
3. blast_radius       — How many people/records are affected?
4. policy_compliance  — Does this violate standard financial controls?

You receive ANONYMIZED text and metadata context. Use both to score accurately.

Return ONLY valid JSON with no markdown fences:
{
  "total_score": <integer 0-100>,
  "factors": {
    "data_sensitivity": <integer 0-25>,
    "reversibility": <integer 0-25>,
    "blast_radius": <integer 0-25>,
    "policy_compliance": <integer 0-25>
  },
  "reasoning": "<one concise sentence explaining the main risk>"
}"""


@dataclass
class RiskScore:
    total: int
    factors: dict
    reasoning: str
    tier: str                  # auto / soft / hard / block
    tier_color: str            # green / yellow / orange / red
    scored_by: str = "azure_openai"
    prefilter_triggered: bool = False
    prefilter_patterns: list[str] = field(default_factory=list)
    content_safety_blocked: bool = False


def _score_to_tier(score: int) -> tuple[str, str]:
    """Map numeric score to (tier_name, color)."""
    if score <= 30:
        return "auto", "green"
    elif score <= 60:
        return "soft", "yellow"
    elif score <= 85:
        return "hard", "orange"
    else:
        return "block", "red"


def _heuristic_score(text: str, metadata: dict) -> RiskScore:
    """
    Rule-based fallback scorer used when Azure OpenAI is unavailable.
    Produces a conservative but realistic score.
    """
    text_lower = text.lower()
    score = 12  # baseline (read-only query starts here)
    factors = {"data_sensitivity": 2, "reversibility": 2, "blast_radius": 2, "policy_compliance": 4}

    # Data sensitivity
    if metadata.get("contains_financial_amount"):
        factors["data_sensitivity"] += 15
    if metadata.get("contains_email"):
        factors["data_sensitivity"] += 8
    if metadata.get("person_count", 0) > 0:
        factors["data_sensitivity"] += 5

    # Reversibility
    if any(w in text_lower for w in ["delete", "remove", "drop", "purge"]):
        factors["reversibility"] += 22
    elif any(w in text_lower for w in ["transfer", "send", "wire", "pay"]):
        factors["reversibility"] += 18
    elif any(w in text_lower for w in ["email", "report", "notify", "forward"]):
        factors["reversibility"] += 14  # emails can't be unsent

    # Blast radius
    if "all" in text_lower:
        factors["blast_radius"] += 20
    elif metadata.get("person_count", 0) > 2:
        factors["blast_radius"] += 10

    # Policy compliance
    magnitude = metadata.get("financial_magnitude", "")
    if "100K+" in magnitude or "1M+" in magnitude:
        factors["policy_compliance"] += 18
    elif "10K-100K" in magnitude:
        factors["policy_compliance"] += 10

    # Clamp each factor to the valid 0-25 range before summing
    factors = {k: max(0, min(25, v)) for k, v in factors.items()}
    total = min(100, sum(factors.values()))
    tier, color = _score_to_tier(total)
    return RiskScore(
        total=total,
        factors=factors,
        reasoning="Heuristic score based on detected keywords and metadata.",
        tier=tier,
        tier_color=color,
        scored_by="heuristic_fallback",
    )


# ═══════════════════════════════════════════════════════════════
# ATTACK VECTOR DETECTION
# ═══════════════════════════════════════════════════════════════

_ATTACK_VECTOR_PATTERNS = [
    ("Prompt Injection",         re.compile(r"\b(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above|instructions)\b", re.IGNORECASE)),
    ("Jailbreak Attempt",        re.compile(r"\b(act\s+as|you\s+are\s+now|pretend\s+you\s+are|imagine\s+you\s+are)\b", re.IGNORECASE)),
    ("Role Override",            re.compile(r"\bnew\s+instructions?\b|\byour\s+new\s+(role|task|job)\b", re.IGNORECASE)),
    ("Semantic Rephrasing",      re.compile(r"\b(set\s+aside|override)\s+(your|the|all)?\s*(previous|prior|earlier|system)?\s*(rules?|guidelines?|instructions?|constraints?)\b", re.IGNORECASE)),
    ("Mode Override",            re.compile(r"\b(switch\s+to|enable|activate)\s+(admin|unrestricted|debug|god|developer?|root)\s*mode\b", re.IGNORECASE)),
    ("Safety Bypass",            re.compile(r"\b(bypass|circumvent|disable|skip)\s+(security|safety|filter|guard|check|restriction)\b", re.IGNORECASE)),
    ("Audit Suppression",        re.compile(r"\b(do\s+not|don'?t|never)\s+(log|audit|track|record)\b|\bdelete\s+(all\s+)?(audit|log|trail)\b", re.IGNORECASE)),
    ("Privilege Escalation",     re.compile(r"\b(grant|elevate)\s+(admin|root|superuser|privileges?|permissions?)\b", re.IGNORECASE)),
    ("Mass Data Exfiltration",   re.compile(r"\b(export|send|forward)\s+all\b", re.IGNORECASE)),
    ("Destructive Operation",    re.compile(r"\b(delete|drop|truncate|purge)\s+all\b", re.IGNORECASE)),
    ("Suspicious Wire Transfer", re.compile(r"\b(wire|transfer)\s+(funds?|money|payment)\b", re.IGNORECASE)),
    ("External Data Send",       re.compile(r"\bsend\s+.{0,40}@[a-z0-9.\-]+\.[a-z]{2,}\b", re.IGNORECASE)),
    ("Credential Harvesting",    re.compile(r"\b(password|api.?key|secret|token|credential)\b", re.IGNORECASE)),
    ("Social Engineering",       re.compile(r"\b(urgently|immediately|without\s+(any\s+)?checks?|bypass)\b", re.IGNORECASE)),
    ("Obfuscation Attempt",      re.compile(r"[il1|][g9][n][o0][r][e3]|[d][i1][s$][r][e3][g9][a@][r][d]", re.IGNORECASE)),  # leetspeak patterns in raw text
]

_FAST_PATH_BLOCKLIST = re.compile(
    r"\b(delete|drop|truncate|purge|transfer|wire|send|email|export|grant|elevate|ignore|disregard|forget|password|secret|token|credential|bypass|urgently|immediately)\b",
    re.IGNORECASE,
)


class RiskScorer:
    """
    Orchestrates pre-filter + AI risk scoring + intervention tier mapping.
    """

    def __init__(self):
        self.openai_svc = get_openai_service()

    # ----------------------------------------------------------
    def score(
        self,
        original_text: str,
        anonymized_text: str,
        metadata: dict,
        content_safety_blocked: bool = False,
    ) -> RiskScore:
        """
        Full scoring pipeline.

        1. Run regex pre-filter on ORIGINAL text (before PII removal).
        2. If blocked, return BLOCK tier immediately.
        3. Otherwise score the ANONYMIZED text + metadata via Azure OpenAI.
        4. Fall back to heuristic scorer if Azure fails.
        """
        # Step 1: pre-filter
        prefilter = run_prefilter(original_text)

        if prefilter.triggered or content_safety_blocked:
            reason = (
                f"Pre-filter matched: {', '.join(prefilter.matched_patterns)}"
                if prefilter.triggered
                else "Azure AI Content Safety flagged harmful content."
            )
            return RiskScore(
                total=98,
                factors={"data_sensitivity": 25, "reversibility": 25, "blast_radius": 25, "policy_compliance": 23},
                reasoning=reason,
                tier="block",
                tier_color="red",
                scored_by="prefilter",
                prefilter_triggered=prefilter.triggered,
                prefilter_patterns=prefilter.matched_patterns,
                content_safety_blocked=content_safety_blocked,
            )

        # Step 2: AI risk scoring
        ai_result = self._azure_score(anonymized_text, metadata)
        if ai_result is not None:
            ai_result.prefilter_triggered = False
            ai_result.prefilter_patterns = []
            return ai_result

        # Step 3: heuristic fallback
        logger.warning("Azure risk scoring failed; using heuristic fallback")
        result = _heuristic_score(anonymized_text, metadata)
        result.prefilter_triggered = False
        return result

    # ----------------------------------------------------------
    def _azure_score(self, anonymized_text: str, metadata: dict) -> Optional[RiskScore]:
        """
        Call Azure OpenAI for risk scoring.
        Returns RiskScore on success, None on failure.
        """
        user_message = (
            f"Anonymized action: {anonymized_text}\n"
            f"Context metadata: {json.dumps(metadata)}\n\n"
            "Note: 'contains_email: true' means this action sends data to an external recipient "
            "which increases both data_sensitivity and reversibility scores."
        )
        raw = self.openai_svc.chat_complete(
            system_prompt=_RISK_SYSTEM_PROMPT,
            user_message=user_message,
            temperature=0.0,
            max_tokens=400,
        )
        if raw is None:
            return None

        # Strip possible markdown fences
        clean = raw.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```[a-z]*\n?", "", clean)
            clean = re.sub(r"\n?```$", "", clean)

        try:
            data = json.loads(clean)
            total = int(data.get("total_score", 50))
            total = max(0, min(100, total))  # clamp
            factors = data.get("factors", {
                "data_sensitivity": 0,
                "reversibility": 0,
                "blast_radius": 0,
                "policy_compliance": 0,
            })
            # Ensure all four factors present
            for f in ("data_sensitivity", "reversibility", "blast_radius", "policy_compliance"):
                factors.setdefault(f, 0)

            reasoning = data.get("reasoning", "No reasoning provided.")
            tier, color = _score_to_tier(total)
            return RiskScore(
                total=total,
                factors=factors,
                reasoning=reasoning,
                tier=tier,
                tier_color=color,
                scored_by="azure_openai",
            )
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("Risk score JSON parse error: %s | raw=%s", exc, raw[:200])
            return None

    # ----------------------------------------------------------
    def detect_attack_vectors(self, text: str) -> list[dict]:
        """
        Scan text for known attack patterns and return a list of findings.
        Checks both original and normalized text to catch obfuscated attacks.
        Each finding: {"vector": str, "matched_text": str}
        """
        normalized = _normalize_text(text)
        findings = []
        seen = set()
        for vector_name, pattern in _ATTACK_VECTOR_PATTERNS:
            m = pattern.search(normalized) or pattern.search(text)
            if m and vector_name not in seen:
                findings.append({"vector": vector_name, "matched_text": m.group()})
                seen.add(vector_name)
        return findings

    # ----------------------------------------------------------
    def is_fast_path_eligible(self, text: str) -> bool:
        """
        Return True if the request is simple enough to skip AI risk scoring
        (i.e. no sensitive keywords detected and text is short).
        Fast-path requests get an automatic heuristic score of 10 (auto tier).
        """
        if len(text) > 200:
            return False
        if _FAST_PATH_BLOCKLIST.search(text):
            return False
        return True


# ─────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────
_risk_scorer_instance: Optional[RiskScorer] = None

def get_risk_scorer() -> RiskScorer:
    global _risk_scorer_instance
    if _risk_scorer_instance is None:
        _risk_scorer_instance = RiskScorer()
    return _risk_scorer_instance
