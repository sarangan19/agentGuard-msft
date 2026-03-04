# AgentGuard Pre-Submission Fix List

**Audit date:** 2026-03-03 | **Total issues:** 13 (6 High, 4 Medium, 3 Low) | **Estimated time:** ~18 minutes

---

## CRITICAL / HIGH PRIORITY

### Fix 1: API keys printed to terminal (SECURITY)
**File:** `test_azure.py:53`

**Current:**
```python
print(f"{PASS}  {var} = {val[:30]}...")
```
**Replace with:**
```python
masked = val[:4] + "*" * 20 + val[-4:] if len(val) > 8 else "****"
print(f"{PASS}  {var} = {masked}")
```

---

### Fix 2: Reputation never updated on block/intervention
**File:** `agentguard/middleware.py:111-128`

Add `self.reputation.update_score(agent_id, "block")` before line 112 (the block raise), and `self.reputation.update_score(agent_id, tier)` before line 118 (the intervention raise). Currently reputation only updates on approved actions (line 128).

---

### Fix 3: Operator precedence bug
**File:** `agentguard/middleware.py:111`

**Current:**
```python
if tier == "block" or trust_level == "untrusted" and recent_block_rate >= 0.6:
```
**Replace with:**
```python
if tier == "block" or (trust_level == "untrusted" and recent_block_rate >= 0.6):
```

---

### Fix 4: Rich metadata discarded in example scripts
**Files:** `examples/simple_usage.py:52-53`, `examples/attack_demo.py:24`

Replace the stub metadata `{"entity_count": ..., "detection_method": "unknown"}` with the actual metadata from the privacy layer's `detect_and_anonymize()` return value. The privacy layer returns `contains_financial_amount`, `person_count`, `financial_magnitude`, etc. which the risk scorer needs for accurate tier assignment.

---

### Fix 5: Dead SQL query + f-string injection in Cosmos
**File:** `azure_services.py:202-208`

**Current:** Parameterized query defined but unused; actual query uses f-string.
**Replace with:**
```python
query = "SELECT TOP @limit * FROM c ORDER BY c._ts DESC"
parameters = [{"name": "@limit", "value": int(limit)}]
items = list(
    self.container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True,
    )
)
```

---

### Fix 6: Version mismatch
- `setup.py:17` — change `"4.2.5"` to `"4.2.8"`
- `examples/simple_usage.py:19` — change `"v4.2.7"` to `"v4.2.8"`
- `app.py:454` already says `4.2.8`

---

## MEDIUM PRIORITY

### Fix 7: Space collapsing doesn't defeat spaced-out attacks
**File:** `risk_scorer.py:73`

Comment says it catches `"i g n o r e  a l l"` but `re.sub(r"\s+", " ", ...)` only collapses multi-spaces to single spaces, not removes them.

**Fix:** In `_run_prefilter`, also test patterns against `normalized.replace(" ", "")`:
```python
def _run_prefilter(text):
    normalized = _normalize_text(text)
    no_spaces = normalized.replace(" ", "")
    matched = []
    for name, pattern in _PREFILTER_PATTERNS:
        if pattern.search(normalized) or pattern.search(no_spaces):
            matched.append(name)
    return (len(matched) > 0, matched)
```

---

### Fix 8: Canary token only checked in app.py, not middleware
**File:** `live_agent.py:58-61`, `app.py:1237`

The `CANARY_TRIGGERED` string is checked in `app.py` but not in `middleware.py`. Terminal users don't get canary protection. Either add the check to middleware or document as UI-only. Not demo-critical.

---

### Fix 9: Singleton uses NameError anti-pattern
**File:** `live_agent.py:152-159`

**Replace with:**
```python
_live_agent_instance: LiveAgent | None = None

def get_live_agent() -> LiveAgent:
    global _live_agent_instance
    if _live_agent_instance is None:
        _live_agent_instance = LiveAgent()
    return _live_agent_instance
```

---

### Fix 10: PII overlap detection misses containment case
**File:** `privacy_layer.py:98`

**Current:**
```python
if any(s <= start < e or s < end <= e for s, e in used_spans):
```
**Replace with:**
```python
if any(start < e and s < end for s, e in used_spans):
```

---

## LOW PRIORITY

### Fix 11: Heuristic factor values exceed 0-25 range
**File:** `risk_scorer.py:256` — add before this line:
```python
for key in factors:
    factors[key] = min(25, max(0, factors[key]))
```

### Fix 12: Local fallback writes Python repr, not JSON
**File:** `agentguard/middleware.py:159`
**Replace:** `handle.write(f"{record}\n")` with `handle.write(json.dumps(record, default=str) + "\n")` (add `import json` at top)

### Fix 13: ACCOUNT regex too broad
**File:** `privacy_layer.py:70` — `\b\d{8,17}\b` matches any 8-17 digit number. Consider requiring a context keyword like `account` or a prefix like `ACC-`.

---

## Execution Order (fastest first)
1. Fix 3 — parentheses (10 sec)
2. Fix 1 — key masking (30 sec)
3. Fix 6 — version unify (30 sec)
4. Fix 10 — overlap fix (30 sec)
5. Fix 9 — singleton (1 min)
6. Fix 5 — parameterized SQL (1 min)
7. Fix 11 — factor clamp (1 min)
8. Fix 12 — JSON fallback (1 min)
9. Fix 2 — reputation on block (2 min)
10. Fix 7 — space collapsing (3 min)
11. Fix 4 — metadata in examples (3 min)
12. Fix 13 — ACCOUNT regex (2 min)
13. Fix 8 — canary documentation (2 min)

**Total: ~18 minutes**
