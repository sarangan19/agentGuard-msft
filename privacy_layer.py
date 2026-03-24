"""
privacy_layer.py
----------------
PII detection and anonymization layer for AgentGuard.

Flow:
  1. Call Azure OpenAI to detect PII entities and receive structured JSON.
  2. Replace each entity with a unique placeholder: [PERSON_A], [EMAIL_A], etc.
  3. Store the reverse mapping so agent responses can be de-anonymized later.
  4. Regex fallback ensures the layer still works if Azure OpenAI is unavailable.

Domain modes:
  - generic    : standard PII (PERSON, EMAIL, PHONE, AMOUNT, ACCOUNT, SSN, ADDRESS, ORG)
  - healthcare : adds HIPAA PHI patterns (MRN, ICD_CODE, NPI_NUMBER, MEDICATION, etc.)
  - legal      : adds legal-privilege patterns (MATTER_REF, BATES_NUMBER, PRIVILEGE_MARKER, etc.)
"""

import re
import json
import logging
from typing import Optional
from azure_services import get_openai_service

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# DOMAIN-SPECIFIC PROMPT ADDONS
# ─────────────────────────────────────────────────────────────
_HEALTHCARE_PROMPT_ADDON = """

Additionally, this is a HEALTHCARE context. Also detect and label:
- MRN: medical record numbers (e.g. MRN-001847, MRN001847)
- ICD_CODE: diagnosis codes (e.g. J18.9, Z23, M79.3)
- NPI_NUMBER: 10-digit National Provider Identifiers (e.g. NPI 1234567890)
- DEA_NUMBER: DEA prescriber numbers (e.g. DEA AB1234567)
- INSURANCE_ID: insurance member or policy IDs
- DATE_OF_SERVICE: clinical service dates
- MEDICATION: drug names and dosages

HIPAA minimum-necessary rule: note in metadata if the request appears to access
more PHI categories than the stated clinical purpose requires. Set
"minimum_necessary_concern": true and list "excess_phi_types" if so."""

_LEGAL_PROMPT_ADDON = """

Additionally, this is a LEGAL context. Also detect and label:
- MATTER_REF: case/matter references (e.g. MATTER-2024-001)
- BATES_NUMBER: document production numbers (e.g. ACME000123)
- BAR_ID: attorney bar numbers
- PRIVILEGE_MARKER: privilege markers (PRIVILEGED, ATTORNEY-CLIENT, WORK PRODUCT)

Attorney-client privilege rule: set "privilege_markers_detected": true in metadata
if any privileged communication markers are found."""

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
# REGEX FALLBACK PATTERNS — generic
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

# ─────────────────────────────────────────────────────────────
# REGEX FALLBACK PATTERNS — healthcare (HIPAA PHI)
# ─────────────────────────────────────────────────────────────
_HEALTHCARE_REGEX_PATTERNS = [
    # Medical Record Number: MRN-001847 / MRN001847 / MRN: 001847
    ("MRN", re.compile(r"\bMRN[-:\s]?\d{6,10}\b", re.IGNORECASE)),
    # ICD-10 diagnosis codes: J18.9 / Z23 / M79.3 / F32.1
    ("ICD_CODE", re.compile(r"\b[A-Z]\d{2}(?:\.\d{1,4})?\b")),
    # National Provider Identifier: NPI 1234567890
    ("NPI_NUMBER", re.compile(r"\bNPI[-:\s]?\d{10}\b", re.IGNORECASE)),
    # DEA prescriber number: DEA AB1234567
    ("DEA_NUMBER", re.compile(r"\bDEA[-:\s]?[A-Z]{2}\d{7}\b", re.IGNORECASE)),
    # Insurance member / policy IDs
    ("INSURANCE_ID", re.compile(r"\b(?:INS|MEM|POL|GRP)[-:\s]?\d{8,12}\b", re.IGNORECASE)),
    # Clinical service date (MM/DD/YYYY or MM-DD-YYYY) — distinct from generic dates
    ("DATE_OF_SERVICE", re.compile(r"\b(?:0[1-9]|1[0-2])[/\-](?:0[1-9]|[12]\d|3[01])[/\-](?:19|20)\d{2}\b")),
    # Common medications (RxNorm names — includes psychiatric, HIV, and substance abuse drugs
    # to ensure special-category PHI is always caught by the regex fallback)
    ("MEDICATION", re.compile(
        r"\b(?:metformin|lisinopril|atorvastatin|amlodipine|omeprazole|simvastatin|"
        r"losartan|azithromycin|gabapentin|hydrocodone|oxycodone|sertraline|fluoxetine|"
        r"quetiapine|olanzapine|risperidone|clozapine|lithium|valproate|buprenorphine|"
        r"naltrexone|methadone|suboxone|tenofovir|emtricitabine|efavirenz|atazanavir|"
        r"dolutegravir|abacavir|rilpivirine|insulin|levothyroxine|warfarin|clopidogrel|"
        r"furosemide|prednisone|albuterol|alprazolam|lorazepam|diazepam|zolpidem)\b",
        re.IGNORECASE,
    )),
]

# ─────────────────────────────────────────────────────────────
# REGEX FALLBACK PATTERNS — legal (attorney-client privilege)
# ─────────────────────────────────────────────────────────────
_LEGAL_REGEX_PATTERNS = [
    # Matter references: MATTER-2024-001
    ("MATTER_REF", re.compile(r"\bMATTER-\d{4}-\d{3}\b", re.IGNORECASE)),
    # Bates numbers: ACME000123 / PH000001 (2-6 alpha prefix + 6-10 digits)
    ("BATES_NUMBER", re.compile(r"\b[A-Z]{2,6}\d{6,10}\b")),
    # Attorney bar numbers
    ("BAR_ID", re.compile(r"\bBar\s*(?:No\.?|Number|#)?\s*\d{5,8}\b", re.IGNORECASE)),
    # Privilege markers
    ("PRIVILEGE_MARKER", re.compile(
        r"\b(?:PRIVILEGED|ATTORNEY[-\s]CLIENT|WORK\s+PRODUCT|"
        r"ATTORNEY[-\s]EYES[-\s]ONLY|PRIVILEGED\s+AND\s+CONFIDENTIAL)\b",
        re.IGNORECASE,
    )),
]


def _regex_detect_pii(text: str, extra_patterns: list | None = None) -> dict:
    """
    Fallback PII detector using regular expressions.
    extra_patterns: additional (type, compiled_pattern) tuples appended after base patterns.
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

    all_patterns = list(_REGEX_PATTERNS) + (extra_patterns or [])
    for pii_type, pattern in all_patterns:
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
    def detect_and_anonymize(self, text: str, domain: str = "generic") -> dict:
        """
        Primary method.
        domain: "generic" | "healthcare" | "legal" — activates domain-specific
                PHI/privilege patterns on top of standard PII detection.
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
        pii_data = self._azure_detect(text, domain=domain)
        method = "azure_openai"

        if pii_data is None:
            logger.warning("Azure PII detection failed; using regex fallback")
            extra = self._domain_regex_patterns(domain)
            pii_data = _regex_detect_pii(text, extra_patterns=extra)
            method = "regex_fallback"
        else:
            # Azure handled primary detection; run domain regex additively to catch
            # any patterns the LLM may have missed (belt-and-suspenders for PHI)
            extra = self._domain_regex_patterns(domain)
            if extra:
                existing_originals = {p.get("original", "") for p in pii_data.get("pii_found", [])}
                extra_data = _regex_detect_pii(text, extra_patterns=extra)
                for item in extra_data.get("pii_found", []):
                    if item.get("original") not in existing_originals:
                        pii_data["pii_found"].append(item)

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

        # Tag domain-specific metadata fields
        all_types = {item.get("type", "") for item in pii_found}
        if domain == "healthcare":
            phi_types = [t for t in all_types if t in {
                "MRN", "ICD_CODE", "NPI_NUMBER", "DEA_NUMBER",
                "INSURANCE_ID", "DATE_OF_SERVICE", "MEDICATION",
            }]
            metadata["healthcare_phi_detected"] = bool(phi_types)
            metadata["phi_types"] = phi_types
        elif domain == "legal":
            legal_types = [t for t in all_types if t in {
                "MATTER_REF", "BATES_NUMBER", "BAR_ID", "PRIVILEGE_MARKER",
            }]
            metadata["legal_entities_detected"] = bool(legal_types)
            metadata["legal_types"] = legal_types
            metadata["privilege_markers_detected"] = "PRIVILEGE_MARKER" in all_types

        return {
            "original_text": text,
            "anonymized_text": anonymized_text,
            "pii_found": pii_found,
            "metadata": metadata,
            "mapping": mapping,
            "reverse_mapping": reverse_mapping,
            "detection_method": method,
            "entity_count": len(pii_found),
            "domain": domain,
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
    def inject_canary(self, text: str, domain: str = "generic") -> tuple[str, str]:
        """
        Append a domain-specific sentinel token to the anonymized text.
        The token is invisible to normal operation — only its presence in the
        agent's output reveals an exfiltration attempt.

        Returns (modified_text, canary_token).

        Token formats:
          finance    → canary-{token}@agentguard-sentinel.io
          legal      → MATTER-CANARY-{token}
          healthcare → MRN-CANARY-{token}
        """
        import uuid
        token = str(uuid.uuid4())[:8].upper()
        if domain == "legal":
            canary = f"MATTER-CANARY-{token}"
        elif domain == "healthcare":
            canary = f"MRN-CANARY-{token}"
        else:
            canary = f"canary-{token}@agentguard-sentinel.io"
        modified = f"{text} [CONTEXT_REF: {canary}]"
        return modified, canary

    # ----------------------------------------------------------
    def check_canary_leak(self, agent_output: str, canary_token: str) -> bool:
        """
        Return True if the canary token appears anywhere in the agent's response.
        A match means the agent echoed the sentinel back — potential exfiltration.
        """
        return canary_token in (agent_output or "")

    # ----------------------------------------------------------
    def _domain_regex_patterns(self, domain: str) -> list:
        """Return the extra regex pattern list for the given domain."""
        if domain == "healthcare":
            return _HEALTHCARE_REGEX_PATTERNS
        elif domain == "legal":
            return _LEGAL_REGEX_PATTERNS
        return []

    # ----------------------------------------------------------
    def _azure_detect(self, text: str, domain: str = "generic") -> Optional[dict]:
        """
        Call Azure OpenAI for PII detection.
        Appends domain-specific instructions to the system prompt when domain != "generic".
        Returns parsed dict on success, None on any failure.
        """
        prompt = _PII_SYSTEM_PROMPT
        if domain == "healthcare":
            prompt = prompt + _HEALTHCARE_PROMPT_ADDON
        elif domain == "legal":
            prompt = prompt + _LEGAL_PROMPT_ADDON

        raw = self.openai_svc.chat_complete(
            system_prompt=prompt,
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
