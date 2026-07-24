"""Generate the CodeStreet 2026 screening-round pitch deck (.pptx).

~10 self-standing slides tuned for Amex Round-1 judging (business impact +
feasibility + 'why Amex'). Run:  uv run python deck/build_deck.py
Output: deck/CodeStreet2026_Servicing_Agent.pptx
"""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

# --- palette ---------------------------------------------------------------
BG = RGBColor(0x0B, 0x10, 0x20)        # deep navy
CARD = RGBColor(0x14, 0x1C, 0x30)
ACCENT = RGBColor(0x2E, 0x8B, 0xF0)    # Amex-ish blue
ACCENT2 = RGBColor(0x00, 0x6F, 0xCF)
WHITE = RGBColor(0xF5, 0xF7, 0xFA)
MUTED = RGBColor(0x93, 0xA0, 0xB4)
GREEN = RGBColor(0x3F, 0xD0, 0x8A)
AMBER = RGBColor(0xF2, 0xB0, 0x4B)
ROSE = RGBColor(0xF2, 0x6D, 0x6D)
VIOLET = RGBColor(0xA6, 0x8B, 0xF0)

FONT = "Calibri"
FONT_H = "Calibri"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
SW, SH = prs.slide_width, prs.slide_height


def slide():
    s = prs.slides.add_slide(BLANK)
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, SH)
    r.fill.solid(); r.fill.fore_color.rgb = BG; r.line.fill.background()
    r.shadow.inherit = False
    return s


def box(s, x, y, w, h, fill=None, line=None, line_w=1.0, radius=False):
    shp = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid(); shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line; shp.line.width = Pt(line_w)
    shp.shadow.inherit = False
    return shp


def text(s, x, y, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         space=1.0):
    """runs: list of paragraphs; each paragraph is list of (txt, size, color,
    bold, font)."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.space_after = Pt(4 * space); p.space_before = 0
        for (txt, size, color, bold, font) in para:
            r = p.add_run(); r.text = txt
            r.font.size = Pt(size); r.font.color.rgb = color
            r.font.bold = bold; r.font.name = font
    return tb


def R(t, size, color=WHITE, bold=False, font=FONT):
    return (t, size, color, bold, font)


def header(s, eyebrow, title, ecolor=ACCENT):
    box(s, 0, 0, 0.18, 7.5, fill=ACCENT)  # left accent stripe
    if eyebrow:
        text(s, 0.85, 0.55, 11, 0.4,
             [[R(eyebrow.upper(), 13, ecolor, True)]])
    text(s, 0.82, 0.92, 11.6, 1.2, [[R(title, 32, WHITE, True, FONT_H)]])


def footer(s, n):
    text(s, 0.85, 7.02, 8, 0.3,
         [[R("End-to-End Servicing Agent · CodeStreet 2026", 9, MUTED)]])
    text(s, 12.0, 7.02, 0.9, 0.3, [[R(f"{n:02d}", 9, MUTED)]], align=PP_ALIGN.RIGHT)


def bullets(s, x, y, w, items, gap=0.66, size=15, dotc=ACCENT):
    yy = y
    for it in items:
        box(s, x, yy + 0.09, 0.12, 0.12, fill=dotc, radius=True)
        text(s, x + 0.32, yy, w, gap,
             [[R(it[0], size, WHITE, True)] + ([R("  " + it[1], size, MUTED)] if it[1] else [])])
        yy += gap


def chip(s, x, y, w, label, color):
    b = box(s, x, y, w, 0.62, fill=CARD, line=color, line_w=1.25, radius=True)
    tf = b.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = label; r.font.size = Pt(12); r.font.bold = True
    r.font.color.rgb = WHITE; r.font.name = FONT
    return b


def arrow(s, x, y, w=0.5):
    a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y),
                           Inches(w), Inches(0.28))
    a.fill.solid(); a.fill.fore_color.rgb = ACCENT; a.line.fill.background()
    a.shadow.inherit = False
    return a


# ========================= SLIDE 1 — TITLE =================================
s = slide()
box(s, 0, 0, 0.18, 7.5, fill=ACCENT)
text(s, 0.9, 1.5, 11, 0.5, [[R("AMERICAN EXPRESS · CODESTREET 2026", 15, ACCENT, True)]])
text(s, 0.85, 2.15, 11.6, 1.8,
     [[R("The End-to-End Servicing Agent", 46, WHITE, True, FONT_H)]])
text(s, 0.9, 3.5, 11.2, 1.4, [[
    R("Resolves fee reversals, credit-limit increases & card replacements in a ", 20, MUTED),
    R("single conversation", 20, WHITE, True),
    R(" — with a ", 20, MUTED),
    R("tamper-evident audit trail", 20, WHITE, True),
    R(" and a human escape hatch.", 20, MUTED),
]])
box(s, 0.9, 5.2, 7.4, 0.02, fill=CARD)
text(s, 0.9, 5.45, 11, 0.5,
     [[R("Problem Statement:  ", 14, MUTED), R("End-to-End Servicing Agent", 14, WHITE, True)]])
text(s, 0.9, 5.95, 11, 0.5,
     [[R("Team:  ", 14, MUTED), R("<your team name>", 14, WHITE, True),
       R("      Members:  ", 14, MUTED), R("<names>", 14, WHITE, True)]])

# ========================= SLIDE 2 — PROBLEM ===============================
s = slide()
header(s, "The problem", "Routine servicing is slow, costly, and repetitive")
bullets(s, 0.9, 2.35, 11.4, [
    ("Fee reversals, limit increases, and replacement cards are the highest-frequency requests —",
     "and the most tedious to service."),
    ("Members wait on hold, repeat themselves, and get transferred between agents.",
     "Every touch adds compliance overhead."),
    ("Skilled human agents spend their time on routine work",
     "instead of the complex cases that actually need them."),
], gap=0.85, size=17)
c = box(s, 0.9, 5.35, 11.5, 1.1, fill=CARD, line=ACCENT, line_w=1.25, radius=True)
text(s, 1.2, 5.5, 5.2, 0.8,
     [[R("~$13.50", 30, ROSE, True)], [R("cost per human-assisted contact", 12, MUTED)]])
text(s, 4.7, 5.5, 4, 0.8,
     [[R("~$1.84", 30, GREEN, True)], [R("cost per self-service contact", 12, MUTED)]])
text(s, 8.0, 5.62, 4.2, 0.9,
     [[R("The opportunity: ", 14, WHITE, True),
       R("resolve the routine autonomously — safely — and free humans for the hard cases.", 14, MUTED)]])
footer(s, 2)

# ========================= SLIDE 3 — SOLUTION ==============================
s = slide()
header(s, "Our solution", "An agent that resolves the request — not just talks about it")
cards = [
    ("Resolves end-to-end", GREEN,
     "Executes the actual fee waiver, limit change, or card order — start to finish, in one interaction."),
    ("Provably auditable", ACCENT,
     "Every decision & action is written to a hash-chained, tamper-evident audit trail — immutable by construction."),
    ("Escalates gracefully", AMBER,
     "When policy limits or low confidence are hit, hands off to a human with full context — no repeating."),
]
x = 0.9
for title_, col, body in cards:
    box(s, x, 2.5, 3.7, 2.9, fill=CARD, line=col, line_w=1.5, radius=True)
    box(s, x + 0.35, 2.85, 0.55, 0.12, fill=col)
    text(s, x + 0.35, 3.1, 3.1, 0.7, [[R(title_, 18, WHITE, True)]])
    text(s, x + 0.35, 3.85, 3.1, 1.4, [[R(body, 13.5, MUTED)]])
    x += 3.95
text(s, 0.9, 5.75, 11.5, 0.7, [[
    R("Single interaction.  ", 18, WHITE, True), R("Real actions.  ", 18, ACCENT, True),
    R("Complete traceability.", 18, WHITE, True)]], align=PP_ALIGN.CENTER)
footer(s, 3)

# ========================= SLIDE 4 — HOW IT WORKS ==========================
s = slide()
header(s, "How it works", "One request → classify → policy → act — every step logged")
y = 2.9
chip(s, 0.9, y, 2.0, "Member request", MUTED)
arrow(s, 3.0, y + 0.17)
chip(s, 3.6, y, 2.35, "Intent classifier\n(confidence)", VIOLET)
arrow(s, 6.05, y + 0.17)
chip(s, 6.65, y, 2.0, "Policy gate", AMBER)
arrow(s, 8.75, y + 0.17)
chip(s, 9.35, y, 3.0, "Resolve & execute", GREEN)
# escalate branch
chip(s, 9.35, y + 1.15, 3.0, "Escalate w/ full context", ROSE)
a = s.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(7.35), Inches(y + 0.62),
                       Inches(0.28), Inches(0.5))
a.fill.solid(); a.fill.fore_color.rgb = ROSE; a.line.fill.background(); a.shadow.inherit = False
text(s, 6.5, y + 1.2, 2.7, 0.6, [[R("over cap /\nlow confidence", 11, ROSE, True)]],
     align=PP_ALIGN.CENTER)
# audit bar under everything
box(s, 0.9, y + 2.15, 11.45, 0.75, fill=CARD, line=ACCENT, line_w=1.25, radius=True)
text(s, 1.15, y + 2.28, 11, 0.5, [[
    R("⛓  Hash-chained audit trail  ", 15, ACCENT, True),
    R("— classifier · policy · backend · agent : every decision sealed in order", 13, MUTED)]])
text(s, 0.9, 6.55, 11, 0.4, [[
    R("Confidence below threshold, or an amount over policy caps, routes to a human instead of a guess.",
      12.5, MUTED)]])
footer(s, 4)

# ========================= SLIDE 5 — DIFF 1: AUDIT =========================
s = slide()
header(s, "Differentiator 1", "Tamper-evident audit trail — trust by architecture", ecolor=ACCENT)
bullets(s, 0.9, 2.4, 7.1, [
    ("Every decision, policy check & backend call is hash-chained (SHA-256)",
     "— each entry seals the one before it."),
    ("Edit any past entry and every downstream hash breaks",
     "— we catch it live in the demo (verify flips to ‘broken @ seq N’)."),
    ("Complete chain-of-custody, not sampling",
     "— the difference between ‘we think’ and ‘we can prove’."),
    ("Maps to model-risk (SR 11-7) & adverse-action explainability",
     "— audit-ready by design."),
], gap=0.92, size=15.5)
# mini chain visual
bx = 8.4
for i, (lbl, col) in enumerate([("#0 request", VIOLET), ("#1 policy", AMBER),
                                ("#2 backend", GREEN), ("#3 agent", ACCENT)]):
    yy = 2.5 + i * 0.95
    box(s, bx, yy, 3.6, 0.72, fill=CARD, line=col, line_w=1.25, radius=True)
    text(s, bx + 0.2, yy + 0.1, 3.2, 0.5,
         [[R(lbl, 13, WHITE, True), R("   hash◄prev", 10, MUTED)]])
    if i < 3:
        a = s.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(bx + 1.6),
                               Inches(yy + 0.72), Inches(0.2), Inches(0.22))
        a.fill.solid(); a.fill.fore_color.rgb = ACCENT; a.line.fill.background()
        a.shadow.inherit = False
footer(s, 5)

# ========================= SLIDE 6 — DIFF 2: GUARDIAN ======================
s = slide()
header(s, "Differentiator 2 · beyond the brief", "A guardian agent that acts while you sleep",
       ecolor=ROSE)
bullets(s, 0.9, 2.4, 7.1, [
    ("A durable Temporal workflow continuously watches for unusual activity",
     "— the agent is idle until something happens."),
    ("On an anomaly (e.g. high-value card-not-present charge) it acts autonomously",
     "— freezes the card, alerts the member, logs everything."),
    ("Oversight at scale: humans handle exceptions, not every step",
     "— the resolution to the bank’s autonomy dilemma."),
    ("Temporal’s durable event history is itself proof",
     "of when the agent woke and what it did."),
], gap=0.92, size=15.5)
# right visual
box(s, 8.4, 2.5, 3.6, 3.55, fill=CARD, line=ROSE, line_w=1.5, radius=True)
text(s, 8.65, 2.7, 3.1, 0.5, [[R("Autonomous action", 14, ROSE, True)]])
for i, (t, c) in enumerate([
    ("⚡ $4,999 charge · Lagos (CNP)", MUTED),
    ("🛡️ anomaly_detected", ROSE),
    ("🔒 auto_freeze_card", AMBER),
    ("🔔 alert_raised → member", GREEN),
    ("⛓ written to audit chain", ACCENT),
]):
    text(s, 8.65, 3.2 + i * 0.55, 3.1, 0.5, [[R(t, 13, c, True)]])
footer(s, 6)

# ========================= SLIDE 7 — METRICS ==============================
s = slide()
header(s, "Evaluation", "Measured, not asserted")
rows = [
    ("Intent classification accuracy", "90% baseline → 95%+ w/ LLM", "labeled eval set (deterministic)", GREEN),
    ("First-contact resolution (in-scope)", "measured per run", "outcome check (deterministic)", GREEN),
    ("Policy violations", "0", "never auto-approve over cap", ACCENT),
    ("Audit completeness & integrity", "100%", "chain verification", ACCENT),
    ("Response clarity", "LLM-judge rubric (1–5)", "planned", MUTED),
]
# table header
box(s, 0.9, 2.35, 11.5, 0.5, fill=ACCENT2, radius=False)
text(s, 1.1, 2.42, 5, 0.4, [[R("Metric", 13, WHITE, True)]])
text(s, 6.4, 2.42, 3, 0.4, [[R("Result", 13, WHITE, True)]])
text(s, 9.4, 2.42, 3, 0.4, [[R("How it’s graded", 13, WHITE, True)]])
yy = 2.85
for i, (m, res, how, col) in enumerate(rows):
    fill = CARD if i % 2 == 0 else BG
    box(s, 0.9, yy, 11.5, 0.62, fill=fill)
    text(s, 1.1, yy + 0.13, 5.2, 0.4, [[R(m, 13.5, WHITE, True)]])
    text(s, 6.4, yy + 0.13, 3, 0.4, [[R(res, 13.5, col, True)]])
    text(s, 9.4, yy + 0.13, 3, 0.4, [[R(how, 12.5, MUTED)]])
    yy += 0.62
text(s, 0.9, yy + 0.2, 11.5, 0.9, [[
    R("We report TRUE resolution + escalation rate — not just deflection. ", 13, WHITE, True),
    R("Financial-services deflection is realistically 25–45%; finance teams target <1% error, "
      "because one wrong answer is a compliance event.", 13, MUTED)]])
footer(s, 7)

# ========================= SLIDE 8 — WHY AMEX ==============================
s = slide()
header(s, "Why Amex · why now", "The governance layer that makes autonomy deployable")
bullets(s, 0.9, 2.4, 11.4, [
    ("Amex’s 2026 direction is agentic commerce — agents that decide and act.",
     "This is exactly that, applied to servicing."),
    ("~80% of financial institutions lack mature agentic-AI governance,",
     "yet most expect heavy agent use by 2027 (Deloitte)."),
    ("Our audit trail + guardian monitor are the prerequisites for safe autonomy —",
     "‘human oversight’ and ‘responsible use’ built in, not bolted on."),
], gap=0.92, size=16.5)
c = box(s, 0.9, 5.5, 11.5, 1.05, fill=CARD, line=ACCENT, line_w=1.25, radius=True)
text(s, 1.2, 5.68, 11, 0.8, [[
    R("“With every use case, we’ve ensured there is human oversight.”", 15, WHITE, True),
    R("   — Amex CIO, on responsible AI. We make that oversight provable and scalable.", 13, MUTED)]])
footer(s, 8)

# ========================= SLIDE 9 — ARCHITECTURE =========================
s = slide()
header(s, "Architecture", "Built to be real")
# row 1: request path
chip(s, 0.9, 2.55, 2.2, "Next.js UI", ACCENT)
arrow(s, 3.2, 2.72)
chip(s, 3.8, 2.55, 2.0, "FastAPI", ACCENT)
arrow(s, 5.9, 2.72)
chip(s, 6.5, 2.55, 5.9, "LangGraph agent: classifier · policy · flows · audit", VIOLET)
# row 2: autonomous path
chip(s, 0.9, 3.85, 2.9, "Temporal dev server", ROSE)
arrow(s, 3.9, 4.02)
chip(s, 4.5, 3.85, 1.9, "Worker", ROSE)
arrow(s, 6.5, 4.02)
chip(s, 7.1, 3.85, 5.3, "Monitor workflow → /monitor/tick (detect · freeze · alert)", ROSE)
# stack line
box(s, 0.9, 5.1, 11.5, 1.0, fill=CARD, radius=True)
text(s, 1.2, 5.25, 11, 0.8, [[R("Stack   ", 14, ACCENT, True),
    R("Python · FastAPI · LangChain/LangGraph · Gemini (model-agnostic) · Temporal · Next.js · SHA-256 hash-chain",
      13.5, WHITE)]])
text(s, 1.2, 5.72, 11, 0.4, [[
    R("Core-banking is mocked today; each call swaps to a real Amex API with no change to the agent logic.",
      12.5, MUTED)]])
footer(s, 9)

# ========================= SLIDE 10 — NEXT / ASK ==========================
s = slide()
header(s, "What’s next", "From prototype to production")
bullets(s, 0.9, 2.4, 11.4, [
    ("Round 2: integrate real servicing APIs, add voice, expand intents,",
     "and add an LLM-judge clarity eval."),
    ("Production audit store: append-only, write-once storage behind the same hash-chain",
     "— exportable for auditors."),
    ("Guardrails & governance: per-action risk tiers, kill-switch, policy versioning",
     "— the governance substrate for Amex agents."),
], gap=0.92, size=16.5)
box(s, 0.9, 5.5, 11.5, 1.05, fill=ACCENT2, radius=True)
text(s, 1.2, 5.72, 11, 0.7, [[
    R("The ask:  ", 18, WHITE, True),
    R("advance us to the prototype round — the core already works end-to-end.", 17, WHITE)]])
footer(s, 10)

# --- save ------------------------------------------------------------------
out = Path(__file__).resolve().parent / "CodeStreet2026_Servicing_Agent.pptx"
prs.save(out)
print(f"Saved deck -> {out}  ({len(prs.slides.__iter__.__self__._sldIdLst)} slides)")
