# AgentGuard Presentation Transfer Context

## What This Is

This file is the full handoff context for continuing the AgentGuard presentation rebuild on another machine.

The presentation work in this session lives in:

- `artifacts/agentguard_presentation_v2/build_agentguard_v2.js`
- `artifacts/agentguard_presentation_v2/dist/AgentGuard_Presentation_v2.pptx`
- `artifacts/agentguard_presentation_v2/pptxgenjs_helpers/*`
- `artifacts/agentguard_presentation_v2/package.json`
- `artifacts/agentguard_presentation_v2/package-lock.json`

## Repo / Branch / Commit

- Repo: `agentGuard-msft`
- Branch used in this session: `main`
- Presentation commit pushed during this session: `37b12fe`
- Commit message: `Add AgentGuard presentation deck source and build artifacts`

## High-Level Goal

Rebuild the AgentGuard Microsoft AI Unlocked presentation from scratch in editable PptxGenJS, with a hard emphasis on:

- zero dead whitespace
- fixed-height placeholders
- dense, investor/corporate-readable layouts
- strong visual hierarchy
- a Microsoft AI Unlocked visual style
- all 9 slides in one `.pptx`

## Build / Run Instructions

From repo root:

```powershell
cd artifacts\agentguard_presentation_v2
npm install
npm run build
```

This writes:

- `artifacts/agentguard_presentation_v2/dist/AgentGuard_Presentation_v2.pptx`

## Optional Render Validation on Windows

In this session, PowerPoint COM export was used to render slides to PNG because LibreOffice was not installed.

Example PowerShell export:

```powershell
$pptPath = 'C:\path\to\AgentGuard_Presentation_v2.pptx'
$outDir = 'C:\path\to\rendered'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$pp = New-Object -ComObject PowerPoint.Application
$pp.Visible = -1
$pres = $pp.Presentations.Open($pptPath, $true, $false, $false)
$pres.Export($outDir, 'PNG', 1280, 720)
$pres.Close()
$pp.Quit()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($pres) | Out-Null
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($pp) | Out-Null
```

## Important Validation Notes From This Session

- JS deck generation works.
- The deck builds with `npm run build`.
- PowerPoint export to PNG at `1280x720` worked.
- LibreOffice-based validation was not available in this environment because `soffice` was missing.
- `pdf2image` was installed locally during the session, but PowerPoint export was the actual render validation path used.

## What Was Fixed During This Session

### Slide 2

Fixed multiple issues:

- bottom warning callout bleeding into the text above it
- stat/evidence row crowding into `WHY EXISTING SOLUTIONS FAIL`
- real-world context row was too small and visually weak

Current Slide 2 design changes:

- more breathing room in the evidence row
- cleaner amber callout panel
- quote-style real-world context cards with visible sources

### Slide 3

The original footer field list looked too technical for a corporate/non-technical audience.

It was redesigned into:

- a headline that says every event is logged as a complete audit record
- an explicit `18 FIELDS LOGGED ON EVERY EVENT` badge
- grouped audit/evidence categories:
  - Record Identity
  - Request Context
  - Safety Signals
  - Decision Logic
  - Outcome & Evidence

### Slide 5

Originally this slide was basically just raw text blocks.

It was redesigned into styled feature cards with:

- colored side rails
- numbered headers
- summary bands
- chips
- structured evidence rows
- visual callouts
- a split legal/healthcare domain panel

Then a follow-up bug fix was made to stop callout boxes from bleeding into the rows above in:

- `MULTI-TURN ATTACK DETECTION`
- `AGENT REPUTATION SCORE`

## Remaining Work / What To Check Next

If continuing this project, the next sensible steps are:

1. Review Slides 6, 7, 8, and 9 visually at presentation size.
2. Confirm there are no remaining whitespace, density, or hierarchy issues.
3. If needed, continue tightening typography and visual polish for corporate readability.
4. If desired, replace placeholder boxes with real screenshots/diagrams.

## Important Files To Edit

- Main authoring file:
  - `artifacts/agentguard_presentation_v2/build_agentguard_v2.js`

- Output deck:
  - `artifacts/agentguard_presentation_v2/dist/AgentGuard_Presentation_v2.pptx`

- Helper bundle used by the slides skill:
  - `artifacts/agentguard_presentation_v2/pptxgenjs_helpers/*`

## Local-Only / Not Pushed

These existed locally during the session but were intentionally not committed:

- `artifacts/agentguard_presentation_v2/node_modules/`
- `artifacts/agentguard_presentation_v2/rendered/`
- temporary PowerPoint lock files
- temporary duplicate helper copy
- temporary PDF export artifact

So on another machine, regenerate locally rather than expecting those to exist.

## Full Main Prompt Used For The Rebuild

Below is the exact main prompt that drove the rebuild work in this session.

---

Now I can see exactly what is wrong. Three specific problems causing the whitespace:

**Slide 2 (Problem):** The comparison table ends halfway down the slide leaving 250px of pure white nothing below it. The table needs more rows or the bottom callout needs to be pulled up to fill the gap.

**Slide 3 (Solution):** The pipeline placeholder box is enormous but empty, and the four stat cards below it are huge with tiny text floating in massive white cards. The stat numbers are large but the cards themselves have too much internal padding.

**Slide 6 (Architecture):** Two placeholder boxes stacked take up 60% of the slide and then the tech stack section has three bullet points with 200px of white space below them.

The fundamental problem is that placeholder boxes are being treated as flex children that stretch to fill available space. When they have no content they just become white rectangles. The fix is to constrain placeholder heights strictly and fill the remaining space with real content.

Here is the complete new prompt:

---

**COMPLETE NEW PROMPT FOR CLAUDE — AgentGuard Presentation v2:**

---

Read the PPTX skill file before starting. You are rebuilding the AgentGuard presentation from scratch. The previous version had a critical density problem — placeholder boxes stretched to fill empty space, leaving large white voids on every slide. This version must have zero empty space on any slide. Every pixel of every slide must contain either text, a data point, a table row, a diagram placeholder with a fixed constrained height, or a colored background element.

**HARD RULES — THESE OVERRIDE EVERYTHING ELSE:**

Rule 1: The presentation is 1280x720px, 16:9. Every slide is exactly this size. No scrolling. No overflow. Everything fits within the slide boundary.

Rule 2: Placeholder boxes for diagrams and screenshots have a FIXED height of exactly 130px. No more. No less. They do not flex or stretch. They do not fill remaining space. After placing a placeholder, fill all remaining space below it with additional real content.

Rule 3: Every slide body must be filled to within 5px of the footer. If you have placed all sections and there is remaining space, add another content row — a callout, a quote, additional data points, a secondary comparison, or a supporting evidence row — until the slide is full.

Rule 4: Stat cards contain the number, a label, a source citation, AND two lines of supporting context text. They are compact — maximum height 110px each. Four stat cards in a row must fill exactly the width of the slide.

Rule 5: No section may have internal padding greater than 6px vertical. No gap between sections greater than 4px.

Rule 6: Font sizes — body text 12px, section header labels 10px uppercase, stat numbers 28px, table cells 11px, captions 10px. These are fixed values not clamp ranges.

Rule 7: The slide header is 44px tall. The footer is 24px tall. The remaining 652px is the body. Divide it precisely among sections so the total equals 652px.

---

**VISUAL THEME:**

Exact Microsoft AI Unlocked style. Dark header bar (#0c1424) with white bold title centered, Microsoft logo left, AI Unlocked badge right. White body (#ffffff). Dark section header bars (#0f1923) with white uppercase text and a 3px left border in the section accent color. Dark footer bar (#0c1424). No gradients in body sections. No background colors on content areas except the section bars themselves.

---

**SLIDE 1 — Product Vision — 652px body**

Section 1 — Vision block — 120px tall — centered, dark background (#0d1f3c), cyan left border:
Label: "PRODUCT VISION" in small cyan uppercase
Vision statement in white bold 16px: "AgentGuard is the compliance layer that makes AI agent deployments auditable, accountable, and safe to run in production — without changing a single line of agent code."

Section 2 — Product identity — 80px tall — two columns:
Left: "AgentGuard · Round 2 Finalist · Top 54 of Microsoft AI Unlocked · Track 5: Trustworthy AI · Manipal Institute of Technology"
Right: Team — Sarangan Srinivasan · Krishna Gera · Saanvi Bansal · Teen Bhai Teeno Tabahi

Section 3 — The problem in one line — 60px tall — dark section bar "THE PROBLEM":
"87% of enterprises have AI agents deployed. 90% are over-permissioned. There is no enforcement layer between what those agents decide and what they execute."

Section 4 — Four product pillars — 160px tall — dark section bar "WHAT AGENTGUARD PROVIDES":
Four equal columns, each with a bold title and two lines of body text:
Column 1: "Privacy" — "PII anonymized before any agent sees it. Zero sensitive data reaches the model."
Column 2: "Security" — "Every action risk-scored 0–100 before execution. Four-factor contextual analysis."
Column 3: "Compliance" — "Immutable audit trail in Azure Cosmos DB. PDF compliance report on demand."
Column 4: "Control" — "YAML policy engine. Agent permissions enforced externally. Agent cannot bypass."

Section 5 — Real data proof row — 80px tall — dark section bar "LIVE DATA FROM REAL RUNS":
Four inline stats in a single row: 384 decisions · 159 blocked (41%) · 225 auto-executed · 425 PII entities masked
Subtext: "Not simulated. Real pipeline runs logged to Azure Cosmos DB."

Section 6 — Ambition statement — 60px tall — amber left border callout:
"Today: law firms and hospitals. Tomorrow: the standard for every regulated AI deployment. Every enterprise deploying AI agents is a potential customer — and 87% already have agents deployed."

Section 7 — Azure tech strip — 48px tall — dark background:
"Powered by: Azure OpenAI · Azure Cosmos DB · Azure AI Content Safety · Microsoft Presidio · FastAPI · Azure Container Apps"

Total: 120+80+60+160+80+60+48 = 608px. Remaining 44px distribute as padding between sections (4px each × 11 gaps = 44px). Exact fit.

---

**SLIDE 2 — The Problem — 652px body**

Section 1 — Who is facing this — 90px tall — dark section bar "WHO IS FACING THIS PROBLEM":
Two columns. Left: "CISOs, compliance officers, and IT directors at enterprises deploying AI agents in regulated environments — law firms, hospitals, financial institutions — responsible for ensuring regulatory compliance when agents operate autonomously." Right: Four industry chips in a row: Banking · Healthcare · Legal · Defence. Below chips: "Key stakeholders who face career-ending consequences when an AI agent exceeds its authority."

Section 2 — Evidence stats — 110px tall — dark section bar "WHY IT MATTERS — THE EVIDENCE":
Six stat cards in a row, each exactly 1/6 of slide width, height 90px:
Card 1: 87% · "Enterprises with AI agents deployed" · Obsidian Security 2025 · "Every single one is a potential AgentGuard customer"
Card 2: 90% · "Of those agents are over-permissioned" · Obsidian Security 2025 · "Nine in ten have more access than they need"
Card 3: 16x · "More data moved by agents than humans" · Obsidian Security 2025 · "Exponentially larger blast radius per incident"
Card 4: $7.42M · "Average healthcare breach cost" · IBM Cost of Data Breach 2025 · "Most expensive industry for 14 consecutive years"
Card 5: 97% · "AI breach victims lacked access controls" · IBM Research · "The gap AgentGuard fills directly"
Card 6: 41% · "Of our 384 real decisions needed intervention" · AgentGuard live data · "The threat is real, not theoretical"

Section 3 — Comparison table — 200px tall — dark section bar "WHY EXISTING SOLUTIONS FAIL":
Table with 7 columns: Solution · What It Does · What It Misses · Action Intercept · Audit Trail · Domain Modes · Verdict
Row 1: Microsoft Presidio · PII detection at message layer · No action interception · ✗ · ✗ · ✗ · Content layer only
Row 2: LlamaGuard · Prompt and response safety · No policy engine · ✗ · ✗ · ✗ · Probabilistic
Row 3: Lakera Guard · Injection detection · No domain modes · ✗ · ✗ · ✗ · Single-signal
Row 4: All existing tools · Best-effort checks · No compliance output · ✗ · ✗ · ✗ · Not prod-grade
Row 5 highlighted green: ✦ AgentGuard · Full pipeline interception + compliance · — · ✓ · ✓ · ✓ · Production-grade
Below table immediately: "No existing product combines action-level interception, domain-specific PII detection, agent reputation, multi-turn attack detection, and PDF compliance output."

Section 4 — Bottom callout — 52px tall — amber border dark background:
Bold: "One bad prompt can trigger a $2M wire transfer, delete audit logs, and leak patient data — simultaneously. Existing tools cannot stop this at the action layer."
Below: "AgentGuard is the only product that intercepts at the action layer, enforces domain-specific policies, and produces a compliance report that survives a regulatory audit."

Section 5 — Secondary evidence row — 60px tall — dark section bar "REAL-WORLD CONTEXT":
Three columns: "Troutman Pepper Locke already deployed an agentic workflow automating 80% of merger communications" · "LexisNexis CEO Jan 2026: 'Show me your guardrails will increasingly mean show me your workflow'" · "EU AI Act August 2026 + HIPAA AI amendments 2024 — compliance is no longer optional"

Total: 90+110+200+52+60 = 512px body content + 5 section bars at 22px each = 110px + gaps = 30px = 652px. Exact fit.

---

**SLIDE 3 — Our Solution — 652px body**

Section 1 — Core idea — 70px tall — dark section bar "THE CORE IDEA":
"AgentGuard sits between every AI agent and everything that agent is allowed to touch. It does not modify the agent. It does not change any agent code. It intercepts proposed actions, evaluates them against a configurable policy the agent cannot read or bypass, and either approves, escalates to a human, or blocks — in under two seconds."
Below: "Framework-agnostic · Three lines of code · AutoGen · Semantic Kernel · LangChain · OpenClaw · any framework · zero changes to the agent"

Section 2 — Pipeline diagram — dark section bar "THE PIPELINE" — placeholder box EXACTLY 130px tall:
Placeholder box 130px fixed height, full width, dashed border, label: "INSERT GEMINI DIAGRAM: AgentGuard Pipeline Flow — horizontal nodes left to right"
Below the placeholder immediately — no gap — a single row of nine labeled chips showing the pipeline nodes inline as text: User Request → Privacy Layer (Azure OpenAI + Presidio) → Agent Sandbox → Pre-Filter (Regex <1ms $0) → Risk Scorer (GPT-4o-mini 0–100) → Policy Engine (YAML) → Intervention Tier → Cosmos DB → Dashboard

Section 3 — Four stat cards — dark section bar "REAL RESULTS FROM LIVE TEST RUNS" — 140px tall:
Four equal cards in a row, each 140px tall:
Card 1: 384 large blue · "Total decisions processed" · "Real pipeline runs, logged to Azure Cosmos DB" · "Across all three deployment profiles" · "finance · legal · healthcare"
Card 2: 159 large red · "Blocked or escalated — 41%" · "41% of all requests required intervention" · "The threat is real, not theoretical" · "Cross-matter, PHI, injection, bulk export"
Card 3: 225 large green · "Auto-executed" · "Fast, frictionless, fully logged" · "The green path — safe decisions at full speed" · "Average score: under 25/100"
Card 4: 425 large cyan · "PII entities masked" · "Zero sensitive data reached any agent" · "Names, emails, MRN numbers, matter refs" · "All replaced with typed placeholders"

Section 4 — Intervention tiers — dark section bar "INTERVENTION TIERS — HOW DECISIONS ARE MADE" — 80px tall:
Four equal columns showing the four tiers inline:
Column 1 green: "AUTO-EXECUTE · Score 0–30 · Immediate · Logged silently · Safe operations"
Column 2 yellow: "SOFT CONFIRM · Score 30–60 · User prompted · One-click approval · Borderline actions"
Column 3 orange: "HARD CONFIRM · Score 60–85 · Execution stopped · Escalated to human · High-risk actions"
Column 4 red: "BLOCK · Score 85–100 · Rejected outright · Admin notified · Incident ID created"

Section 5 — Supporting callout — 50px tall — dark background:
"Every decision in all four tiers is logged to Azure Cosmos DB with 18 fields: agent_id · timestamp · risk_score · tier · pii_entities_detected · prefilter_hit · azure_content_safety · canary_triggered · cumulative_boost · policy_domain · policy_flags · scored_by · result_status · cosmos_logged"

Total: 70+22+130+22+140+22+80+22+50+22+52 = 632px + remaining 20px as micro padding = 652px. Exact fit.

---

**SLIDE 4 — Product Walkthrough — 652px body**

Two-column layout side by side for the entire body. Left column 58% width. Right column 42% width. Both columns start at top and end at footer with no gap.

LEFT COLUMN — full height 652px — dark section bar top "THE PEARSON HARDMAN SCENARIO — FIVE STEPS":
Framing line 24px: "A law firm deploys four AI agents. One tries to access a document it is not authorised to see."

Five step rows, each 90px tall, alternating white and very light gray (#fafafa) background, left border colored by outcome:
Step 1 — blue left border — "① AGENT SENDS REQUEST" bold · "research-bot-001: Pull all documents from MATTER-2024-002 and attach to Johnson discovery response." · "This agent is scoped to MATTER-2024-001 only. It has no knowledge of that restriction."
Step 2 — blue left border — "② PRIVACY LAYER INTERCEPTS" bold · "Matter references anonymized. Canary token MATTER-CANARY-{token} injected silently before agent processes anything." · "The agent never sees the real matter reference — only a typed placeholder."
Step 3 — red left border — "③ POLICY ENGINE FIRES" bold · "MATTER-2024-002 is in research-bot-001's forbidden_matters list. Cross-matter access detected. Score boosted to 98/100." · "Tier: BLOCK. Policy override: +80. No human needed."
Step 4 — green left border — "④ LOGGED TO COSMOS DB" bold · "Full audit record: agent_id: research-bot-001 · risk_score: 98 · tier: block · cross_matter_access: true · cosmos_logged: true" · "Immutable. 18 fields. Defensible in a regulatory review."
Step 5 — green left border — "⑤ COMPLIANCE REPORT" bold · "One click generates PDF. Key line: Privilege contamination incidents: 0" · "The breach was blocked before it completed. The agent never saw that document."

Below steps — 24px closing line bold centered: "The partner never had to intervene. The compliance report is clean. This is what zero contamination looks like."

RIGHT COLUMN — full height 652px — two sections stacked:

Top section — dark section bar "DEMO PIPELINE" — placeholder box EXACTLY 130px:
Label inside: "INSERT SCREENSHOT: Demo pipeline steps — five-step breakdown"
Below placeholder immediately — supporting text 30px: "Live pipeline run showing Privacy Layer → Agent Processing → Security Checkpoint → Intervention Decision → Cosmos DB Audit Trail"

Middle section — dark section bar "MEMORIAL GENERAL — DOMAIN SWITCH" — 120px:
"Same product. Different YAML config. Different domain."
Three rows:
"Switch to Memorial General Hospital — one dropdown — no server restart — no code changes"
"pharmacy-agent attempts: Retrieve psychiatric medication history for MRN-002391 for cardiology review"
"Result: BLOCK · special_category_phi: true · PHI breaches: 0 · HIPAA minimum necessary enforced"
One line bold: "The architecture is universal. The policy is configurable."

Bottom section — dark section bar "AUDIT LOG EVIDENCE" — placeholder box EXACTLY 130px:
Label inside: "INSERT SCREENSHOT: Audit log table — mix of AUTO green and BLOCK red decisions"
Below placeholder — 30px: "Every decision from both scenarios logged to Azure Cosmos DB in real time. Source of truth for all compliance reporting."

Bottom strip — 40px — dark background spanning full right column:
"AgentGuard processed 384 real decisions across finance · legal · healthcare domains. 41% required intervention."

---

**SLIDE 5 — Key Features — 652px body**

Section bar top — "FIVE CAPABILITIES NO COMPETITOR COMBINES" — 22px

Five feature blocks arranged as: top row three blocks, bottom row two blocks centered. Each block has a dark header bar with the feature name and a white body.

Top row — three equal blocks — each 240px tall:

Block 1 — header "POLICY-AS-YAML ENGINE":
"Each agent's permissions are defined in a YAML config file it cannot read or bypass. AgentGuard enforces it externally at the network layer — not inside the agent."
Three deployment profile chips: TechCorp Finance · Pearson Hardman Legal · Memorial General HIPAA
"Switch domains with one dropdown. No code changes. No server restart. New domain = one new YAML file."
Supporting evidence: "Three validated configs ship with the product. Operator testing required before production."
Quote: "This is the line that impresses enterprise buyers: 'Your agent cannot override its own policy.'"

Block 2 — header "CANARY TOKEN INJECTION":
"Before every request, AgentGuard plants a unique sentinel token in the context. Domain formats: Finance: canary-{token}@agentguard-sentinel.io · Legal: MATTER-CANARY-{token} · Healthcare: MRN-CANARY-{token}"
"If the agent echoes the token back in its response, AgentGuard catches it, blocks the response, and logs canary_triggered: true."
"This catches the entire category of data exfiltration that uses legitimate-sounding language with no suspicious keywords."
Bold: "No keyword filter catches this. No content safety model flags this. No competitor detects this attack category."

Block 3 — header "MULTI-TURN ATTACK DETECTION":
"AgentGuard tracks the last 5 risk scores per agent independently. A query → identify → exfiltrate pattern across three innocent-looking messages triggers a cumulative boost of up to +40 points."
"Agent-specific window. One agent's suspicious pattern cannot poison another agent's score."
"Every single-message scanner misses reconnaissance sequences. AgentGuard catches them."
Two example rows: "Message 1: score 15 — safe query" · "Message 3: score 58 + boost 40 = 98 — BLOCK"
Bold: "The attack that every competitor misses. We catch it."

Bottom row — two equal blocks — each 230px tall — centered with 10px gap:

Block 4 — header "AGENT REPUTATION SCORE":
"Every agent builds a trust score 0–100 persisted to Azure Cosmos DB across sessions."
"HIGH trust (70+): more autonomy, faster approvals · MEDIUM (30–69): standard controls · LOW (<30): mandatory review, tighter thresholds"
"An agent that triggered escalations last week starts this session with a degraded score — not a fresh 50."
"Score history: last 10 changes with timestamp, previous score, new score, and reason stored per agent."
Bold: "No competitor has persistent cross-session reputation. The guardrails adapt over time — not just within a session."

Block 5 — header "DOMAIN-SPECIFIC PROTECTION":
Two sub-columns:
Left — "LEGAL MODE": "Detects: matter numbers (MATTER-XXXX-XXX) · privilege markers (ATTORNEY-CLIENT, WORK PRODUCT) · Bates numbers · bar IDs · opposing counsel patterns · cross-matter access attempts"
"Enforces: matter-based agent scoping · privilege contamination prevention · external send restrictions per agent"
Right — "HEALTHCARE MODE": "Detects: MRN · ICD-10 diagnosis codes · CPT procedure codes · NPI numbers · DEA numbers · insurance member IDs · psychiatric and HIV record flags"
"Enforces: HIPAA minimum necessary standard · special category PHI protection · agent scope violations"
Bottom spanning both: "Same detection architecture. Different entity patterns. Configured entirely through the YAML file."

---

**SLIDE 6 — Architecture and Tech Stack — 652px body**

Section 1 — dark section bar "SYSTEM ARCHITECTURE" — placeholder EXACTLY 130px:
Label: "INSERT GEMINI DIAGRAM: Full system architecture — Pearson Hardman agents left · AgentGuard pipeline center · Memorial General agents right · Cosmos DB and Dashboard bottom"
Below placeholder immediately — 50px supporting content row with 8 labeled component chips in a single line:
Privacy Layer · Pre-Filter · Risk Scorer · Policy Engine · Intervention Tier · Cosmos DB · Dashboard · FastAPI Server
Each chip has a small colored dot matching the Gemini diagram color coding: blue · orange · purple · yellow · yellow · green · blue · gray

Section 2 — dark section bar "DATA FLOW" — placeholder EXACTLY 80px:
Label: "INSERT GEMINI DIAGRAM: Compact horizontal data flow strip — User → Privacy → Pre-Filter → Risk Scorer → Policy → Intervention → Cosmos DB → Dashboard"
Below placeholder immediately — 30px: "Every request travels all layers in sequence. Nothing bypasses. Pre-filter catches obvious threats in <1ms. LLM scorer handles ambiguous cases in 1–2.5 seconds."

Section 3 — dark section bar "TECHNOLOGY STACK" — 200px:
Two columns equal width. Each column has two sub-sections.

Left column:
Sub-header "AI AND INTELLIGENCE" bold:
Row 1: "Azure OpenAI GPT-4o-mini" bold blue · "PII entity detection with domain-specific prompt addons. Four-factor risk scoring with written reasoning. Every decision explainable."
Row 2: "Microsoft Presidio" bold blue · "Local entity detection. Zero API cost. Zero latency. Zero data leaves the machine for PII detection. Runs before any Azure call."
Row 3: "Azure AI Content Safety" bold blue · "Parallel jailbreak and injection detection on every request. Independent second signal. When both pre-filter and Content Safety flag — two systems logged separately."

Right column:
Sub-header "INFRASTRUCTURE AND DATA" bold:
Row 1: "Azure Cosmos DB" bold blue · "Immutable audit log. 18 fields per record. Reputation persistence across sessions. Compliance report source of truth."
Row 2: "FastAPI" bold blue · "Production REST API. POST /intercept · POST /confirm · GET /status/{id}. HTML dashboard served as static files same port."
Row 3: "Azure Container Apps" bold blue · "Production deployment target. Auto-scaling. Enterprise-grade. HTML/CSS/JS dashboard — 7 pages, real-time polling, 9 navigation sections."

Below both columns — 30px — italic centered: "Every Azure service chosen because it is the right tool for that specific layer — not for the sake of using Azure."

Section 4 — dark section bar "ENGINEERING DECISIONS" — 60px:
Three columns: "Modular architecture — policy engine, privacy layer, risk scorer, pre-filter all independently swappable" · "Domain agnosticism — same core serves finance, legal, healthcare through YAML configuration only" · "Zero agent modification — three lines of code wraps any existing agent framework"

---

**SLIDE 7 — AI Integration and Enhancements — 652px body**

Section 1 — dark section bar "WHERE AND WHY AI IS USED — SMART USAGE NOT HEAVY USAGE" — 180px:
Four rows, each 40px:
Row 1: "Azure OpenAI · PII Detection" bold blue · "Contextual entity detection in legal and healthcare language requires language understanding regex cannot provide. ICD-10 code in a clinical sentence vs. a billing record need different treatment — only an LLM understands that distinction."
Row 2: "Azure OpenAI · Risk Scoring" bold blue · "Four-factor analysis — sensitivity, reversibility, blast radius, policy compliance — requires reasoning about context. A $50,000 transfer from billing-agent is different from the same transfer from scheduling-agent. Returns 0–100 score with written reasoning. Every decision explainable."
Row 3: "Azure AI Content Safety · Parallel Validation" bold blue · "Runs on every request in parallel with the pre-filter. When both trigger, both signals are logged independently. Two systems agreeing is stronger evidence than one — shown in the audit record."
Row 4: "Azure OpenAI · Agent Persona Simulation" bold blue · "Each simulated agent generates realistic varied requests using a persona prompt. Routine traffic is genuinely varied — not scripted. Proves the system handles novel unpredictable inputs."

Below the four rows — 30px highlighted box: "What we chose NOT to use AI for: pre-filter matching · policy engine enforcement · canary detection · multi-turn window · reputation scoring. Deterministic code where deterministic code is correct. AI only where reasoning is genuinely required."

Section 2 — dark section bar "MENTOR FEEDBACK INCORPORATED — WHAT CHANGED BETWEEN ROUNDS" — 180px:
Two columns equal width with a vertical divider:

Left column — "ROUND 1 — WHAT MENTOR FEEDBACK WE RECEIVED":
Feedback received in bold amber: "Presentation hard to read · not information dense · demo was a human typing into a box"
Three before items each with a red ✗:
✗ "Generic demo — prompt input and output with no narrative or story"
✗ "Streamlit dashboard looked like a student project — not a product"
✗ "No domain-specific protection — general purpose only"
✗ "Mock keyword-matching agent — not a real AI making real decisions"
✗ "No compliance output — nothing a CISO could actually use"

Right column — "ROUND 2 — WHAT WE BUILT IN RESPONSE":
Five after items each with a green ✓:
✓ "Pearson Hardman scenario — four named agents, legal context, cross-matter breach caught in real time — story makes features memorable and judging rubric criteria directly addressed"
✓ "FastAPI server with HTML dashboard and live agent simulation — four agents operate autonomously — dashboard lights up without anyone typing"
✓ "Legal privilege mode · HIPAA mode · YAML policy engine · canary tokens · multi-turn detection · persistent reputation — none existed in Round 1"
✓ "Live AI agent — GPT-4o-mini making real decisions — not keyword matching"
✓ "PDF compliance report — privilege contamination: 0 · PHI breaches: 0 — output a CISO can submit to a regulator"

Below both columns — 24px bold centered: "This is not an iteration. This is a rebuild informed by real feedback, real testing, and 384 real decisions processed."

Section 3 — dark section bar "LIVE SIMULATION EVIDENCE" — 130px:
Two equal placeholder boxes side by side each EXACTLY 108px tall:
Left placeholder: "INSERT SCREENSHOT: Agent simulation — four agents at corners, middleware center, animated lines, live feed panel"
Right placeholder: "INSERT SCREENSHOT: Audit log table — AUTO green and BLOCK red decisions from real simulation run"
Below both — 22px: "Left: Four autonomous agents operating simultaneously at Pearson Hardman — routine green traffic interrupted by scripted red BLOCK events · Right: Real Cosmos DB audit records from the simulation"

---

**SLIDE 8 — Scalability and Future Scope — 652px body**

Section 1 — dark section bar "MARKET OPPORTUNITY" — 130px:
Four stat cards in a row each exactly 108px tall:
Card 1 blue: $93.75B · "AI Cybersecurity by 2030 · 24.4% CAGR" · Grand View Research 2024 · "Fastest growing security category globally"
Card 2 cyan: $10.82B · "Legal AI Software by 2030 · 28.3% CAGR" · MarketsandMarkets 2025 · "Harvey AI: $190M ARR — the market is real"
Card 3 green: $56.3B · "Healthcare Cybersecurity by 2030 · 18.5% CAGR" · Grand View Research 2023 · "Most expensive breach industry 14 years running"
Card 4 red: $7.42M · "Average healthcare breach cost" · IBM 2025 · "AgentGuard prevents this at $0.003 per decision"
Below cards — 20px bold: "Combined addressable market across all three verticals exceeds $160B by 2030. AgentGuard addresses all three with one product."

Section 2 — dark section bar "GO-TO-MARKET STRATEGY" — 100px:
Three-phase timeline shown as three equal columns with phase numbers:
Phase 1 — NOW — "Open SDK · developer adoption · three deployment configs ship with product · target IT directors at law firms and hospitals deploying AI agents · GitHub repository + pip install agentguard"
Phase 2 — Q3 2026 — "Azure Marketplace listing · AutoGen + Semantic Kernel native integrations · fine-tuned local model for air-gapped hospital deployments where patient data cannot leave the network"
Phase 3 — 2027 — "Enterprise custom deployments · custom risk models trained on client data · multi-tenant SaaS · white-glove professional services · Azure partner program"

Section 3 — two-column layout — 200px — dark section bars:
Left column — "CURRENT CHALLENGES — HONEST LIMITATIONS":
Three challenge rows each with challenge in bold and mitigation in regular:
"Policy Quality — guardrail effectiveness depends on YAML correctness" · Mitigation: "Three validated configs ship with the product"
"Scale Testing — tested at 384 decisions · production load testing not yet complete" · Mitigation: "Cosmos DB + Container Apps designed for enterprise scale"
"Human Escalation Routing — Slack and email alerts not yet wired" · Mitigation: "Cosmos DB record is source of truth regardless · Phase 2"

Right column — "SCALABILITY PROOF":
Three evidence rows:
"$0.003 per decision with caching · 10,000 decisions per day = $30 · scales linearly · pre-filter at $0 for obvious threats"
"Pre-filter handles dangerous patterns in under 1ms at zero API cost · scales horizontally with no bottleneck"
"Same codebase serves finance + legal + healthcare · new domain = one new YAML file · zero code changes required"
Below three rows — supporting line: "Architecture uses Azure services designed for millions of records and concurrent requests."

Section 4 — dark section bar "COMPETITIVE MOAT" — 80px:
Four columns:
"Agent Reputation Score · Persistent cross-session trust · No competitor has this"
"Multi-Turn Detection · Reconnaissance pattern catching · No competitor has this"
"Canary Tokens · Exfiltration fingerprinting · No competitor has this"
"Domain YAML Engine · Infinite configurability · No competitor has this"
Below: "These four capabilities require 6+ months to replicate. Each one addresses a real attack category that existing products miss entirely."

Section 5 — dark section bar "REGULATORY TAILWINDS" — 60px:
Three columns: "EU AI Act — August 2026 enforcement — requires traceable AI decisions · AgentGuard provides this today" · "HIPAA Security Rule 2024 amendments — explicitly addresses AI systems handling ePHI · AgentGuard enforces this" · "Colorado AI Act — June 2026 — risk management and transparency for high-risk AI · AgentGuard compliance report covers this"

---

**SLIDE 9 — Closing Vision — 652px body — dark background (#0a0e1a)**

Section 1 — 100px — centered — dark navy box with cyan border:
Label small cyan uppercase: "THE VISION"
Vision statement white bold 18px centered: "AgentGuard is the compliance layer that makes AI agent deployments auditable, accountable, and safe to run in production — without changing a single line of agent code."

Section 2 — 140px — three equal columns on dark background:
Column 1 white header: "WHAT EXISTS TODAY"
"Production FastAPI server · real REST endpoints · POST /intercept + POST /confirm + GET /status"
"384 decisions processed · 159 blocked · 225 auto-executed · 425 PII entities masked"
"Legal + healthcare domain modes · 7 agents · 4 scripted simulation events · PDF compliance reports"
"Three deployment configs · YAML policy engine · agent reputation persistence"

Column 2 white header: "WHAT WE ARE BUILDING"
"Azure Marketplace listing · AutoGen native integration · Semantic Kernel integration"
"Fine-tuned local model · air-gapped hospital deployments · patient data never leaves network"
"Enterprise custom risk models trained on client data · multi-tenant SaaS"
"Real-time alert routing · Slack + email escalation notifications · Phase 2"

Column 3 white header: "WHY IT MATTERS NOW"
"87% of enterprises already have agents — every one is a potential customer"
"EU AI Act August 2026 · HIPAA AI amendments · Colorado AI Act June 2026"
"Show me your guardrails is now a procurement question not a nice-to-have"
"The compliance layer for AI agents does not exist at scale — AgentGuard is building it"

Section 3 — placeholder EXACTLY 130px — dark border dashed:
Label white centered: "INSERT SCREENSHOT: Raw Cosmos DB JSON record — BLOCK decision · agent_id: research-bot-001 · risk_score: 98 · tier: block · cross_matter_access: true · canary_triggered: false · cosmos_logged: true"
Below placeholder — 24px white italic centered: "This is a real audit record from a real pipeline run. This is what accountability looks like."

Section 4 — 80px — dark background — three columns:
Column 1: "384 real decisions · Azure Cosmos DB · not simulated"
Column 2: Prominent vision line repeated smaller: "Auditable. Accountable. Safe. Without changing a single line of agent code."
Column 3: "Sarangan Srinivasan · Krishna Gera · Saanvi Bansal · Teen Bhai Teeno Tabahi · Manipal Institute of Technology"

Section 5 — 60px — dark footer strip:
Three Azure service rows: "Azure OpenAI · Azure Cosmos DB · Azure AI Content Safety · Microsoft Presidio · FastAPI · Azure Container Apps"
Center: "Microsoft AI Unlocked · Track 5: Trustworthy AI · Top 54 Finalist"
Right: Azure logo + "Powered by Microsoft Azure"

---

**FINAL ASSEMBLY INSTRUCTIONS:**

After generating all nine slides verify the following on every slide:
1. Open the slide at 1280x720 in a browser. Scroll to the bottom. There must be zero white space between the last content element and the footer bar.
2. Every placeholder box is EXACTLY the height specified — 130px for large placeholders, 80px for compact ones. They have a dashed border, a light gray background (#f1f5f9), and the label text centered inside in 11px gray.
3. All six stat numbers across slides 1, 2, 3, and 8 are 28px bold — not larger, not smaller.
4. The comparison table on Slide 2 has exactly 5 data rows plus a header row. The AgentGuard row has a green left border and light green background.
5. No section has more than 6px vertical padding. No gap between sections greater than 4px.
6. Export as a single file. All nine slides in sequence.

---

## Session-Specific Follow-Up Changes After The Main Prompt

These were not in the original prompt, but were specifically requested and implemented during this session:

1. Slide 2:
   - fixed bottom callout bleed
   - fixed `WHY EXISTING SOLUTIONS FAIL` header crowding
   - turned `REAL-WORLD CONTEXT` into source-style quote cards

2. Slide 3:
   - replaced raw audit field dump with grouped executive/compliance summary
   - made the “18 fields” message clearer to non-technical viewers

3. Slide 5:
   - redesigned from text-heavy blocks into styled feature cards
   - fixed callout bleed in `MULTI-TURN ATTACK DETECTION`
   - fixed callout bleed in `AGENT REPUTATION SCORE`

## Practical Continuation Advice

If continuing on the lab computer:

- start with `build_agentguard_v2.js`
- run `npm install`
- run `npm run build`
- export slides via PowerPoint COM if you want PNG review
- visually inspect the latest slides before making more density changes

If you need to continue the exact spirit of this session, prioritize:

- corporate readability over technical completeness
- dense layouts over empty space
- structured evidence over raw field lists
- visual hierarchy over paragraph dumps
