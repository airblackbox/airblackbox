"""
AIR Blackbox — PDF Compliance Report Generator
Converts a compliance evidence bundle into a professional PDF report.

Usage (from CLI):
    air-blackbox export --pdf
    air-blackbox export --pdf --output report.pdf
    air-blackbox comply --scan . -v --pdf
"""

from datetime import datetime

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer,
        Table, TableStyle, HRFlowable, PageBreak
    )
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

# ── Brand colors ───────────────────────────────────────────────
_NAVY   = "#0f172a"
_ACCENT = "#00d4aa"
_GREEN  = "#22c55e"
_RED    = "#ef4444"
_AMBER  = "#f59e0b"
_DIM    = "#888888"
_LIGHT  = "#f8fafc"
_BORDER = "#e2e8f0"


def _c(hex_str):
    """Convert hex string to ReportLab color."""
    from reportlab.lib import colors as _colors
    return _colors.HexColor(hex_str)


def generate_pdf(bundle: dict, output_path: str = "AIR_Blackbox_Compliance_Report.pdf"):
    """
    Generate a PDF compliance report from an evidence bundle dict.

    Args:
        bundle: Output from generate_evidence_bundle()
        output_path: Where to save the PDF

    Returns:
        str: Path to generated PDF

    Raises:
        ImportError: If reportlab is not installed
    """
    if not REPORTLAB_OK:
        raise ImportError(
            "reportlab is required for PDF export.\n"
            "Install it: pip install reportlab"
        )

    from reportlab.lib import colors

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        title="AIR Blackbox EU AI Act Compliance Report",
        author="AIR Blackbox",
    )

    styles = getSampleStyleSheet()
    story  = []

    # ── Style definitions ──────────────────────────────────────
    title_s = ParagraphStyle("AirTitle", parent=styles["Normal"],
        fontSize=22, fontName="Helvetica-Bold",
        textColor=_c(_NAVY), spaceAfter=4)

    sub_s = ParagraphStyle("AirSub", parent=styles["Normal"],
        fontSize=11, fontName="Helvetica",
        textColor=_c(_DIM), spaceAfter=14)

    section_s = ParagraphStyle("AirSection", parent=styles["Normal"],
        fontSize=12, fontName="Helvetica-Bold",
        textColor=_c(_NAVY), spaceBefore=14, spaceAfter=6)

    body_s = ParagraphStyle("AirBody", parent=styles["Normal"],
        fontSize=8.5, fontName="Helvetica",
        textColor=_c("#333333"), leading=13)

    footer_s = ParagraphStyle("AirFooter", parent=styles["Normal"],
        fontSize=7.5, fontName="Helvetica",
        textColor=_c(_DIM), alignment=TA_CENTER)

    # ── Extract data from bundle ───────────────────────────────
    meta      = bundle.get("air_blackbox_evidence_bundle", {})
    gw        = bundle.get("gateway", {})
    comp      = bundle.get("compliance", {})
    summary   = comp.get("summary", {})
    articles  = comp.get("results", [])
    audit     = bundle.get("audit_trail", {})
    scan_meta = bundle.get("scan_metadata", {})

    generated_at = meta.get("generated_at", datetime.utcnow().isoformat() + "Z")
    scan_path    = scan_meta.get("path", ".")
    file_count   = scan_meta.get("files_scanned", "—")
    version      = meta.get("generator", "air-blackbox")

    # ── Header ─────────────────────────────────────────────────
    story.append(Paragraph("AIR Blackbox", title_s))
    story.append(Paragraph("EU AI Act Compliance Report", sub_s))
    story.append(HRFlowable(width="100%", thickness=1, color=_c(_BORDER)))
    story.append(Spacer(1, 8))

    # Meta table
    try:
        date_str = datetime.fromisoformat(generated_at.replace("Z", "")).strftime("%B %d, %Y %H:%M UTC")
    except Exception:
        date_str = generated_at

    meta_rows = [
        ["Project / Path",  str(scan_path)],
        ["Scan Date",       date_str],
        ["Files Scanned",   str(file_count)],
        ["Detection",       "95% automated (AUTO + HYBRID + MANUAL)"],
        ["Generator",       version],
        ["Gateway",         "Reachable" if gw.get("reachable") else "Not reachable"],
    ]
    meta_tbl = Table(meta_rows, colWidths=[1.4 * inch, 5.6 * inch])
    meta_tbl.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",  (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",  (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (0, -1),  _c("#555555")),
        ("TEXTCOLOR", (1, 0), (1, -1),  _c(_NAVY)),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 14))

    # ── Scorecard ───────────────────────────────────────────────
    passing  = summary.get("passing",  0)
    warnings = summary.get("warnings", 0)
    failing  = summary.get("failing",  0)
    total    = summary.get("total_checks", passing + warnings + failing)

    story.append(Paragraph("Compliance Score", section_s))

    score_data = [
        [f"{passing} PASSING", f"{warnings} WARNINGS", f"{failing} FAILING", f"{total} TOTAL"],
    ]
    score_tbl = Table(score_data, colWidths=[1.75 * inch] * 4)
    score_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), _c(_GREEN)),
        ("BACKGROUND", (1, 0), (1, 0), _c(_AMBER)),
        ("BACKGROUND", (2, 0), (2, 0), _c(_RED)),
        ("BACKGROUND", (3, 0), (3, 0), _c(_NAVY)),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 14),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("GRID", (0, 0), (-1, -1), 0.5, _c(_BORDER)),
    ]))
    story.append(score_tbl)
    story.append(Spacer(1, 16))

    # ── Per-article tables ──────────────────────────────────────
    ARTICLE_LABELS = {
        9:  "Article 9 — Risk Management",
        10: "Article 10 — Data Governance",
        11: "Article 11 — Technical Documentation",
        12: "Article 12 — Record-Keeping",
        14: "Article 14 — Human Oversight",
        15: "Article 15 — Accuracy, Robustness & Cybersecurity",
    }

    def status_label(s):
        return {"pass": "✓ PASS", "fail": "✗ FAIL", "warn": "⚠ WARN"}.get(s, s.upper())

    def status_color(s):
        return {"pass": _c(_GREEN), "fail": _c(_RED), "warn": _c(_AMBER)}.get(s, _c(_DIM))

    for art in articles:
        art_num   = art.get("article", "")
        art_title = ARTICLE_LABELS.get(art_num, f"Article {art_num}")
        checks    = art.get("checks", [])

        story.append(Paragraph(art_title, section_s))

        rows = [["Status", "Check", "Type", "Evidence / Fix"]]
        for chk in checks:
            rows.append([
                status_label(chk.get("status", "")),
                chk.get("name", ""),
                chk.get("detection_type", "AUTO"),
                chk.get("evidence", "") or chk.get("fix", ""),
            ])

        col_w = [0.65 * inch, 1.75 * inch, 0.6 * inch, 4.0 * inch]
        tbl = Table(rows, colWidths=col_w, repeatRows=1)

        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), _c(_NAVY)),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("FONTNAME",   (0, 1), (-1, -1), "Helvetica"),
            ("VALIGN",     (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.4, _c(_BORDER)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _c(_LIGHT)]),
        ]
        for i, chk in enumerate(checks, 1):
            c = status_color(chk.get("status", ""))
            style_cmds += [
                ("TEXTCOLOR", (0, i), (0, i), c),
                ("FONTNAME",  (0, i), (0, i), "Helvetica-Bold"),
            ]

        tbl.setStyle(TableStyle(style_cmds))
        story.append(tbl)
        story.append(Spacer(1, 8))

    # ── Audit trail summary ─────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=_c(_BORDER)))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Audit Trail Summary", section_s))

    audit_rows = [
        ["Total Records",  str(audit.get("total_records", 0))],
        ["Total Tokens",   str(audit.get("total_tokens", 0))],
        ["Models Active",  ", ".join(audit.get("models", {}).keys()) or "—"],
        ["PII Alerts",     str(audit.get("pii_alerts", 0))],
        ["Chain Verified", "Yes" if audit.get("chain_valid") else "No signing key set"],
    ]
    audit_tbl = Table(audit_rows, colWidths=[1.4 * inch, 5.6 * inch])
    audit_tbl.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",  (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",  (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (0, -1), _c("#555555")),
        ("TEXTCOLOR", (1, 0), (1, -1), _c(_NAVY)),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(audit_tbl)
    story.append(Spacer(1, 16))

    # ── Footer ──────────────────────────────────────────────────
    story.append(Paragraph(
        f"Generated by AIR Blackbox — airblackbox.ai — Apache 2.0 Open Source — {date_str}",
        footer_s
    ))

    doc.build(story)
    return output_path
