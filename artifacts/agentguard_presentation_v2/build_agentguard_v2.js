const path = require("path");
const fs = require("fs");
const PptxGenJS = require("pptxgenjs");
const {
  warnIfSlideHasOverlaps,
  warnIfSlideElementsOutOfBounds,
} = require("./pptxgenjs_helpers/layout");

const pptx = new PptxGenJS();

const PX_PER_IN = 96;
const px = (value) => value / PX_PER_IN;
const ptFromPx = (value) => value * 0.75;

const W = 1280;
const H = 720;
const HEADER_H = 44;
const FOOTER_H = 24;
const BODY_Y = HEADER_H;
const BODY_H = 652;
const FOOTER_Y = H - FOOTER_H;
const BAR_H = 22;

const C = {
  header: "0C1424",
  bar: "0F1923",
  white: "FFFFFF",
  bodyLine: "D7E0EA",
  light: "F8FAFC",
  lightBlue: "EFF6FF",
  lightAmber: "FFF7ED",
  lightGreen: "F0FDF4",
  lightGray: "F1F5F9",
  text: "102033",
  muted: "526172",
  gray: "64748B",
  cyan: "22D3EE",
  blue: "2563EB",
  green: "16A34A",
  red: "DC2626",
  amber: "D97706",
  yellow: "FACC15",
  orange: "EA580C",
  purple: "7C3AED",
  dark: "0A0E1A",
};

const FONT = {
  display: "Aptos Display",
  body: "Aptos",
  mono: "Consolas",
};

pptx.defineLayout({ name: "AG_1280_720", width: px(W), height: px(H) });
pptx.layout = "AG_1280_720";
pptx.author = "OpenAI Codex";
pptx.company = "AgentGuard";
pptx.subject = "AgentGuard Microsoft AI Unlocked Presentation v2";
pptx.title = "AgentGuard Presentation v2";
pptx.lang = "en-US";
pptx.theme = {
  headFontFace: FONT.display,
  bodyFontFace: FONT.body,
  lang: "en-US",
};

function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) fs.mkdirSync(dirPath, { recursive: true });
}

function addRect(slide, x, y, w, h, opts = {}) {
  slide.addShape(pptx.ShapeType.rect, {
    x: px(x),
    y: px(y),
    w: px(w),
    h: px(h),
    fill: {
      color: opts.fill || C.white,
      transparency: opts.fillTransparency || 0,
    },
    line: {
      color: opts.line || opts.fill || C.white,
      transparency: opts.lineTransparency !== undefined ? opts.lineTransparency : 0,
      width: opts.lineWidth !== undefined ? opts.lineWidth : 1,
      dashType: opts.dashType,
    },
    radius: opts.radius || 0,
  });
}

function addText(slide, text, x, y, w, h, opts = {}) {
  slide.addText(text, {
    x: px(x),
    y: px(y),
    w: px(w),
    h: px(h),
    fontFace: opts.fontFace || FONT.body,
    fontSize: ptFromPx(opts.fontPx || 12),
    bold: opts.bold || false,
    italic: opts.italic || false,
    color: opts.color || C.text,
    margin: opts.margin !== undefined ? opts.margin : 0,
    align: opts.align || "left",
    valign: opts.valign || "top",
    breakLine: opts.breakLine || false,
    fit: opts.fit,
    paraSpaceAfterPt: 0,
    charSpace: opts.charSpace || 0,
    underline: opts.underline || false,
  });
}

function addRuns(slide, runs, x, y, w, h, opts = {}) {
  slide.addText(runs, {
    x: px(x),
    y: px(y),
    w: px(w),
    h: px(h),
    fontFace: opts.fontFace || FONT.body,
    fontSize: ptFromPx(opts.fontPx || 12),
    color: opts.color || C.text,
    margin: opts.margin !== undefined ? opts.margin : 0,
    align: opts.align || "left",
    valign: opts.valign || "top",
    paraSpaceAfterPt: 0,
  });
}

function addDivider(slide, y, color = C.bodyLine) {
  slide.addShape(pptx.ShapeType.line, {
    x: px(0),
    y: px(y),
    w: px(W),
    h: 0,
    line: {
      color,
      width: 1,
    },
  });
}

function addVerticalDivider(slide, x, y, h, color = C.bodyLine) {
  slide.addShape(pptx.ShapeType.line, {
    x: px(x),
    y: px(y),
    w: 0,
    h: px(h),
    line: {
      color,
      width: 1,
    },
  });
}

function addSectionBar(slide, y, label, accent = C.cyan) {
  addRect(slide, 0, y, W, BAR_H, {
    fill: C.bar,
    line: C.bar,
    lineWidth: 0,
  });
  addRect(slide, 0, y, 4, BAR_H, {
    fill: accent,
    line: accent,
    lineWidth: 0,
  });
  addText(slide, label.toUpperCase(), 16, y + 4, W - 32, BAR_H - 8, {
    fontFace: FONT.display,
    fontPx: 10,
    bold: true,
    color: C.white,
    charSpace: 1.2,
    valign: "mid",
  });
}

function addSectionBarBox(slide, x, y, w, label, accent = C.cyan) {
  addRect(slide, x, y, w, BAR_H, {
    fill: C.bar,
    line: C.bar,
    lineWidth: 0,
  });
  addRect(slide, x, y, 4, BAR_H, {
    fill: accent,
    line: accent,
    lineWidth: 0,
  });
  addText(slide, label.toUpperCase(), x + 16, y + 4, w - 32, BAR_H - 8, {
    fontFace: FONT.display,
    fontPx: 10,
    bold: true,
    color: C.white,
    charSpace: 1.2,
    valign: "mid",
  });
}

function addHeaderFooter(slide, title, slideNo, totalSlides, opts = {}) {
  const bodyFill = opts.bodyFill || C.white;
  addRect(slide, 0, 0, W, H, {
    fill: bodyFill,
    line: bodyFill,
    lineWidth: 0,
  });

  addRect(slide, 0, 0, W, HEADER_H, {
    fill: C.header,
    line: C.header,
    lineWidth: 0,
  });
  addRect(slide, 0, FOOTER_Y, W, FOOTER_H, {
    fill: C.header,
    line: C.header,
    lineWidth: 0,
  });

  const logoX = 16;
  const logoY = 10;
  const s = 9;
  addRect(slide, logoX, logoY, s, s, { fill: "F25022", line: "F25022" });
  addRect(slide, logoX + s + 2, logoY, s, s, { fill: "7FBA00", line: "7FBA00" });
  addRect(slide, logoX, logoY + s + 2, s, s, { fill: "00A4EF", line: "00A4EF" });
  addRect(slide, logoX + s + 2, logoY + s + 2, s, s, { fill: "FFB900", line: "FFB900" });
  addText(slide, "Microsoft", 42, 10, 88, 18, {
    fontFace: FONT.body,
    fontPx: 11,
    color: C.white,
    bold: true,
    valign: "mid",
  });

  addText(slide, title, 180, 8, 920, 24, {
    fontFace: FONT.display,
    fontPx: 20,
    bold: true,
    color: C.white,
    align: "center",
    valign: "mid",
  });

  addRect(slide, 1110, 8, 154, 28, {
    fill: "132744",
    line: C.cyan,
    lineWidth: 1.25,
  });
  addText(slide, "AI UNLOCKED | TRUSTWORTHY AI", 1118, 15, 138, 14, {
    fontFace: FONT.display,
    fontPx: 9,
    bold: true,
    color: C.white,
    align: "center",
    valign: "mid",
    charSpace: 0.8,
  });

  addText(slide, "AgentGuard | Microsoft AI Unlocked", 16, FOOTER_Y + 5, 320, 12, {
    fontFace: FONT.body,
    fontPx: 9,
    color: C.white,
    valign: "mid",
  });
  addText(slide, `${slideNo} / ${totalSlides}`, 1200, FOOTER_Y + 5, 56, 12, {
    fontFace: FONT.body,
    fontPx: 9,
    color: C.white,
    bold: true,
    align: "right",
    valign: "mid",
  });
}

function addPlaceholder(slide, x, y, w, h, label) {
  addRect(slide, x, y, w, h, {
    fill: C.lightGray,
    line: "CBD5E1",
    lineWidth: 1.2,
    dashType: "dash",
  });
  addText(slide, label, x + 12, y + h / 2 - 10, w - 24, 20, {
    fontPx: 11,
    color: C.gray,
    align: "center",
    valign: "mid",
  });
}

function addChip(slide, x, y, w, h, label, opts = {}) {
  addRect(slide, x, y, w, h, {
    fill: opts.fill || C.light,
    line: opts.line || C.bodyLine,
    lineWidth: 1,
  });
  if (opts.dotColor) {
    slide.addShape(pptx.ShapeType.ellipse, {
      x: px(x + 8),
      y: px(y + h / 2 - 4),
      w: px(8),
      h: px(8),
      fill: { color: opts.dotColor },
      line: { color: opts.dotColor, transparency: 100, width: 0 },
    });
    addText(slide, label, x + 22, y + 4, w - 28, h - 8, {
      fontPx: opts.fontPx || 10,
      color: opts.color || C.text,
      bold: opts.bold || false,
      valign: "mid",
      align: "center",
    });
    return;
  }
  addText(slide, label, x + 6, y + 4, w - 12, h - 8, {
    fontPx: opts.fontPx || 10,
    color: opts.color || C.text,
    bold: opts.bold || false,
    valign: "mid",
    align: "center",
  });
}

function addStatCard(slide, cfg) {
  addRect(slide, cfg.x, cfg.y, cfg.w, cfg.h, {
    fill: cfg.fill || C.light,
    line: cfg.line || cfg.numberColor || C.bodyLine,
    lineWidth: 1.25,
  });
  const numberY = cfg.numberY !== undefined ? cfg.numberY : 6;
  const numberH = cfg.numberH !== undefined ? cfg.numberH : 26;
  const labelY = cfg.labelY !== undefined ? cfg.labelY : 34;
  const labelH = cfg.labelH !== undefined ? cfg.labelH : 24;
  const sourceY = cfg.sourceY !== undefined ? cfg.sourceY : 58;
  const sourceH = cfg.sourceH !== undefined ? cfg.sourceH : 12;
  const contextY = cfg.contextY !== undefined ? cfg.contextY : 72;
  const contextH = cfg.contextH !== undefined ? cfg.contextH : cfg.h - 80;
  addText(slide, cfg.number, cfg.x + 8, cfg.y + numberY, cfg.w - 16, numberH, {
    fontFace: FONT.display,
    fontPx: 28,
    bold: true,
    color: cfg.numberColor || C.blue,
    align: "left",
  });
  addText(slide, cfg.label, cfg.x + 8, cfg.y + labelY, cfg.w - 16, labelH, {
    fontPx: 11,
    bold: true,
    color: C.text,
  });
  addText(slide, cfg.source, cfg.x + 8, cfg.y + sourceY, cfg.w - 16, sourceH, {
    fontPx: 10,
    color: C.gray,
    italic: true,
  });
  addText(slide, cfg.context, cfg.x + 8, cfg.y + contextY, cfg.w - 16, contextH, {
    fontPx: 10,
    color: C.muted,
  });
}

function addFeatureBlock(slide, cfg) {
  addRect(slide, cfg.x, cfg.y, cfg.w, cfg.h, {
    fill: C.white,
    line: C.bodyLine,
    lineWidth: 1.2,
  });
  addRect(slide, cfg.x, cfg.y, cfg.w, BAR_H, {
    fill: C.bar,
    line: C.bar,
    lineWidth: 0,
  });
  addText(slide, cfg.title, cfg.x + 10, cfg.y + 4, cfg.w - 20, BAR_H - 8, {
    fontFace: FONT.display,
    fontPx: 10,
    bold: true,
    color: C.white,
    charSpace: 1,
    valign: "mid",
  });
  addText(slide, cfg.body, cfg.x + 10, cfg.y + 30, cfg.w - 20, cfg.h - 40, {
    fontPx: cfg.fontPx || 12,
    color: C.text,
  });
}

function addFeatureCard(slide, cfg) {
  addRect(slide, cfg.x, cfg.y, cfg.w, cfg.h, {
    fill: C.white,
    line: cfg.accent,
    lineWidth: 1.2,
  });
  addRect(slide, cfg.x, cfg.y, 6, cfg.h, {
    fill: cfg.accent,
    line: cfg.accent,
    lineWidth: 0,
  });
  addRect(slide, cfg.x, cfg.y, cfg.w, BAR_H, {
    fill: C.bar,
    line: C.bar,
    lineWidth: 0,
  });
  addText(slide, cfg.title, cfg.x + 14, cfg.y + 4, cfg.w - 28, BAR_H - 8, {
    fontFace: FONT.display,
    fontPx: 10,
    bold: true,
    color: C.white,
    charSpace: 1,
    valign: "mid",
  });
  addText(slide, cfg.number, cfg.x + cfg.w - 52, cfg.y + 4, 36, 12, {
    fontFace: FONT.display,
    fontPx: 10,
    bold: true,
    color: C.white,
    align: "right",
    valign: "mid",
  });
  addRect(slide, cfg.x + 14, cfg.y + 30, cfg.w - 28, 46, {
    fill: cfg.tint,
    line: cfg.tint,
    lineWidth: 0,
  });
  addText(slide, cfg.summary, cfg.x + 20, cfg.y + 38, cfg.w - 40, 30, {
    fontPx: 11,
    bold: true,
    color: C.text,
    valign: "mid",
  });

  if (cfg.chips && cfg.chips.length) {
    const chipGap = 6;
    const chipW = Math.floor((cfg.w - 28 - chipGap * (cfg.chips.length - 1)) / cfg.chips.length);
    cfg.chips.forEach((chip, index) => {
      addChip(slide, cfg.x + 14 + index * (chipW + chipGap), cfg.y + 82, chipW, 18, chip, {
        fill: C.light,
        line: C.bodyLine,
        fontPx: 9,
        bold: true,
      });
    });
  }

  (cfg.rows || []).forEach((row, index) => {
    const rowY = cfg.y + 106 + index * 42;
    addRect(slide, cfg.x + 14, rowY, cfg.w - 28, 36, {
      fill: index % 2 === 0 ? C.white : C.light,
      line: C.bodyLine,
      lineWidth: 1,
    });
    addText(slide, row.label, cfg.x + 20, rowY + 6, cfg.w - 40, 10, {
      fontFace: FONT.display,
      fontPx: 9,
      bold: true,
      color: cfg.accent,
      charSpace: 0.8,
    });
    addText(slide, row.text, cfg.x + 20, rowY + 18, cfg.w - 40, 12, {
      fontPx: 10,
      color: C.text,
    });
  });

  if (cfg.callout) {
    addRect(slide, cfg.x + 14, cfg.y + cfg.h - 44, cfg.w - 28, 28, {
      fill: cfg.tint,
      line: cfg.accent,
      lineWidth: 1,
    });
    addText(slide, cfg.callout, cfg.x + 20, cfg.y + cfg.h - 36, cfg.w - 40, 12, {
      fontPx: 10,
      color: C.text,
      bold: true,
      italic: true,
      valign: "mid",
    });
  }
}

function addAuditStep(slide, cfg) {
  addRect(slide, cfg.x, cfg.y, cfg.w, cfg.h, {
    fill: cfg.fill || C.white,
    line: C.bodyLine,
    lineWidth: 1,
  });
  addRect(slide, cfg.x, cfg.y, 6, cfg.h, {
    fill: cfg.accent,
    line: cfg.accent,
    lineWidth: 0,
  });
  addText(slide, cfg.title, cfg.x + 14, cfg.y + 8, cfg.w - 24, 18, {
    fontFace: FONT.display,
    fontPx: 12,
    bold: true,
    color: C.text,
  });
  addText(slide, cfg.line1, cfg.x + 14, cfg.y + 30, cfg.w - 24, 26, {
    fontPx: 12,
    color: C.text,
  });
  addText(slide, cfg.line2, cfg.x + 14, cfg.y + 60, cfg.w - 24, cfg.h - 68, {
    fontPx: 10,
    color: C.muted,
  });
}

function addTableCell(slide, text, x, y, w, h, opts = {}) {
  addRect(slide, x, y, w, h, {
    fill: opts.fill || C.white,
    line: opts.line || C.bodyLine,
    lineWidth: 1,
  });
  if (opts.leftAccent) {
    addRect(slide, x, y, 5, h, {
      fill: opts.leftAccent,
      line: opts.leftAccent,
      lineWidth: 0,
    });
  }
  addText(slide, text, x + (opts.leftAccent ? 10 : 6), y + 4, w - (opts.leftAccent ? 14 : 12), h - 8, {
    fontPx: opts.fontPx || 11,
    bold: opts.bold || false,
    color: opts.color || C.text,
    align: opts.align || "left",
    valign: "mid",
  });
}

function finalizeSlide(slide) {
  warnIfSlideHasOverlaps(slide, pptx, {
    muteContainment: true,
    ignoreLines: true,
  });
  warnIfSlideElementsOutOfBounds(slide, pptx);
}

function slide1() {
  const slide = pptx.addSlide();
  addHeaderFooter(slide, "AgentGuard | Product Vision", 1, 9);
  let y = BODY_Y;

  addRect(slide, 0, y, W, 124, { fill: "0D1F3C", line: "0D1F3C" });
  addRect(slide, 0, y, 6, 124, { fill: C.cyan, line: C.cyan });
  addText(slide, "PRODUCT VISION", 24, y + 16, 1232, 14, {
    fontFace: FONT.display,
    fontPx: 10,
    bold: true,
    color: C.cyan,
    charSpace: 1.4,
    align: "center",
  });
  addText(
    slide,
    "AgentGuard is the compliance layer that makes AI agent deployments auditable, accountable, and safe to run in production - without changing a single line of agent code.",
    90,
    y + 40,
    1100,
    56,
    {
      fontFace: FONT.display,
      fontPx: 16,
      bold: true,
      color: C.white,
      align: "center",
      valign: "mid",
    }
  );
  y += 124;

  addRect(slide, 0, y, W, 88, { fill: C.white, line: C.bodyLine });
  addText(
    slide,
    "AgentGuard | Round 2 Finalist | Top 54 of Microsoft AI Unlocked | Track 5: Trustworthy AI | Manipal Institute of Technology",
    24,
    y + 16,
    600,
    52,
    { fontPx: 12, color: C.text, valign: "mid" }
  );
  addVerticalDivider(slide, 640, y + 10, 68);
  addText(
    slide,
    "Team | Sarangan Srinivasan | Krishna Gera | Saanvi Bansal | Teen Bhai Teeno Tabahi",
    664,
    y + 16,
    592,
    52,
    { fontPx: 12, color: C.text, valign: "mid" }
  );
  y += 88;

  addRect(slide, 0, y, W, 72, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "The Problem", C.cyan);
  addText(
    slide,
    "87% of enterprises have AI agents deployed. 90% are over-permissioned. There is no enforcement layer between what those agents decide and what they execute.",
    24,
    y + 30,
    1232,
    34,
    { fontPx: 12, color: C.text, valign: "mid" }
  );
  y += 72;

  addRect(slide, 0, y, W, 170, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "What AgentGuard Provides", C.blue);
  const pillarY = y + 30;
  const pillarW = 320;
  const pillars = [
    {
      x: 0,
      title: "Privacy",
      body: "PII anonymized before any agent sees it. Zero sensitive data reaches the model.",
      accent: C.cyan,
    },
    {
      x: 320,
      title: "Security",
      body: "Every action risk-scored 0-100 before execution. Four-factor contextual analysis.",
      accent: C.red,
    },
    {
      x: 640,
      title: "Compliance",
      body: "Immutable audit trail in Azure Cosmos DB. PDF compliance report on demand.",
      accent: C.green,
    },
    {
      x: 960,
      title: "Control",
      body: "YAML policy engine. Agent permissions enforced externally. Agent cannot bypass.",
      accent: C.amber,
    },
  ];
  pillars.forEach((pillar) => {
    addRect(slide, pillar.x, pillarY, pillarW, 140, {
      fill: pillar.x % 640 === 0 ? C.white : C.light,
      line: C.bodyLine,
    });
    addRect(slide, pillar.x, pillarY, 5, 140, {
      fill: pillar.accent,
      line: pillar.accent,
    });
    addText(slide, pillar.title, pillar.x + 16, pillarY + 14, pillarW - 24, 18, {
      fontFace: FONT.display,
      fontPx: 14,
      bold: true,
      color: C.text,
    });
    addText(slide, pillar.body, pillar.x + 16, pillarY + 42, pillarW - 24, 74, {
      fontPx: 12,
      color: C.text,
    });
  });
  y += 170;

  addRect(slide, 0, y, W, 84, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "Live Data From Real Runs", C.green);
  addText(
    slide,
    "384 decisions | 159 blocked (41%) | 225 auto-executed | 425 PII entities masked",
    24,
    y + 32,
    1232,
    18,
    {
      fontFace: FONT.display,
      fontPx: 18,
      bold: true,
      color: C.blue,
      align: "center",
      valign: "mid",
    }
  );
  addText(
    slide,
    "Not simulated. Real pipeline runs logged to Azure Cosmos DB.",
    24,
    y + 56,
    1232,
    14,
    { fontPx: 10, color: C.gray, align: "center" }
  );
  y += 84;

  addRect(slide, 0, y, W, 66, { fill: C.lightAmber, line: "FCD7AA" });
  addRect(slide, 0, y, 6, 66, { fill: C.amber, line: C.amber });
  addText(
    slide,
    "Today: law firms and hospitals. Tomorrow: the standard for every regulated AI deployment. Every enterprise deploying AI agents is a potential customer - and 87% already have agents deployed.",
    20,
    y + 14,
    1240,
    40,
    { fontPx: 12, color: C.text, bold: true, valign: "mid" }
  );
  y += 66;

  addRect(slide, 0, y, W, 48, { fill: C.bar, line: C.bar });
  addText(
    slide,
    "Powered by: Azure OpenAI | Azure Cosmos DB | Azure AI Content Safety | Microsoft Presidio | FastAPI | Azure Container Apps",
    24,
    y + 14,
    1232,
    18,
    { fontPx: 12, color: C.white, align: "center", valign: "mid" }
  );

  finalizeSlide(slide);
}

function slide2() {
  const slide = pptx.addSlide();
  addHeaderFooter(slide, "AgentGuard | The Problem", 2, 9);
  let y = BODY_Y;

  addRect(slide, 0, y, W, 112, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "Who Is Facing This Problem", C.blue);
  addText(
    slide,
    "CISOs, compliance officers, and IT directors at enterprises deploying AI agents in regulated environments - law firms, hospitals, financial institutions - responsible for ensuring regulatory compliance when agents operate autonomously.",
    24,
    y + 32,
    700,
    70,
    { fontPx: 12, color: C.text }
  );
  addVerticalDivider(slide, 760, y + 28, 80);
  const chipLabels = ["Banking", "Healthcare", "Legal", "Defence"];
  chipLabels.forEach((label, index) => {
    addChip(slide, 790 + index * 110, y + 36, 96, 26, label, {
      fill: C.light,
      bold: true,
      fontPx: 10,
    });
  });
  addText(
    slide,
    "Key stakeholders who face career-ending consequences when an AI agent exceeds its authority.",
    790,
    y + 72,
    446,
    26,
    { fontPx: 10, color: C.muted }
  );
  y += 112;

  addRect(slide, 0, y, W, 132, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "Why It Matters - The Evidence", C.red);
  const statW = W / 6;
  const stats = [
    ["87%", "Enterprises with AI agents deployed", "Obsidian Security 2025", "Every single one is a potential AgentGuard customer", C.blue],
    ["90%", "Of those agents are over-permissioned", "Obsidian Security 2025", "Nine in ten have more access than they need", C.red],
    ["16x", "More data moved by agents than humans", "Obsidian Security 2025", "Exponentially larger blast radius per incident", C.amber],
    ["$7.42M", "Average healthcare breach cost", "IBM Cost of Data Breach 2025", "Most expensive industry for 14 consecutive years", C.red],
    ["97%", "AI breach victims lacked access controls", "IBM Research", "The gap AgentGuard fills directly", C.purple],
    ["41%", "Of our 384 real decisions needed intervention", "AgentGuard live data", "The threat is real, not theoretical", C.green],
  ];
  stats.forEach((item, index) => {
    addStatCard(slide, {
      x: index * statW,
      y: y + 24,
      w: statW,
      h: 102,
      number: item[0],
      label: item[1],
      source: item[2],
      context: item[3],
      numberColor: item[4],
      fill: index % 2 === 0 ? C.light : C.white,
      labelH: 22,
      sourceY: 60,
      sourceH: 10,
      contextY: 74,
      contextH: 20,
    });
  });
  y += 132;

  addRect(slide, 0, y, W, 254, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "Why Existing Solutions Fail", C.amber);
  const cols = [190, 235, 235, 120, 120, 120, 260];
  const headers = [
    "Solution",
    "What It Does",
    "What It Misses",
    "Action Intercept",
    "Audit Trail",
    "Domain Modes",
    "Verdict",
  ];
  let cx = 0;
  headers.forEach((header, index) => {
    addTableCell(slide, header, cx, y + 30, cols[index], 30, {
      fill: C.bar,
      line: C.bodyLine,
      color: C.white,
      bold: true,
      fontPx: 11,
      align: index >= 3 && index <= 5 ? "center" : "left",
    });
    cx += cols[index];
  });

  const tableRows = [
    ["Microsoft Presidio", "PII detection at message layer", "No action interception", "NO", "NO", "NO", "Content layer only"],
    ["LlamaGuard", "Prompt and response safety", "No policy engine", "NO", "NO", "NO", "Probabilistic"],
    ["Lakera Guard", "Injection detection", "No domain modes", "NO", "NO", "NO", "Single-signal"],
    ["All existing tools", "Best-effort checks", "No compliance output", "NO", "NO", "NO", "Not prod-grade"],
    ["AgentGuard", "Full pipeline interception + compliance", "-", "YES", "YES", "YES", "Production-grade"],
  ];
  tableRows.forEach((row, rowIndex) => {
    let x = 0;
    const rowY = y + 60 + rowIndex * 32;
    row.forEach((cell, index) => {
      addTableCell(slide, cell, x, rowY, cols[index], 32, {
        fill: rowIndex === 4 ? C.lightGreen : rowIndex % 2 === 0 ? C.white : C.light,
        leftAccent: index === 0 && rowIndex === 4 ? C.green : undefined,
        align: index >= 3 && index <= 5 ? "center" : "left",
        bold: rowIndex === 4 && index === 0,
        fontPx: 11,
      });
      x += cols[index];
    });
  });
  addText(
    slide,
    "No existing product combines action-level interception, domain-specific PII detection, agent reputation, multi-turn attack detection, and PDF compliance output.",
    20,
    y + 224,
    1240,
    18,
    { fontPx: 10, color: C.gray, align: "center", italic: true, valign: "mid" }
  );
  y += 254;

  addRect(slide, 0, y, W, 74, { fill: C.lightAmber, line: "FCD7AA" });
  addRect(slide, 0, y, 6, 74, { fill: C.amber, line: C.amber });
  addText(
    slide,
    "One bad prompt can trigger a $2M wire transfer, delete audit logs, and leak patient data - simultaneously. Existing tools cannot stop this at the action layer.",
    18,
    y + 12,
    1244,
    22,
    { fontPx: 13, bold: true, color: C.text }
  );
  addText(
    slide,
    "AgentGuard is the only product that intercepts at the action layer, enforces domain-specific policies, and produces a compliance report that survives a regulatory audit.",
    18,
    y + 42,
    1244,
    18,
    { fontPx: 10, color: C.amber, bold: true }
  );
  y += 74;

  addRect(slide, 0, y, W, 80, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "Real-World Context", C.purple);
  const rw = (W - 32) / 3;
  const realWorld = [
    {
      source: "TROUTMAN PEPPER LOCKE | MERGER COMMS",
      quote: "\"Already automating 80% of merger communications.\"",
      accent: C.blue,
    },
    {
      source: "LEXISNEXIS CEO | JAN 2026",
      quote: "\"Show me your guardrails\" is increasingly becoming \"show me your workflow.\"",
      accent: C.purple,
    },
    {
      source: "EU AI ACT + HIPAA AI AMENDMENTS",
      quote: "Compliance is no longer optional for autonomous systems handling regulated data.",
      accent: C.red,
    },
  ];
  realWorld.forEach((item, index) => {
    const cardX = 8 + index * (rw + 8);
    addRect(slide, cardX, y + 28, rw, 48, {
      fill: index % 2 === 0 ? C.light : C.white,
      line: C.bodyLine,
      lineWidth: 1,
    });
    addRect(slide, cardX, y + 28, 5, 48, {
      fill: item.accent,
      line: item.accent,
      lineWidth: 0,
    });
    addText(slide, item.source, cardX + 12, y + 34, rw - 20, 10, {
      fontFace: FONT.display,
      fontPx: 9,
      bold: true,
      color: item.accent,
      charSpace: 0.8,
    });
    addText(slide, item.quote, cardX + 12, y + 48, rw - 20, 22, {
      fontPx: 12,
      color: C.text,
      bold: index === 1,
      italic: index !== 2,
    });
  });

  finalizeSlide(slide);
}

function slide3() {
  const slide = pptx.addSlide();
  addHeaderFooter(slide, "AgentGuard | Our Solution", 3, 9);
  let y = BODY_Y;

  addRect(slide, 0, y, W, 96, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "The Core Idea", C.cyan);
  addText(
    slide,
    "AgentGuard sits between every AI agent and everything that agent is allowed to touch. It does not modify the agent. It intercepts proposed actions, evaluates them against a configurable policy the agent cannot read or bypass, and either approves, escalates to a human, or blocks - in under two seconds.",
    24,
    y + 30,
    1232,
    38,
    { fontPx: 12, color: C.text }
  );
  addText(
    slide,
    "Framework-agnostic | Three lines of code | AutoGen | Semantic Kernel | LangChain | OpenClaw | any framework | zero changes to the agent",
    24,
    y + 70,
    1232,
    16,
    { fontPx: 10, color: C.gray, bold: true, align: "center", valign: "mid" }
  );
  y += 96;

  addRect(slide, 0, y, W, 188, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "The Pipeline", C.blue);
  addPlaceholder(
    slide,
    18,
    y + 30,
    1244,
    130,
    "INSERT GEMINI DIAGRAM: AgentGuard Pipeline Flow - horizontal nodes left to right"
  );
  const pipeLabels = [
    "User Request",
    "Privacy Layer",
    "Agent Sandbox",
    "Pre-Filter",
    "Risk Scorer",
    "Policy Engine",
    "Intervention Tier",
    "Cosmos DB",
    "Dashboard",
  ];
  const pipeW = 138;
  pipeLabels.forEach((label, index) => {
    addChip(slide, 12 + index * 140, y + 164, pipeW, 20, label, {
      fill: index % 2 === 0 ? C.lightBlue : C.light,
      line: C.bodyLine,
      fontPx: 9,
      bold: true,
    });
  });
  y += 188;

  addRect(slide, 0, y, W, 144, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "Real Results From Live Test Runs", C.green);
  const cardW = W / 4;
  const cards = [
    ["384", "Total decisions processed", "Real pipeline runs, logged to Azure Cosmos DB", "Across all three deployment profiles\nfinance | legal | healthcare", C.blue],
    ["159", "Blocked or escalated - 41%", "41% of all requests required intervention", "The threat is real, not theoretical\ncross-matter | PHI | injection | bulk export", C.red],
    ["225", "Auto-executed", "Fast, frictionless, fully logged", "The green path - safe decisions at full speed\nAverage score: under 25 / 100", C.green],
    ["425", "PII entities masked", "Zero sensitive data reached any agent", "Names, emails, MRN numbers, matter refs\nAll replaced with typed placeholders", C.cyan],
  ];
  cards.forEach((item, index) => {
    addStatCard(slide, {
      x: index * cardW,
      y: y + 30,
      w: cardW,
      h: 110,
      number: item[0],
      label: item[1],
      source: item[2],
      context: item[3],
      numberColor: item[4],
      fill: index % 2 === 0 ? C.light : C.white,
    });
  });
  y += 144;

  addRect(slide, 0, y, W, 112, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "Intervention Tiers - How Decisions Are Made", C.amber);
  const tierW = W / 4;
  const tiers = [
    ["AUTO-EXECUTE", "Score 0-30", "Immediate | Logged silently | Safe operations", C.green, C.lightGreen],
    ["SOFT CONFIRM", "Score 30-60", "User prompted | One-click approval | Borderline actions", C.yellow, "FFFBEB"],
    ["HARD CONFIRM", "Score 60-85", "Execution stopped | Escalated to human | High-risk actions", C.orange, "FFF7ED"],
    ["BLOCK", "Score 85-100", "Rejected outright | Admin notified | Incident ID created", C.red, "FEF2F2"],
  ];
  tiers.forEach((tier, index) => {
    addRect(slide, index * tierW, y + 30, tierW, 82, {
      fill: tier[4],
      line: C.bodyLine,
    });
    addRect(slide, index * tierW, y + 30, 6, 82, { fill: tier[3], line: tier[3] });
    addText(slide, tier[0], index * tierW + 14, y + 38, tierW - 20, 18, {
      fontFace: FONT.display,
      fontPx: 12,
      bold: true,
      color: C.text,
    });
    addText(slide, tier[1], index * tierW + 14, y + 58, tierW - 20, 14, {
      fontPx: 11,
      bold: true,
      color: tier[3],
    });
    addText(slide, tier[2], index * tierW + 14, y + 76, tierW - 20, 26, {
      fontPx: 10,
      color: C.muted,
    });
  });
  y += 112;

  addRect(slide, 0, y, W, 112, { fill: C.bar, line: C.bar });
  addRect(slide, 1038, y + 10, 220, 18, {
    fill: "132744",
    line: C.cyan,
    lineWidth: 1,
  });
  addText(slide, "18 FIELDS LOGGED ON EVERY EVENT", 1046, y + 14, 204, 10, {
    fontFace: FONT.display,
    fontPx: 9,
    bold: true,
    color: C.white,
    align: "center",
    valign: "mid",
    charSpace: 0.7,
  });
  addText(
    slide,
    "Every decision in all four tiers is logged to Azure Cosmos DB as a complete audit record.",
    20,
    y + 10,
    980,
    18,
    { fontPx: 12, bold: true, color: C.white }
  );
  addText(
    slide,
    "Each event record captures who acted, what was requested, which signals fired, which policy applied, and exactly how AgentGuard responded.",
    20,
    y + 28,
    1230,
    14,
    { fontPx: 10, color: "D7E3F4" }
  );
  const auditCards = [
    ["RECORD IDENTITY", "agent_id | timestamp | scored_by", C.blue],
    ["REQUEST CONTEXT", "policy_domain | pii_entities_detected | prefilter_hit", C.cyan],
    ["SAFETY SIGNALS", "azure_content_safety | canary_triggered | cumulative_boost", C.amber],
    ["DECISION LOGIC", "risk_score | tier | policy_flags", C.purple],
    ["OUTCOME & EVIDENCE", "result_status | cosmos_logged | escalation / incident linkage", C.green],
  ];
  const auditW = 240;
  auditCards.forEach((card, index) => {
    const cardX = 24 + index * 248;
    addRect(slide, cardX, y + 48, auditW, 30, {
      fill: C.white,
      line: card[2],
      lineWidth: 1.2,
    });
    addRect(slide, cardX, y + 48, 5, 30, {
      fill: card[2],
      line: card[2],
      lineWidth: 0,
    });
    addText(slide, card[0], cardX + 12, y + 52, auditW - 20, 10, {
      fontFace: FONT.display,
      fontPx: 9,
      bold: true,
      color: card[2],
      charSpace: 0.7,
    });
    addText(slide, card[1], cardX + 12, y + 64, auditW - 20, 10, {
      fontPx: 9,
      color: C.text,
    });
  });
  addText(
    slide,
    "This is the evidence layer that turns a guardrail into an auditable product, not just a best-effort filter.",
    20,
    y + 88,
    1240,
    16,
    { fontPx: 10, color: C.cyan, bold: true, align: "center" }
  );

  finalizeSlide(slide);
}

function slide4() {
  const slide = pptx.addSlide();
  addHeaderFooter(slide, "AgentGuard | Product Walkthrough", 4, 9);
  const leftW = Math.round(W * 0.58);
  const rightW = W - leftW;
  const y = BODY_Y;

  addRect(slide, 0, y, leftW, BODY_H, { fill: C.white, line: C.bodyLine });
  addSectionBarBox(slide, 0, y, leftW, "The Pearson Hardman Scenario - Five Steps", C.blue);
  addText(
    slide,
    "A law firm deploys four AI agents. One tries to access a document it is not authorised to see.",
    18,
    y + 28,
    leftW - 36,
    28,
    { fontPx: 12, color: C.text, bold: true, align: "center", valign: "mid" }
  );
  const stepX = 18;
  const stepW = leftW - 36;
  const steps = [
    ["1. AGENT SENDS REQUEST", "research-bot-001: Pull all documents from MATTER-2024-002 and attach to Johnson discovery response.", "This agent is scoped to MATTER-2024-001 only. It has no knowledge of that restriction.", C.blue, C.white],
    ["2. PRIVACY LAYER INTERCEPTS", "Matter references anonymized. Canary token MATTER-CANARY-{token} injected silently before agent processes anything.", "The agent never sees the real matter reference - only a typed placeholder.", C.blue, C.light],
    ["3. POLICY ENGINE FIRES", "MATTER-2024-002 is in research-bot-001's forbidden_matters list. Cross-matter access detected. Score boosted to 98 / 100.", "Tier: BLOCK. Policy override: +80. No human needed.", C.red, C.white],
    ["4. LOGGED TO COSMOS DB", "Full audit record: agent_id: research-bot-001 | risk_score: 98 | tier: block | cross_matter_access: true | cosmos_logged: true", "Immutable. 18 fields. Defensible in a regulatory review.", C.green, C.light],
    ["5. COMPLIANCE REPORT", "One click generates PDF. Key line: Privilege contamination incidents: 0", "The breach was blocked before it completed. The agent never saw that document.", C.green, C.white],
  ];
  steps.forEach((step, index) => {
    addAuditStep(slide, {
      x: stepX,
      y: y + 58 + index * 104,
      w: stepW,
      h: 102,
      title: step[0],
      line1: step[1],
      line2: step[2],
      accent: step[3],
      fill: step[4],
    });
  });
  addText(
    slide,
    "The partner never had to intervene. The compliance report is clean. This is what zero contamination looks like.",
    18,
    y + 600,
    leftW - 36,
    26,
    { fontPx: 12, bold: true, color: C.text, align: "center", valign: "mid" }
  );

  addRect(slide, leftW, y, rightW, BODY_H, { fill: C.light, line: C.bodyLine });
  addVerticalDivider(slide, leftW, y, BODY_H);

  addRect(slide, leftW, y, rightW, 204, { fill: C.white, line: C.bodyLine });
  addSectionBarBox(slide, leftW, y, rightW, "Demo Pipeline", C.cyan);
  addPlaceholder(
    slide,
    leftW + 16,
    y + 30,
    rightW - 32,
    130,
    "INSERT SCREENSHOT: Demo pipeline steps - five-step breakdown"
  );
  addText(
    slide,
    "Live pipeline run showing Privacy Layer -> Agent Processing -> Security Checkpoint -> Intervention Decision -> Cosmos DB Audit Trail",
    leftW + 16,
    y + 168,
    rightW - 32,
    26,
    { fontPx: 10, color: C.gray, align: "center", valign: "mid" }
  );

  addRect(slide, leftW, y + 204, rightW, 170, { fill: C.white, line: C.bodyLine });
  addSectionBarBox(slide, leftW, y + 204, rightW, "Memorial General - Domain Switch", C.green);
  addText(
    slide,
    "Same product. Different YAML config. Different domain.",
    leftW + 16,
    y + 236,
    rightW - 32,
    18,
    { fontPx: 12, bold: true, color: C.text, align: "center" }
  );
  addText(slide, "Switch to Memorial General Hospital - one dropdown - no server restart - no code changes", leftW + 16, y + 266, rightW - 32, 18, {
    fontPx: 10,
    color: C.text,
  });
  addText(slide, "pharmacy-agent attempts: Retrieve psychiatric medication history for MRN-002391 for cardiology review", leftW + 16, y + 290, rightW - 32, 18, {
    fontPx: 10,
    color: C.text,
  });
  addText(slide, "Result: BLOCK | special_category_phi: true | PHI breaches: 0 | HIPAA minimum necessary enforced", leftW + 16, y + 314, rightW - 32, 18, {
    fontPx: 10,
    color: C.red,
    bold: true,
  });
  addText(slide, "The architecture is universal. The policy is configurable.", leftW + 16, y + 338, rightW - 32, 18, {
    fontPx: 12,
    bold: true,
    color: C.blue,
    align: "center",
  });

  addRect(slide, leftW, y + 374, rightW, 198, { fill: C.white, line: C.bodyLine });
  addSectionBarBox(slide, leftW, y + 374, rightW, "Audit Log Evidence", C.amber);
  addPlaceholder(
    slide,
    leftW + 16,
    y + 404,
    rightW - 32,
    130,
    "INSERT SCREENSHOT: Audit log table - mix of AUTO green and BLOCK red decisions"
  );
  addText(
    slide,
    "Every decision from both scenarios logged to Azure Cosmos DB in real time. Source of truth for all compliance reporting.",
    leftW + 16,
    y + 540,
    rightW - 32,
    22,
    { fontPx: 10, color: C.gray, align: "center", valign: "mid" }
  );

  addRect(slide, leftW, y + 572, rightW, 80, { fill: C.bar, line: C.bar });
  addText(
    slide,
    "AgentGuard processed 384 real decisions across finance | legal | healthcare domains.",
    leftW + 16,
    y + 592,
    rightW - 32,
    16,
    { fontPx: 12, color: C.white, bold: true, align: "center" }
  );
  addText(
    slide,
    "41% required intervention.",
    leftW + 16,
    y + 614,
    rightW - 32,
    14,
    { fontPx: 10, color: C.cyan, bold: true, align: "center" }
  );

  finalizeSlide(slide);
}

function slide5() {
  const slide = pptx.addSlide();
  addHeaderFooter(slide, "AgentGuard | Key Features", 5, 9);
  let y = BODY_Y;

  addRect(slide, 0, y, W, 22, { fill: C.bar, line: C.bar });
  addText(slide, "FIVE CAPABILITIES NO COMPETITOR COMBINES", 16, y + 4, W - 32, 14, {
    fontFace: FONT.display,
    fontPx: 10,
    bold: true,
    color: C.white,
    charSpace: 1.2,
    align: "center",
    valign: "mid",
  });
  y += 22;

  const colW = Math.floor(W / 3);
  const topH = 322;
  addFeatureCard(slide, {
    x: 0,
    y,
    w: colW,
    h: topH,
    title: "POLICY-AS-YAML ENGINE",
    number: "01",
    accent: C.blue,
    tint: C.lightBlue,
    summary: "External policy enforcement. The agent cannot read, change, or bypass its own permissions.",
    chips: ["TechCorp Finance", "Pearson Hardman", "Memorial General"],
    rows: [
      { label: "HOW IT WORKS", text: "Permissions live in YAML outside the agent and are enforced at the network layer." },
      { label: "WHY IT MATTERS", text: "One new domain means one new YAML file, not a rewrite or a restart." },
      { label: "BUYER SIGNAL", text: "Enterprise teams immediately understand the phrase: your agent cannot override its own policy." },
      { label: "READINESS", text: "Three validated configurations already ship with the product for testing and rollout." },
    ],
    callout: "The cleanest enterprise story on the slide: policy stays outside the agent.",
  });
  addFeatureCard(slide, {
    x: colW,
    y,
    w: colW,
    h: topH,
    title: "CANARY TOKEN INJECTION",
    number: "02",
    accent: C.amber,
    tint: C.lightAmber,
    summary: "A hidden sentinel token fingerprints exfiltration that looks perfectly normal to traditional filters.",
    chips: ["Finance email", "Legal matter tag", "Healthcare MRN"],
    rows: [
      { label: "MECHANISM", text: "AgentGuard plants a unique canary in the context before the agent acts." },
      { label: "TRIGGER", text: "If the token comes back in the response, the action is blocked and the event is logged." },
      { label: "DEFENSIVE VALUE", text: "This catches exfiltration attempts that do not contain suspicious keywords or obvious prompts." },
      { label: "COMPETITIVE EDGE", text: "Keyword filters miss this category. Generic safety models often miss it too." },
    ],
    callout: "It detects a class of leakage competitors cannot easily see.",
  });
  addFeatureCard(slide, {
    x: colW * 2,
    y,
    w: W - colW * 2,
    h: topH,
    title: "MULTI-TURN ATTACK DETECTION",
    number: "03",
    accent: C.red,
    tint: "FEF2F2",
    summary: "AgentGuard catches reconnaissance chains across multiple messages, not just single prompts in isolation.",
    chips: ["Track last 5 scores", "Per-agent memory", "Boost up to +40"],
    rows: [
      { label: "PATTERN", text: "A safe-looking query can become dangerous when it is the third step in a sequence." },
      { label: "ISOLATION", text: "Each agent has its own rolling history so one suspicious actor does not poison the others." },
      { label: "EXAMPLE", text: "Message 1 scores 15. Message 3 scores 58 plus the cumulative boost, landing at 98 and BLOCK." },
      { label: "VALUE", text: "This is how AgentGuard catches the reconnaissance behavior single-message scanners miss." },
    ],
    callout: "The attack pattern every competitor says is 'safe enough' until it is too late.",
  });
  y += topH;

  const bottomGap = 10;
  const bottomW = Math.floor((W - bottomGap) / 2);
  const bottomY = y;
  addFeatureCard(slide, {
    x: 0,
    y: bottomY,
    w: bottomW,
    h: 308,
    title: "AGENT REPUTATION SCORE",
    number: "04",
    accent: C.green,
    tint: C.lightGreen,
    summary: "Trust is persistent. A risky agent does not return next week with a clean slate and full autonomy.",
    chips: ["HIGH 70+", "MEDIUM 30-69", "LOW <30"],
    rows: [
      { label: "PERSISTENCE", text: "Scores are stored in Azure Cosmos DB across sessions, not recalculated from scratch each time." },
      { label: "CONTROL", text: "High-trust agents move faster. Low-trust agents face tighter thresholds and mandatory review." },
      { label: "HISTORY", text: "Score changes retain the previous score, new score, timestamp, and reason for every adjustment." },
      { label: "WHY IT MATTERS", text: "The guardrails adapt over time instead of forgetting an agent's past behavior." },
    ],
    callout: "Persistent trust scoring makes the guardrails smarter every week.",
  });
  const domainX = bottomW + bottomGap;
  const domainW = W - bottomW - bottomGap;
  addRect(slide, domainX, bottomY, domainW, 308, {
    fill: C.white,
    line: C.purple,
    lineWidth: 1.2,
  });
  addRect(slide, domainX, bottomY, 6, 308, { fill: C.purple, line: C.purple, lineWidth: 0 });
  addRect(slide, domainX, bottomY, domainW, BAR_H, { fill: C.bar, line: C.bar, lineWidth: 0 });
  addText(slide, "DOMAIN-SPECIFIC PROTECTION", domainX + 14, bottomY + 4, domainW - 28, BAR_H - 8, {
    fontFace: FONT.display,
    fontPx: 10,
    bold: true,
    color: C.white,
    charSpace: 1,
    valign: "mid",
  });
  addText(slide, "05", domainX + domainW - 52, bottomY + 4, 36, 12, {
    fontFace: FONT.display,
    fontPx: 10,
    bold: true,
    color: C.white,
    align: "right",
    valign: "mid",
  });
  addRect(slide, domainX + 14, bottomY + 30, domainW - 28, 42, {
    fill: "F5F3FF",
    line: "F5F3FF",
    lineWidth: 0,
  });
  addText(slide, "Same protection architecture. Different domain rules, patterns, and enforcement logic delivered through YAML configuration.", domainX + 20, bottomY + 40, domainW - 40, 24, {
    fontPx: 11,
    bold: true,
    color: C.text,
    valign: "mid",
  });
  const domainInnerGap = 10;
  const domainColW = Math.floor((domainW - 28 - domainInnerGap) / 2);
  const legalX = domainX + 14;
  const healthX = legalX + domainColW + domainInnerGap;
  [
    {
      x: legalX,
      title: "LEGAL MODE",
      accent: C.blue,
      rows: [
        "Detects matter numbers, privilege markers, Bates numbers, bar IDs, and opposing counsel patterns.",
        "Stops cross-matter access attempts before they become privilege contamination incidents.",
        "Enforces matter-based scoping and outbound restrictions per agent.",
      ],
    },
    {
      x: healthX,
      title: "HEALTHCARE MODE",
      accent: C.red,
      rows: [
        "Detects MRN, ICD-10 codes, CPT codes, NPI numbers, DEA numbers, and insurance member IDs.",
        "Flags psychiatric and HIV records as special-category PHI requiring stricter intervention.",
        "Enforces HIPAA minimum necessary access and domain-specific scope controls.",
      ],
    },
  ].forEach((panel) => {
    addRect(slide, panel.x, bottomY + 82, domainColW, 172, {
      fill: panel.title === "LEGAL MODE" ? C.lightBlue : "FEF2F2",
      line: panel.accent,
      lineWidth: 1,
    });
    addText(slide, panel.title, panel.x + 12, bottomY + 92, domainColW - 24, 14, {
      fontFace: FONT.display,
      fontPx: 10,
      bold: true,
      color: panel.accent,
      charSpace: 0.8,
    });
    panel.rows.forEach((row, index) => {
      addRect(slide, panel.x + 10, bottomY + 112 + index * 44, domainColW - 20, 34, {
        fill: C.white,
        line: C.bodyLine,
        lineWidth: 1,
      });
      addText(slide, row, panel.x + 16, bottomY + 122 + index * 44, domainColW - 32, 16, {
        fontPx: 10,
        color: C.text,
        valign: "mid",
      });
    });
  });
  addRect(slide, domainX + 14, bottomY + 260, domainW - 28, 32, {
    fill: "F5F3FF",
    line: C.purple,
    lineWidth: 1,
  });
  addText(slide, "Configured entirely through YAML: same core platform, different entity patterns, scopes, and regulatory rules.", domainX + 22, bottomY + 269, domainW - 44, 14, {
    fontPx: 10,
    color: C.text,
    bold: true,
    align: "center",
    valign: "mid",
  });

  finalizeSlide(slide);
}

function slide6() {
  const slide = pptx.addSlide();
  addHeaderFooter(slide, "AgentGuard | Architecture and Tech Stack", 6, 9);
  let y = BODY_Y;

  addRect(slide, 0, y, W, 238, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "System Architecture", C.blue);
  addPlaceholder(
    slide,
    18,
    y + 30,
    1244,
    130,
    "INSERT GEMINI DIAGRAM: Full system architecture - Pearson Hardman agents left | AgentGuard pipeline center | Memorial General agents right | Cosmos DB and Dashboard bottom"
  );
  const componentLabels = [
    ["Privacy Layer", C.blue],
    ["Pre-Filter", C.orange],
    ["Risk Scorer", C.purple],
    ["Policy Engine", C.yellow],
    ["Intervention Tier", C.amber],
    ["Cosmos DB", C.green],
    ["Dashboard", C.blue],
    ["FastAPI Server", C.gray],
  ];
  componentLabels.forEach((item, index) => {
    addChip(slide, 12 + index * 158, y + 172, 150, 24, item[0], {
      fill: index % 2 === 0 ? C.light : C.white,
      dotColor: item[1],
      fontPx: 10,
      bold: true,
    });
  });
  addText(slide, "Each placeholder is fixed height. The explanatory layer below it now carries the density.", 24, y + 212, 1232, 12, {
    fontPx: 10,
    color: C.gray,
    align: "center",
  });
  y += 238;

  addRect(slide, 0, y, W, 140, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "Data Flow", C.cyan);
  addPlaceholder(
    slide,
    24,
    y + 30,
    1232,
    80,
    "INSERT GEMINI DIAGRAM: Compact horizontal data flow strip - User -> Privacy -> Pre-Filter -> Risk Scorer -> Policy -> Intervention -> Cosmos DB -> Dashboard"
  );
  addText(
    slide,
    "Every request travels all layers in sequence. Nothing bypasses. Pre-filter catches obvious threats in <1ms. LLM scorer handles ambiguous cases in 1-2.5 seconds.",
    24,
    y + 116,
    1232,
    14,
    { fontPx: 10, color: C.text, align: "center", valign: "mid" }
  );
  y += 140;

  addRect(slide, 0, y, W, 204, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "Technology Stack", C.green);
  addVerticalDivider(slide, 640, y + 30, 160);
  addText(slide, "AI AND INTELLIGENCE", 24, y + 34, 580, 14, {
    fontFace: FONT.display,
    fontPx: 11,
    bold: true,
    color: C.blue,
  });
  const leftRows = [
    ["Azure OpenAI GPT-4o-mini", "PII entity detection with domain-specific prompt addons. Four-factor risk scoring with written reasoning. Every decision explainable."],
    ["Microsoft Presidio", "Local entity detection. Zero API cost. Zero latency. Zero data leaves the machine for PII detection. Runs before any Azure call."],
    ["Azure AI Content Safety", "Parallel jailbreak and injection detection on every request. Independent second signal. When both pre-filter and Content Safety flag, two systems are logged separately."],
  ];
  leftRows.forEach((row, index) => {
    addText(slide, row[0], 24, y + 58 + index * 44, 220, 16, {
      fontPx: 11,
      bold: true,
      color: C.blue,
    });
    addText(slide, row[1], 250, y + 58 + index * 44, 360, 28, {
      fontPx: 10,
      color: C.text,
    });
  });
  addText(slide, "INFRASTRUCTURE AND DATA", 664, y + 34, 580, 14, {
    fontFace: FONT.display,
    fontPx: 11,
    bold: true,
    color: C.blue,
  });
  const rightRows = [
    ["Azure Cosmos DB", "Immutable audit log. 18 fields per record. Reputation persistence across sessions. Compliance report source of truth."],
    ["FastAPI", "Production REST API. POST /intercept | POST /confirm | GET /status/{id}. HTML dashboard served as static files on the same port."],
    ["Azure Container Apps", "Production deployment target. Auto-scaling. Enterprise-grade. HTML/CSS/JS dashboard - 7 pages, real-time polling, 9 navigation sections."],
  ];
  rightRows.forEach((row, index) => {
    addText(slide, row[0], 664, y + 58 + index * 44, 190, 16, {
      fontPx: 11,
      bold: true,
      color: C.blue,
    });
    addText(slide, row[1], 860, y + 58 + index * 44, 364, 28, {
      fontPx: 10,
      color: C.text,
    });
  });
  addText(slide, "Every Azure service chosen because it is the right tool for that specific layer - not for the sake of using Azure.", 24, y + 184, 1232, 12, {
    fontPx: 10,
    italic: true,
    color: C.gray,
    align: "center",
  });
  y += 204;

  addRect(slide, 0, y, W, 70, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "Engineering Decisions", C.amber);
  const engW = W / 3;
  const engTexts = [
    "Modular architecture - policy engine, privacy layer, risk scorer, and pre-filter are independently swappable.",
    "Domain agnosticism - the same core serves finance, legal, and healthcare through YAML configuration only.",
    "Zero agent modification - three lines of code wrap any existing agent framework.",
  ];
  engTexts.forEach((text, index) => {
    addText(slide, text, index * engW + 16, y + 34, engW - 32, 22, {
      fontPx: 10,
      color: C.text,
      align: "center",
      valign: "mid",
    });
  });

  finalizeSlide(slide);
}

function slide7() {
  const slide = pptx.addSlide();
  addHeaderFooter(slide, "AgentGuard | AI Integration and Enhancements", 7, 9);
  let y = BODY_Y;

  addRect(slide, 0, y, W, 236, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "Where And Why AI Is Used - Smart Usage Not Heavy Usage", C.blue);
  const aiRows = [
    ["Azure OpenAI | PII Detection", "Contextual entity detection in legal and healthcare language requires language understanding regex cannot provide. ICD-10 code in a clinical sentence vs. a billing record needs different treatment."],
    ["Azure OpenAI | Risk Scoring", "Four-factor analysis - sensitivity, reversibility, blast radius, policy compliance - requires reasoning about context. A $50,000 transfer from billing-agent is different from the same transfer from scheduling-agent."],
    ["Azure AI Content Safety | Parallel Validation", "Runs on every request in parallel with the pre-filter. When both trigger, both signals are logged independently. Two systems agreeing is stronger evidence than one."],
    ["Azure OpenAI | Agent Persona Simulation", "Each simulated agent generates realistic varied requests using a persona prompt. Routine traffic is genuinely varied - not scripted. The system is tested on novel unpredictable inputs."],
  ];
  aiRows.forEach((row, index) => {
    const rowY = y + 30 + index * 40;
    addText(slide, row[0], 24, rowY, 300, 16, {
      fontPx: 11,
      bold: true,
      color: C.blue,
    });
    addText(slide, row[1], 332, rowY, 912, 26, {
      fontPx: 10,
      color: C.text,
    });
  });
  addRect(slide, 18, y + 192, 1244, 34, { fill: C.lightAmber, line: "FCD7AA" });
  addText(
    slide,
    "What we chose NOT to use AI for: pre-filter matching | policy engine enforcement | canary detection | multi-turn window | reputation scoring. Deterministic code where deterministic code is correct.",
    28,
    y + 201,
    1224,
    16,
    { fontPx: 10, color: C.text, bold: true, align: "center", valign: "mid" }
  );
  y += 236;

  addRect(slide, 0, y, W, 210, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "Mentor Feedback Incorporated - What Changed Between Rounds", C.amber);
  addVerticalDivider(slide, 640, y + 30, 156);
  addText(slide, "ROUND 1 - WHAT MENTOR FEEDBACK WE RECEIVED", 20, y + 34, 600, 16, {
    fontFace: FONT.display,
    fontPx: 11,
    bold: true,
    color: C.amber,
  });
  addText(slide, "Presentation hard to read | not information dense | demo was a human typing into a box", 20, y + 54, 600, 18, {
    fontPx: 10,
    bold: true,
    color: C.text,
  });
  const before = [
    "X Generic demo - prompt input and output with no narrative or story",
    "X Streamlit dashboard looked like a student project - not a product",
    "X No domain-specific protection - general purpose only",
    "X Mock keyword-matching agent - not a real AI making real decisions",
    "X No compliance output - nothing a CISO could actually use",
  ];
  before.forEach((line, index) => {
    addText(slide, line, 20, y + 80 + index * 20, 600, 16, {
      fontPx: 10,
      color: C.text,
    });
  });
  addText(slide, "ROUND 2 - WHAT WE BUILT IN RESPONSE", 660, y + 34, 600, 16, {
    fontFace: FONT.display,
    fontPx: 11,
    bold: true,
    color: C.green,
  });
  const after = [
    "OK Pearson Hardman scenario with cross-matter breach caught in real time",
    "OK FastAPI server with HTML dashboard and live agent simulation",
    "OK Legal privilege mode, HIPAA mode, YAML policy engine, canary tokens, multi-turn detection, persistent reputation",
    "OK Live AI agent with GPT-4o-mini making real decisions",
    "OK PDF compliance report a CISO can submit to a regulator",
  ];
  after.forEach((line, index) => {
    addText(slide, line, 660, y + 58 + index * 22, 590, 18, {
      fontPx: 10,
      color: C.text,
    });
  });
  addText(
    slide,
    "This is not an iteration. This is a rebuild informed by real feedback, real testing, and 384 real decisions processed.",
    20,
    y + 184,
    1240,
    16,
    { fontPx: 10, bold: true, color: C.blue, align: "center", valign: "mid" }
  );
  y += 210;

  addRect(slide, 0, y, W, 206, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "Live Simulation Evidence", C.green);
  const phW = (W - 48) / 2;
  addPlaceholder(
    slide,
    16,
    y + 30,
    phW,
    108,
    "INSERT SCREENSHOT: Agent simulation - four agents at corners, middleware center, animated lines, live feed panel"
  );
  addPlaceholder(
    slide,
    32 + phW,
    y + 30,
    phW,
    108,
    "INSERT SCREENSHOT: Audit log table - AUTO green and BLOCK red decisions from real simulation run"
  );
  addText(
    slide,
    "Left: Four autonomous agents operating simultaneously at Pearson Hardman with routine green traffic interrupted by scripted red BLOCK events.",
    20,
    y + 148,
    600,
    26,
    { fontPx: 10, color: C.text, align: "center" }
  );
  addText(
    slide,
    "Right: Real Cosmos DB audit records from the simulation showing AUTO and BLOCK outcomes side by side.",
    660,
    y + 148,
    600,
    26,
    { fontPx: 10, color: C.text, align: "center" }
  );
  addText(
    slide,
    "The screenshots are bounded. The evidence below them carries the rest of the density.",
    20,
    y + 188,
    1240,
    12,
    { fontPx: 10, color: C.gray, italic: true, align: "center" }
  );

  finalizeSlide(slide);
}

function slide8() {
  const slide = pptx.addSlide();
  addHeaderFooter(slide, "AgentGuard | Scalability and Future Scope", 8, 9);
  let y = BODY_Y;

  addRect(slide, 0, y, W, 152, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "Market Opportunity", C.blue);
  const marketW = W / 4;
  const marketCards = [
    ["$93.75B", "AI Cybersecurity by 2030 | 24.4% CAGR", "Grand View Research 2024", "Fastest growing security category globally", C.blue],
    ["$10.82B", "Legal AI Software by 2030 | 28.3% CAGR", "MarketsandMarkets 2025", "Harvey AI: $190M ARR - the market is real", C.cyan],
    ["$56.3B", "Healthcare Cybersecurity by 2030 | 18.5% CAGR", "Grand View Research 2023", "Most expensive breach industry 14 years running", C.green],
    ["$7.42M", "Average healthcare breach cost", "IBM 2025", "AgentGuard prevents this at $0.003 per decision", C.red],
  ];
  marketCards.forEach((item, index) => {
    addStatCard(slide, {
      x: index * marketW,
      y: y + 30,
      w: marketW,
      h: 108,
      number: item[0],
      label: item[1],
      source: item[2],
      context: item[3],
      numberColor: item[4],
      fill: index % 2 === 0 ? C.light : C.white,
    });
  });
  addText(
    slide,
    "Combined addressable market across all three verticals exceeds $160B by 2030. AgentGuard addresses all three with one product.",
    20,
    y + 138,
    1240,
    14,
    { fontPx: 10, bold: true, color: C.text, align: "center" }
  );
  y += 152;

  addRect(slide, 0, y, W, 120, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "Go-To-Market Strategy", C.green);
  const phaseW = W / 3;
  const phases = [
    ["PHASE 1 | NOW", "Open SDK | developer adoption | three deployment configs ship with product | target IT directors at law firms and hospitals deploying AI agents | GitHub repository + pip install agentguard"],
    ["PHASE 2 | Q3 2026", "Azure Marketplace listing | AutoGen + Semantic Kernel native integrations | fine-tuned local model for air-gapped hospital deployments"],
    ["PHASE 3 | 2027", "Enterprise custom deployments | custom risk models trained on client data | multi-tenant SaaS | white-glove professional services | Azure partner program"],
  ];
  phases.forEach((phase, index) => {
    addRect(slide, index * phaseW, y + 30, phaseW, 90, {
      fill: index % 2 === 0 ? C.light : C.white,
      line: C.bodyLine,
    });
    addText(slide, phase[0], index * phaseW + 14, y + 38, phaseW - 28, 16, {
      fontFace: FONT.display,
      fontPx: 12,
      bold: true,
      color: C.blue,
      align: "center",
    });
    addText(slide, phase[1], index * phaseW + 14, y + 58, phaseW - 28, 48, {
      fontPx: 10,
      color: C.text,
      align: "center",
    });
  });
  y += 120;

  addRect(slide, 0, y, W, 220, { fill: C.white, line: C.bodyLine });
  const half = W / 2;
  addRect(slide, 0, y, half, 220, { fill: C.white, line: C.bodyLine });
  addRect(slide, half, y, half, 220, { fill: C.white, line: C.bodyLine });
  addSectionBarBox(slide, 0, y, half, "Current Challenges - Honest Limitations", C.red);
  addSectionBarBox(slide, half, y, half, "Scalability Proof", C.blue);
  addVerticalDivider(slide, half, y + 22, 198);
  const challenges = [
    ["Policy Quality", "Guardrail effectiveness depends on YAML correctness", "Mitigation: Three validated configs ship with the product."],
    ["Scale Testing", "Tested at 384 decisions; production load testing not yet complete", "Mitigation: Cosmos DB plus Container Apps were chosen for enterprise scale."],
    ["Human Escalation Routing", "Slack and email alerts are not yet wired", "Mitigation: Cosmos DB record remains the source of truth; Phase 2 closes the loop."],
  ];
  challenges.forEach((item, index) => {
    const baseY = y + 34 + index * 58;
    addText(slide, item[0], 20, baseY, 180, 16, {
      fontPx: 11,
      bold: true,
      color: C.red,
    });
    addText(slide, item[1], 200, baseY, 410, 18, {
      fontPx: 10,
      color: C.text,
    });
    addText(slide, item[2], 20, baseY + 22, 590, 18, {
      fontPx: 10,
      color: C.muted,
      italic: true,
    });
  });
  const proofs = [
    "$0.003 per decision with caching. 10,000 decisions per day = $30. Pre-filter stays at $0 for obvious threats.",
    "Pre-filter handles dangerous patterns in under 1ms at zero API cost and scales horizontally with no bottleneck.",
    "Same codebase serves finance, legal, and healthcare. New domain = one new YAML file. Zero code changes required.",
  ];
  proofs.forEach((text, index) => {
    addText(slide, text, 660, y + 42 + index * 48, 590, 28, {
      fontPx: 10,
      color: C.text,
    });
  });
  addText(slide, "Architecture uses Azure services designed for millions of records and concurrent requests.", 660, y + 188, 590, 14, {
    fontPx: 10,
    color: C.gray,
    italic: true,
    align: "center",
  });
  y += 220;

  addRect(slide, 0, y, W, 92, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "Competitive Moat", C.purple);
  const moatW = W / 4;
  const moats = [
    "Agent Reputation Score | Persistent cross-session trust | No competitor has this",
    "Multi-Turn Detection | Reconnaissance pattern catching | No competitor has this",
    "Canary Tokens | Exfiltration fingerprinting | No competitor has this",
    "Domain YAML Engine | Infinite configurability | No competitor has this",
  ];
  moats.forEach((text, index) => {
    addText(slide, text, index * moatW + 14, y + 34, moatW - 28, 40, {
      fontPx: 10,
      color: C.text,
      align: "center",
    });
  });
  y += 92;

  addRect(slide, 0, y, W, 68, { fill: C.white, line: C.bodyLine });
  addSectionBar(slide, y, "Regulatory Tailwinds", C.amber);
  const regW = W / 3;
  const regs = [
    "EU AI Act - August 2026 enforcement - requires traceable AI decisions. AgentGuard provides this today.",
    "HIPAA Security Rule 2024 amendments explicitly address AI systems handling ePHI. AgentGuard enforces this.",
    "Colorado AI Act - June 2026 - risk management and transparency for high-risk AI. AgentGuard compliance report covers this.",
  ];
  regs.forEach((text, index) => {
    addText(slide, text, index * regW + 14, y + 32, regW - 28, 28, {
      fontPx: 10,
      color: C.text,
      align: "center",
    });
  });

  finalizeSlide(slide);
}

function slide9() {
  const slide = pptx.addSlide();
  addHeaderFooter(slide, "AgentGuard | Closing Vision", 9, 9, { bodyFill: C.dark });
  let y = BODY_Y;

  addRect(slide, 80, y + 12, 1120, 100, { fill: "10182B", line: C.cyan, lineWidth: 1.2 });
  addText(slide, "THE VISION", 100, y + 26, 1080, 14, {
    fontFace: FONT.display,
    fontPx: 10,
    bold: true,
    color: C.cyan,
    charSpace: 1.2,
    align: "center",
  });
  addText(
    slide,
    "AgentGuard is the compliance layer that makes AI agent deployments auditable, accountable, and safe to run in production - without changing a single line of agent code.",
    120,
    y + 48,
    1040,
    46,
    { fontFace: FONT.display, fontPx: 18, bold: true, color: C.white, align: "center", valign: "mid" }
  );
  y += 120;

  addRect(slide, 0, y, W, 180, { fill: C.dark, line: "22304A" });
  const closeW = W / 3;
  const closingCols = [
    ["WHAT EXISTS TODAY", "Production FastAPI server | real REST endpoints | POST /intercept + POST /confirm + GET /status\n\n384 decisions processed | 159 blocked | 225 auto-executed | 425 PII entities masked\n\nLegal + healthcare domain modes | 7 agents | 4 scripted simulation events | PDF compliance reports\n\nThree deployment configs | YAML policy engine | agent reputation persistence"],
    ["WHAT WE ARE BUILDING", "Azure Marketplace listing | AutoGen native integration | Semantic Kernel integration\n\nFine-tuned local model | air-gapped hospital deployments | patient data never leaves network\n\nEnterprise custom risk models trained on client data | multi-tenant SaaS\n\nReal-time alert routing | Slack + email escalation notifications | Phase 2"],
    ["WHY IT MATTERS NOW", "87% of enterprises already have agents - every one is a potential customer\n\nEU AI Act August 2026 | HIPAA AI amendments | Colorado AI Act June 2026\n\n'Show me your guardrails' is now a procurement question, not a nice-to-have\n\nThe compliance layer for AI agents does not exist at scale - AgentGuard is building it"],
  ];
  closingCols.forEach((col, index) => {
    addText(slide, col[0], index * closeW + 18, y + 14, closeW - 36, 16, {
      fontFace: FONT.display,
      fontPx: 11,
      bold: true,
      color: C.white,
      align: "center",
    });
    addText(slide, col[1], index * closeW + 18, y + 40, closeW - 36, 126, {
      fontPx: 10,
      color: "D7E3F4",
      align: "center",
    });
  });
  y += 180;

  addRect(slide, 0, y, W, 176, { fill: C.dark, line: "22304A" });
  addPlaceholder(
    slide,
    100,
    y + 10,
    1080,
    130,
    "INSERT SCREENSHOT: Raw Cosmos DB JSON record - BLOCK decision | agent_id: research-bot-001 | risk_score: 98 | tier: block | cross_matter_access: true | canary_triggered: false | cosmos_logged: true"
  );
  addText(
    slide,
    "This is a real audit record from a real pipeline run. This is what accountability looks like.",
    100,
    y + 148,
    1080,
    18,
    { fontPx: 10, color: C.white, italic: true, align: "center", valign: "mid" }
  );
  y += 176;

  addRect(slide, 0, y, W, 92, { fill: "10182B", line: "22304A" });
  const bottomCols = [
    "384 real decisions | Azure Cosmos DB | not simulated",
    "Auditable. Accountable. Safe. Without changing a single line of agent code.",
    "Sarangan Srinivasan | Krishna Gera | Saanvi Bansal | Teen Bhai Teeno Tabahi | Manipal Institute of Technology",
  ];
  bottomCols.forEach((text, index) => {
    addText(slide, text, index * closeW + 18, y + 26, closeW - 36, 38, {
      fontPx: index === 1 ? 12 : 10,
      bold: index === 1,
      color: C.white,
      align: "center",
      valign: "mid",
    });
  });
  y += 92;

  addRect(slide, 0, y, W, 84, { fill: C.bar, line: C.bar });
  addText(
    slide,
    "Azure OpenAI | Azure Cosmos DB | Azure AI Content Safety | Microsoft Presidio | FastAPI | Azure Container Apps",
    20,
    y + 14,
    1240,
    16,
    { fontPx: 12, color: C.white, align: "center" }
  );
  addText(
    slide,
    "Microsoft AI Unlocked | Track 5: Trustworthy AI | Top 54 Finalist",
    20,
    y + 38,
    1240,
    14,
    { fontPx: 10, color: C.cyan, bold: true, align: "center" }
  );
  addText(slide, "Powered by Microsoft Azure", 20, y + 58, 1240, 12, {
    fontPx: 10,
    color: C.white,
    align: "center",
  });

  finalizeSlide(slide);
}

async function main() {
  ensureDir(path.join(__dirname, "dist"));
  slide1();
  slide2();
  slide3();
  slide4();
  slide5();
  slide6();
  slide7();
  slide8();
  slide9();

  const outputPath = path.join(__dirname, "dist", "AgentGuard_Presentation_v2.pptx");
  await pptx.writeFile({ fileName: outputPath, compression: true });
  console.log(`Wrote ${outputPath}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
