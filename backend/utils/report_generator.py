"""PDF report generation using ReportLab."""
from io import BytesIO
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from models.contract import AnalysisResult, RiskSeverity, ScoredClause

SEVERITY_COLORS = {
    RiskSeverity.CRITICAL: colors.HexColor("#DC2626"),
    RiskSeverity.HIGH: colors.HexColor("#EA580C"),
    RiskSeverity.MEDIUM: colors.HexColor("#D97706"),
    RiskSeverity.LOW: colors.HexColor("#16A34A"),
}

SEVERITY_HEX = {
    RiskSeverity.CRITICAL: "#DC2626",
    RiskSeverity.HIGH: "#EA580C",
    RiskSeverity.MEDIUM: "#D97706",
    RiskSeverity.LOW: "#16A34A",
}


def _build_cover_page(result: AnalysisResult, styles: dict) -> List:
    """Build the cover page elements."""
    color_hex = SEVERITY_HEX.get(result.overall_severity, "#000000")
    story = [
        Spacer(1, 3 * cm),
        Paragraph("LexGuard Contract Risk Report", styles["Title"]),
        Spacer(1, 0.5 * cm),
        Paragraph(f"Contract: {result.filename}", styles["Heading2"]),
        Paragraph(
            f'<font color="{color_hex}">Overall Risk Score: {result.overall_risk_score}/100</font>',
            styles["Heading2"],
        ),
        Paragraph(
            f'<font color="{color_hex}">Severity: {result.overall_severity.value}</font>',
            styles["Heading2"],
        ),
        Paragraph(f"Analysis ID: {result.analysis_id}", styles["Normal"]),
        Paragraph(f"Date: {result.created_at[:10]}", styles["Normal"]),
        PageBreak(),
    ]
    return story


def _build_executive_summary(result: AnalysisResult, styles: dict) -> List:
    """Build the executive summary section."""
    critical = sorted(
        [
            c
            for c in result.clauses
            if c.severity in (RiskSeverity.CRITICAL, RiskSeverity.HIGH)
        ],
        key=lambda x: x.risk_score,
        reverse=True,
    )[:3]

    story = [
        Paragraph("Executive Summary", styles["Heading1"]),
        Paragraph(result.summary, styles["Normal"]),
        Spacer(1, 0.5 * cm),
        Paragraph("Top Critical Risks:", styles["Heading2"]),
    ]

    if critical:
        for clause in critical:
            color_hex = SEVERITY_HEX.get(clause.severity, "#000000")
            story.append(
                Paragraph(
                    f'<font color="{color_hex}">• [{clause.severity.value}] {clause.clause_type}:</font> {clause.explanation}',
                    styles["Normal"],
                )
            )
    else:
        story.append(
            Paragraph("No critical or high risk clauses detected.", styles["Normal"])
        )

    story.append(PageBreak())
    return story


def _build_metadata_section(result: AnalysisResult, styles: dict) -> List:
    """Build the contract metadata section."""
    meta = result.metadata
    story = [
        Paragraph("Contract Metadata", styles["Heading1"]),
        Paragraph(f"Contract Type: {meta.contract_type}", styles["Normal"]),
        Paragraph(f"Parties: {', '.join(meta.parties) if meta.parties else 'Not specified'}", styles["Normal"]),
        Paragraph(f"Effective Date: {meta.effective_date or 'Not specified'}", styles["Normal"]),
        Paragraph(f"Governing Law: {meta.governing_law or 'Not specified'}", styles["Normal"]),
        Paragraph(f"Duration: {meta.contract_duration or 'Not specified'}", styles["Normal"]),
        Spacer(1, 0.5 * cm),
    ]
    return story


def _build_clause_section(clause: ScoredClause, styles: dict) -> List:
    """Build analysis section for a single clause."""
    color_hex = SEVERITY_HEX.get(clause.severity, "#000000")
    story = [
        Paragraph(
            f'<font color="{color_hex}">[{clause.severity.value}] {clause.clause_type}</font>',
            styles["Heading3"],
        ),
        Paragraph(
            f"Risk Score: {clause.risk_score}/10 | Category: {clause.risk_category.value}",
            styles["Normal"],
        ),
        Paragraph(f"<b>Explanation:</b> {clause.explanation}", styles["Normal"]),
    ]

    if clause.negotiation_tip:
        story.append(
            Paragraph(
                f"<b>Negotiation Tip:</b> {clause.negotiation_tip}", styles["Normal"]
            )
        )

    if clause.worst_case_scenario:
        story.append(
            Paragraph(
                f"<b>Worst Case:</b> {clause.worst_case_scenario}", styles["Normal"]
            )
        )

    story.append(Spacer(1, 0.5 * cm))
    return story


def generate_pdf_report(result: AnalysisResult) -> bytes:
    """Generate a PDF risk report for a contract analysis result.

    Args:
        result: The completed AnalysisResult to render as PDF.

    Returns:
        PDF file bytes ready for download.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.extend(_build_cover_page(result, styles))
    story.extend(_build_executive_summary(result, styles))
    story.extend(_build_metadata_section(result, styles))

    story.append(Paragraph("Clause-by-Clause Analysis", styles["Heading1"]))
    for clause in result.clauses:
        story.extend(_build_clause_section(clause, styles))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
