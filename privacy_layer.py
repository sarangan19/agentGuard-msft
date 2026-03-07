"""
privacy_layer.py
----------------
PII detection and anonymization layer for AgentGuard.

Flow:
  1. Call Azure OpenAI to detect PII entities and receive structured JSON.
  2. Replace each entity with a unique placeholder: [PERSON_A], [EMAIL_A], etc.
  3. Store the reverse mapping so agent responses can be de-anonymized later.
  4. Regex fallback ensures the layer still works if Azure OpenAI is unavailable.
"""

import re
import json
import logging
from typing import Optional
from azure_services import get_openai_service

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# PII DETECTION PROMPT
# ─────────────────────────────────────────────────────────────
_PII_SYSTEM_PROMPT = """You are a PII detection engine for a financial security system.
Analyze the text and return a JSON object identifying ALL personally identifiable information.

For each PII item return:
- "original": the exact text as it appears
- "type": one of [PERSON, EMAIL, PHONE, AMOUNT, ACCOUNT, SSN, ADDRESS, ORG]
- "placeholder": a unique placeholder like [PERSON_A], [AMOUNT_A], [ORG_A], etc.

Also include a "metadata" object that summarizes what sensitive data types are present
WITHOUT including the actual values.

Return ONLY valid JSON. No markdown fences. No explanation.

Example:
Input: "Transfer $50,000 to John Smith at john@acme.com"
Output:
{
  "pii_found": [
    {"original": "John Smith", "type": "PERSON", "placeholder": "[PERSON_A]"},
    {"original": "$50,000", "type": "AMOUNT", "placeholder": "[AMOUNT_A]"},
    {"original": "john@acme.com", "type": "EMAIL", "placeholder": "[EMAIL_A]"}
  ],
  "metadata": {
    "person_count": 1,
    "contains_financial_amount": true,
    "financial_magnitude": "10K-100K",
    "contains_email": true,
    "contains_external_entity": true,
    "entity_types": ["PERSON", "AMOUNT", "EMAIL"]
  }
}"""


# ─────────────────────────────────────────────────────────────
# REGEX FALLBACK PATTERNS
# ─────────────────────────────────────────────────────────────
_REGEX_PATTERNS = [
    # Dollar amounts: $50,000  /  $1.5M  /  $500K
    ("AMOUNT", re.compile(r"\$[\d,]+(?:\.\d+)?[KkMmBb]?|\b\d[\d,]*(?:\.\d+)?\s*(?:dollars?|USD)\b", re.IGNORECASE)),
    # Email addresses
    ("EMAIL", re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b")),
    # Phone numbers (US-style)
    ("PHONE", re.compile(r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b")),
    # SSN
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    # Bank account numbers (8-17 digits standalone)
    ("ACCOUNT", re.compile(r"\b\d{8,17}\b")),
    # Capitalized names (naive: two+ consecutive capitalized words not at sentence start)
    ("PERSON", re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")),
]


def _regex_detect_pii(text: str) -> dict:
    """
    Fallback PII detector using regular expressions.
    Returns the same structure as the Azure OpenAI response.
    """
    pii_found = []
    type_counters: dict[str, int] = {}
    used_spans: list[tuple[int, int]] = []

    def _letter(n: int) -> str:
        """Convert 0 -> A, 1 -> B, ... 25 -> Z, 26 -> AA ..."""
        result = ""
        n += 1
        while n:
            n, r = divmod(n - 1, 26)
            result = chr(65 + r) + result
        return result

    for pii_type, pattern in _REGEX_PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.span()
            # Skip if this span overlaps with an already-captured entity
            # Uses the standard half-open interval overlap check: two intervals
            # [start,end) and [s,e) overlap iff start < e and s < end.
            if any(start < e and s < end for s, e in used_spans):
                continue
            count = type_counters.get(pii_type, 0)
            placeholder = f"[{pii_type}_{_letter(count)}]"
            pii_found.append({
                "original": match.group(),
                "type": pii_type,
                "placeholder": placeholder,
            })
            type_counters[pii_type] = count + 1
            used_spans.append((start, end))

    entity_types = list(type_counters.keys())
    metadata = {
        "person_count": type_counters.get("PERSON", 0),
        "contains_financial_amount": "AMOUNT" in type_counters,
        "financial_magnitude": "unknown",
        "contains_email": "EMAIL" in type_counters,
        "contains_external_entity": "EMAIL" in type_counters or "ORG" in type_counters,
        "entity_types": entity_types,
        "detected_by": "regex_fallback",
    }
    return {"pii_found": pii_found, "metadata": metadata}


# ═══════════════════════════════════════════════════════════════
# PRIVACY LAYER  (main entry point)
# ═══════════════════════════════════════════════════════════════

class PrivacyLayer:
    """
    Detects PII, anonymizes text, and provides de-anonymization.
    Uses Azure OpenAI as primary; regex as fallback.
    """

    def __init__(self):
        self.openai_svc = get_openai_service()

    # ----------------------------------------------------------
    def detect_and_anonymize(self, text: str) -> dict:
        """
        Primary method.
        Returns:
          {
            "original_text":    str,
            "anonymized_text":  str,
            "pii_found":        list[dict],
            "metadata":         dict,
            "mapping":          dict  # placeholder -> original
            "reverse_mapping":  dict  # original -> placeholder
            "detection_method": "azure_openai" | "regex_fallback"
          }
        """
        pii_data = self._azure_detect(text)
        method = "azure_openai"

        if pii_data is None:
            logger.warning("Azure PII detection failed; using regex fallback")
            pii_data = _regex_detect_pii(text)
            method = "regex_fallback"

        pii_found = pii_data.get("pii_found", [])
        metadata = pii_data.get("metadata", {})

        anonymized_text = text
        mapping: dict[str, str] = {}        # placeholder -> original
        reverse_mapping: dict[str, str] = {}  # original -> placeholder

        # Sort by length descending so longer strings are replaced first
        # (prevents partial replacement of overlapping entities)
        sorted_pii = sorted(pii_found, key=lambda x: len(x.get("original", "")), reverse=True)

        for item in sorted_pii:
            original = item.get("original", "")
            placeholder = item.get("placeholder", "")
            if original and placeholder:
                anonymized_text = anonymized_text.replace(original, placeholder)
                mapping[placeholder] = original
                reverse_mapping[original] = placeholder

        return {
            "original_text": text,
            "anonymized_text": anonymized_text,
            "pii_found": pii_found,
            "metadata": metadata,
            "mapping": mapping,
            "reverse_mapping": reverse_mapping,
            "detection_method": method,
            "entity_count": len(pii_found),
        }

    # ----------------------------------------------------------
    def scan_output(self, text: str) -> dict:
        """
        Scan agent output / response for PII that shouldn't be exposed.

        The agent receives anonymized text as input, but could still generate
        responses that contain or reconstruct PII. This method catches that.

        Uses the regex patterns only (fast, no API call) since this is a
        post-processing safety net, not a primary detection mechanism.

        Returns:
          {
            "original_output":  str,
            "sanitized_output": str,   # PII replaced with [REDACTED]
            "leaks_found":      int,
            "leaked_types":     list[str],
          }
        """
        pii_data = _regex_detect_pii(text)
        leaked = pii_data.get("pii_found", [])

        sanitized = text
        for item in sorted(leaked, key=lambda x: len(x.get("original", "")), reverse=True):
            original = item.get("original", "")
            if original:
                sanitized = sanitized.replace(original, "[REDACTED]")

        return {
            "original_output":  text,
            "sanitized_output": sanitized,
            "leaks_found":      len(leaked),
            "leaked_types":     [i.get("type", "UNKNOWN") for i in leaked],
        }

    # ----------------------------------------------------------
    def de_anonymize(self, text: str, mapping: dict) -> str:
        """
        Restore original values in agent response text.
        mapping: { "[PERSON_A]": "John Smith", ... }
        """
        result = text
        # Sort by placeholder length descending to avoid partial replacements
        for placeholder, original in sorted(mapping.items(), key=lambda kv: len(kv[0]), reverse=True):
            result = result.replace(placeholder, original)
        return result

    # ----------------------------------------------------------
    def _azure_detect(self, text: str) -> Optional[dict]:
        """
        Call Azure OpenAI for PII detection.
        Returns parsed dict on success, None on any failure.
        """
        raw = self.openai_svc.chat_complete(
            system_prompt=_PII_SYSTEM_PROMPT,
            user_message=text,
            temperature=0.0,
            max_tokens=800,
        )
        if raw is None:
            return None

        # Strip possible markdown code fences
        clean = raw.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```[a-z]*\n?", "", clean)
            clean = re.sub(r"\n?```$", "", clean)

        try:
            data = json.loads(clean)
            # Validate expected structure
            if "pii_found" not in data:
                data["pii_found"] = []
            if "metadata" not in data:
                data["metadata"] = {}
            return data
        except json.JSONDecodeError as exc:
            logger.error("PII detection JSON parse error: %s | raw=%s", exc, raw[:200])
            return None


# ─────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────
_privacy_layer_instance: Optional[PrivacyLayer] = None

def get_privacy_layer() -> PrivacyLayer:
    global _privacy_layer_instance
    if _privacy_layer_instance is None:
        _privacy_layer_instance = PrivacyLayer()
    return _privacy_layer_instance
