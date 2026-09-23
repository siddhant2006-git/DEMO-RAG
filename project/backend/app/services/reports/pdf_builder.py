import io
from dataclasses import dataclass, field
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.risk.scorer import RiskAssessment
from app.services.rules.engine import FindingResult

_STATUS_COLORS = {
    "PASS": colors.HexColor("#059669"),
    "FAIL": colors.HexColor("#dc2626"),
    "NEEDS_REVIEW": colors.HexColor("#d97706"),
}


@dataclass
class EvidenceRef:
    document_filename: str
    document_sha256: str
    page_number: int
    snippet: str


@dataclass
class ReportContext:
    tender_title: str
    tender_reference_no: str | None
    vendor_name: str
    generated_by: str
    findings: list[FindingResult]
    risk: RiskAssessment
    evidence_by_rule_id: dict[str, EvidenceRef] = field(default_factory=dict)
    document_hashes: dict[str, str] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.utcnow)
    # Which rule pack (and engine build) produced these findings, so a
    # report filed today stays distinguishable from a re-run under a
    # later-edited pack — see Finding.rule_pack_* / ENGINE_VERSION.
    rule_pack_name: str | None = None
    rule_pack_version: int | None = None
    rule_pack_sha256: str | None = None
    engine_version: str | None = None


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("SmallGrey", parent=styles["Normal"], fontSize=8, textColor=colors.grey))
    styles.add(ParagraphStyle("CellText", parent=styles["Normal"], fontSize=8, leading=10))
    return styles


def build_report_pdf(ctx: ReportContext) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        title=f"TenderGuard Compliance Report — {ctx.tender_title}",
    )
    styles = _styles()
    story = []

    # --- Header ---
    story.append(Paragraph("TenderGuard Compliance Report", styles["Title"]))
    story.append(Paragraph(f"Tender: {ctx.tender_title}", styles["Heading2"]))
    if ctx.tender_reference_no:
        story.append(Paragraph(f"Reference No: {ctx.tender_reference_no}", styles["Normal"]))
    story.append(Paragraph(f"Vendor: {ctx.vendor_name}", styles["Normal"]))
    story.append(
        Paragraph(
            f"Generated: {ctx.generated_at.strftime('%Y-%m-%d %H:%M UTC')} by {ctx.generated_by}",
            styles["SmallGrey"],
        )
    )
    if ctx.document_hashes:
        hash_lines = "<br/>".join(f"{k}: {v}" for k, v in ctx.document_hashes.items())
        story.append(Paragraph(f"Document hashes (SHA-256):<br/>{hash_lines}", styles["SmallGrey"]))
    if ctx.rule_pack_name:
        pack_sha_short = f"{ctx.rule_pack_sha256[:16]}…" if ctx.rule_pack_sha256 else "unknown"
        story.append(
            Paragraph(
                f"Rule pack: {ctx.rule_pack_name} v{ctx.rule_pack_version} (sha256 {pack_sha_short}) · "
                f"Engine: {ctx.engine_version}",
                styles["SmallGrey"],
            )
        )
    story.append(Spacer(1, 0.6 * cm))

    # --- Summary ---
    story.append(Paragraph("Summary", styles["Heading2"]))
    summary_rows = [
        ["Risk score", f"{ctx.risk.score:.1f} / 100", "Band", ctx.risk.band],
        ["PASS", str(ctx.risk.pass_count), "FAIL", str(ctx.risk.fail_count)],
        ["NEEDS REVIEW", str(ctx.risk.needs_review_count), "Total criteria", str(len(ctx.findings))],
    ]
    summary_table = Table(summary_rows, colWidths=[3.5 * cm, 3.5 * cm, 3.5 * cm, 3.5 * cm])
    summary_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f3f4f6")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 0.6 * cm))

    # --- Compliance matrix ---
    story.append(Paragraph("Compliance Matrix", styles["Heading2"]))
    matrix_header = ["Rule", "Requirement", "Status", "Severity", "Reason"]
    matrix_rows = [matrix_header]
    for f in ctx.findings:
        matrix_rows.append(
            [
                Paragraph(f.rule_id, styles["CellText"]),
                Paragraph(f.label, styles["CellText"]),
                f.status,
                f.severity,
                Paragraph(f.reason, styles["CellText"]),
            ]
        )
    matrix_table = Table(matrix_rows, colWidths=[2.2 * cm, 4 * cm, 2.2 * cm, 2 * cm, 6.6 * cm], repeatRows=1)
    style_commands = [
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    for row_index, f in enumerate(ctx.findings, start=1):
        style_commands.append(("TEXTCOLOR", (2, row_index), (2, row_index), _STATUS_COLORS.get(f.status, colors.black)))
    matrix_table.setStyle(TableStyle(style_commands))
    story.append(matrix_table)

    # --- Evidence appendix ---
    non_passing = [f for f in ctx.findings if f.status != "PASS"]
    if non_passing:
        story.append(PageBreak())
        story.append(Paragraph("Evidence Appendix", styles["Heading2"]))
        story.append(
            Paragraph(
                "Every FAIL and NEEDS-REVIEW finding, traced to its source page and snippet.",
                styles["SmallGrey"],
            )
        )
        story.append(Spacer(1, 0.4 * cm))

        for f in non_passing:
            block = [Paragraph(f"{f.rule_id} — {f.label} ({f.status})", styles["Heading3"])]
            block.append(Paragraph(f.reason, styles["Normal"]))

            evidence = ctx.evidence_by_rule_id.get(f.rule_id)
            if evidence:
                block.append(
                    Paragraph(
                        f"Source: {evidence.document_filename}, page {evidence.page_number} "
                        f"(sha256 {evidence.document_sha256[:12]}…)",
                        styles["SmallGrey"],
                    )
                )
                block.append(Paragraph(f"“{evidence.snippet}”", styles["CellText"]))
            else:
                block.append(Paragraph("No source evidence recorded for this finding.", styles["SmallGrey"]))

            block.append(Spacer(1, 0.4 * cm))
            story.append(KeepTogether(block))

    doc.build(story)
    return buffer.getvalue()
