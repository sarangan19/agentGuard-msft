# AgentGuard — Strategy Notes

Created: 2026-03-17

---

## The Problem with the Current Market Position
The current implementation is generic middleware for AI-to-AI security. This is redundant — every major tech company either has this already or will build it internally. Direct competitors include Lakera, Protect AI, and Cisco (Robust Intelligence), all well-funded. Microsoft is building this natively into Azure AI Foundry.

Staying generic means competing on features with companies that have enterprise sales teams, years of head start, and unlimited Azure credits. That is not a winnable fight.

---

## The Pivot: Regulated Industries

The opportunity is that the same core technology is dramatically MORE valuable in regulated industries:
- **The buyer has a mandated compliance budget** — they are not choosing whether to spend, only where
- **The pain is existential** — HIPAA violations average $1.9M per incident; privilege contamination can end legal careers
- **No well-funded competitor is specifically targeting AI-agent-specific compliance** in these sectors
- **Regulatory pressure is accelerating** — EU AI Act, updated HIPAA guidance on AI tools, ABA ethics opinions on AI in law

The pivot does not require rebuilding. The core technology (PII boundary enforcement, intervention tiers, audit trail, reputation tracking) is domain-agnostic. What changes:
1. Entity types detected (general PII → HIPAA PHI or legal privilege markers)
2. Output format (security dashboard → compliance report)
3. Distribution model (developers integrate it → IT installs it, executives see reports)
4. Language (security middleware → AI compliance infrastructure)

---

## Healthcare Use Case

**The actors:**
- IT team installs AgentGuard (one afternoon)
- Compliance officer monitors the dashboard
- Doctor / administrator never touches anything — just sees weekly email digests and audit reports

**The scenario:**
Hospital has two AI agents — a scheduling bot and a clinical documentation bot. Scheduling bot gets prompted to "also check what medications this patient is on." This is outside its authorized scope — a HIPAA minimum-necessary violation. AgentGuard blocks it before execution.

**The integration path:**
All hospital software must support FHIR (Fast Healthcare Interoperability Resources) API by law. AgentGuard wraps around FHIR calls — any AI agent requesting patient data goes through AgentGuard first. No custom code per hospital.

**The output the hospital buys:**
- Real-time compliance dashboard: "847 AI agent requests this month. 12 blocked. 0 PHI breaches."
- One-click HIPAA audit report PDF with every AI interaction timestamped and classified
- Evidence of due diligence when regulators come knocking

---

## Legal Use Case

**The actors:**
- IT team or managed service provider installs AgentGuard
- Compliance officer / general counsel monitors
- Lawyers never interact with the tool directly

**The scenario:**
Law firm has AI agents scoped to specific matters (cases). A research agent for Matter 002 (confidential M&A deal) receives a prompt that tries to pull documents from Matter 001 (personal injury case). This is a cross-matter privilege contamination attempt — potentially a bar ethics violation. AgentGuard blocks it and logs "privilege contamination attempt."

**The integration path:**
Legal document management systems (iManage, Clio, NetDocuments) all have APIs. AgentGuard sits between AI tools and these APIs. Matter-based scoping is configured in the policy YAML.

**The output the law firm buys:**
- Weekly report: "2 cross-matter access attempts intercepted. Attorney-client privilege intact."
- Annual compliance report for bar association ethics review
- Evidence of due diligence for malpractice defense

---

## The Fine-Tuned Local Model — Why It Matters for This Pivot

Healthcare clients and law firms **cannot send data to external APIs**. Full stop.
- A scheduling bot query might contain patient name + date of birth — that's PHI
- A legal research query might contain matter number + client name — that's privileged

Azure OpenAI can be configured for data residency, but lawyers and compliance officers don't know that. The fear is real and the procurement block is real.

The air-gapped local model eliminates this objection entirely:
> "AgentGuard runs entirely on your network. No data leaves. Not to Microsoft. Not to us. The model is yours."

This is a sales unlock, not just a technical feature.

---

## Competitive Positioning

| Competitor | What they do | Why AgentGuard wins in regulated industries |
|------------|-------------|---------------------------------------------|
| Lakera | LLM firewall for prompts | Generic, no domain-specific compliance modes, no air-gap story |
| Protect AI | ML security scanning | Focused on model security, not agent-to-agent communication |
| Cisco/Robust Intelligence | Enterprise AI security | Enterprise sales motion, slow procurement, not regulated-industry-specific |
| Microsoft (built-in) | Azure AI Foundry guardrails | Single-vendor lock-in, no cross-matter or PHI-specific modes, no air-gap |

AgentGuard's moat: **domain-specific compliance modes + air-gapped local model + audit reports that compliance officers actually need**.

---

## What NOT to Do

- Do not try to compete on generic "AI safety" — that market is crowded and going to get more crowded
- Do not build a consumer product — regulated industries have budget and urgency, consumers do not
- Do not position Change 8 (local model) as a technical curiosity — it is the key that unlocks the regulated industry market
