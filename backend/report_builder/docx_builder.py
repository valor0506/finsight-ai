from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from datetime import datetime
import io


# ── Brand colours ──────────────────────────────────────────────
DARK_BG    = "0D1117"   # near-black header
ACCENT     = "00C896"   # emerald green
SUBACCENT  = "1A73E8"   # blue for links / sub-headings
LIGHT_GREY = "F4F6F9"   # table row alternate
MID_GREY   = "6B7280"   # caption / meta text
WHITE      = "FFFFFF"


# ── Helpers ────────────────────────────────────────────────────

def _set_cell_bg(cell, hex_color: str):
    """Fill a table cell with a solid background colour."""
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex_color)
    tcPr.append(shd)


def _add_run(para, text: str, bold=False, italic=False,
             size_pt=11, color=None, font="Calibri"):
    run = para.add_run(text)
    run.bold   = bold
    run.italic = italic
    run.font.name = font
    run.font.size = Pt(size_pt)
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    return run


def _add_divider(doc, color=ACCENT, thickness=8):
    """Thin coloured rule between sections."""
    p   = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pb  = OxmlElement("w:pBdr")
    bot = OxmlElement("w:bottom")
    bot.set(qn("w:val"),   "single")
    bot.set(qn("w:sz"),    str(thickness))
    bot.set(qn("w:space"), "1")
    bot.set(qn("w:color"), color)
    pb.append(bot)
    pPr.append(pb)
    p.paragraph_format.space_after  = Pt(4)
    p.paragraph_format.space_before = Pt(4)
    return p


def _kv_table(doc, rows: list[tuple], col_widths=(5.5, 4.0)):
    """Two-column key-value table with alternating row shading."""
    table = doc.add_table(rows=len(rows), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    for i, (key, val) in enumerate(rows):
        row   = table.rows[i]
        bg    = LIGHT_GREY if i % 2 == 0 else WHITE
        left  = row.cells[0]
        right = row.cells[1]
        _set_cell_bg(left,  bg)
        _set_cell_bg(right, bg)
        # widths
        left.width  = Inches(col_widths[0])
        right.width = Inches(col_widths[1])
        kp = left.paragraphs[0]
        _add_run(kp, str(key), bold=True, size_pt=10, color="374151")
        vp = right.paragraphs[0]
        _add_run(vp, str(val) if val is not None else "N/A", size_pt=10)
    doc.add_paragraph()   # breathing room after table


def _section_heading(doc, title: str):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after  = Pt(2)
    _add_run(p, f"  {title}", bold=True, size_pt=13,
             color=WHITE, font="Calibri")
    # green left bar via cell shading trick — use a 1-cell table instead
    # (paragraph shading not reliably supported in python-docx)
    # ↑ actually we shade via paragraph background using XML
    pPr  = p._p.get_or_add_pPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  "1B2A3B")
    pPr.append(shd)
    return p


def _parse_analysis_text(doc, text: str):
    """
    Render Gemini markdown-ish output into docx paragraphs.
    Handles: # headings, ## headings, **bold**, plain paragraphs.
    """
    for line in text.splitlines():
        line = line.strip()
        if not line:
            doc.add_paragraph()
            continue

        if line.startswith("## "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            _add_run(p, line[3:], bold=True, size_pt=12, color=SUBACCENT)

        elif line.startswith("# "):
            _section_heading(doc, line[2:])

        elif line.startswith("- ") or line.startswith("* "):
            p = doc.add_paragraph(style="List Bullet")
            _add_run(p, line[2:], size_pt=10.5)

        else:
            # inline **bold** handling
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(4)
            parts = line.split("**")
            for idx, part in enumerate(parts):
                if part:
                    _add_run(p, part, bold=(idx % 2 == 1), size_pt=10.5)


# ── Cover block ────────────────────────────────────────────────

def _build_cover(doc, symbol: str, data: dict):
    # Dark header paragraph
    header_p = doc.add_paragraph()
    header_p.paragraph_format.space_before = Pt(0)
    header_p.paragraph_format.space_after  = Pt(0)
    pPr = header_p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  DARK_BG)
    pPr.append(shd)
    _add_run(header_p, f"FinSight AI  |  {symbol} Intelligence Report",
             bold=True, size_pt=20, color=ACCENT, font="Calibri")

    sub_p = doc.add_paragraph()
    pPr2  = sub_p._p.get_or_add_pPr()
    shd2  = OxmlElement("w:shd")
    shd2.set(qn("w:val"),   "clear")
    shd2.set(qn("w:color"), "auto")
    shd2.set(qn("w:fill"),  DARK_BG)
    pPr2.append(shd2)
    ts = datetime.utcnow().strftime("%d %b %Y, %H:%M UTC")
    _add_run(sub_p,
             f"Generated: {ts}  |  Powered by Gemini 1.5 Flash  |  Data: yFinance + FRED + NewsAPI",
             size_pt=9, color=MID_GREY)

    doc.add_paragraph()   # spacer


def _build_snapshot_table(doc, symbol: str, data: dict, macro: dict):
    _section_heading(doc, "Market Snapshot")
    doc.add_paragraph()

    price    = data.get("current_price")
    currency = data.get("currency", "USD")
    rsi      = data.get("rsi_14")
    sma20    = data.get("sma_20")
    sma50    = data.get("sma_50")
    hi52     = data.get("week_52_high")
    lo52     = data.get("week_52_low")
    pct_hi   = data.get("pct_from_52w_high")
    dxy      = macro.get("DXY", {}).get("value")
    us10y    = macro.get("US_10Y_YIELD", {}).get("value")
    gs_ratio = macro.get("GOLD_SILVER_RATIO", {}).get("value")
    usdinr   = macro.get("USDINR", {}).get("value")

    rows = [
        ("Current Price",         f"{price} {currency}" if price else "N/A"),
        ("52-Week High",          f"{hi52} {currency}" if hi52 else "N/A"),
        ("52-Week Low",           f"{lo52} {currency}" if lo52 else "N/A"),
        ("% from 52W High",       f"{pct_hi}%" if pct_hi is not None else "N/A"),
        ("RSI-14",                str(rsi) if rsi else "N/A"),
        ("SMA-20",                str(sma20) if sma20 else "N/A"),
        ("SMA-50",                str(sma50) if sma50 else "N/A"),
        ("── Macro Context ──",   ""),
        ("DXY (USD Index)",       str(dxy) if dxy else "N/A"),
        ("US 10Y Yield",          f"{us10y}%" if us10y else "N/A"),
        ("Gold-Silver Ratio",     str(gs_ratio) if gs_ratio else "N/A"),
        ("USD/INR",               str(usdinr) if usdinr else "N/A"),
    ]
    _kv_table(doc, rows)


# ── Main public function ────────────────────────────────────────

def build_commodity_report(
    symbol: str,
    data: dict,
    analysis_text: str,
    macro: dict,
) -> bytes:
    """
    Build a commodity intelligence report DOCX.

    Args:
        symbol:        e.g. "SILVER"
        data:          output of get_commodity_data()
        analysis_text: plain text from Gemini (llm_analyst)
        macro:         output of get_macro_snapshot()

    Returns:
        bytes: raw .docx file content (write to disk or upload directly)
    """
    doc = Document()

    # ── Page margins (1 inch all sides) ──
    for section in doc.sections:
        section.top_margin    = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin   = Inches(1.1)
        section.right_margin  = Inches(1.1)

    # ── Default paragraph style ──
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    # ── Build sections ──
    _build_cover(doc, symbol, data)
    _add_divider(doc, color=ACCENT)
    _build_snapshot_table(doc, symbol, data, macro)
    _add_divider(doc, color=ACCENT)

    _section_heading(doc, "AI-Generated Analysis")
    doc.add_paragraph()
    _parse_analysis_text(doc, analysis_text)

    _add_divider(doc, color=MID_GREY, thickness=4)

    # ── Footer note ──
    footer_p = doc.add_paragraph()
    footer_p.paragraph_format.space_before = Pt(8)
    _add_run(footer_p,
             "DISCLAIMER: This report is AI-generated for informational purposes only. "
             "Not financial advice. Always consult a qualified financial advisor before making investment decisions.",
             size_pt=8, italic=True, color=MID_GREY)

    # ── Serialise to bytes ──
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()
