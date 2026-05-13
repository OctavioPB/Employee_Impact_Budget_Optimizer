"""Export helpers for EIBO: CSV, Excel (multi-sheet), and PDF (reportlab).

All functions return bytes suitable for st.download_button().
"""

import io
import logging
from datetime import date
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Serialize a DataFrame to UTF-8 CSV bytes."""
    return df.to_csv(index=False).encode("utf-8")


# ---------------------------------------------------------------------------
# Excel (multi-sheet)
# ---------------------------------------------------------------------------

def tables_to_excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    """Serialize multiple DataFrames into a multi-sheet Excel workbook.

    Args:
        sheets: Ordered dict of sheet_name → DataFrame.

    Returns:
        Raw bytes of the .xlsx file.
    """
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            safe_name = sheet_name[:31]  # Excel sheet name limit
            df.to_excel(writer, sheet_name=safe_name, index=False)
            ws = writer.sheets[safe_name]
            _autofit_columns(ws, df)
    return buf.getvalue()


def _autofit_columns(ws, df: pd.DataFrame, min_width: int = 10, max_width: int = 40) -> None:
    """Approximate column width from content."""
    try:
        for i, col in enumerate(df.columns, 1):
            header_len = len(str(col))
            max_data_len = df[col].astype(str).str.len().max() if len(df) > 0 else 0
            width = min(max(header_len, int(max_data_len or 0), min_width), max_width)
            col_letter = ws.cell(row=1, column=i).column_letter
            ws.column_dimensions[col_letter].width = width + 2
    except Exception:
        pass  # column autofit is cosmetic; never block export


# ---------------------------------------------------------------------------
# PDF (reportlab)
# ---------------------------------------------------------------------------

def generate_pdf_summary(
    org_name: str,
    scenario_id: str,
    total_spend: float,
    total_budget: float,
    n_employees: int,
    avg_impact: float,
    n_nexus: int,
    dept_summary: pd.DataFrame,
    top_impact_employees: Optional[pd.DataFrame] = None,
    warnings: Optional[list[str]] = None,
) -> bytes:
    """Generate an executive summary PDF using reportlab.

    Args:
        org_name: Organization display name.
        scenario_id: Demo scenario identifier (A/B/C) or "real".
        total_spend: Current annual payroll.
        total_budget: Approved annual budget.
        n_employees: Total active headcount.
        avg_impact: Organization-wide average impact score.
        n_nexus: Count of nexus employees.
        dept_summary: Department summary DataFrame.
        top_impact_employees: Top 10 employees by impact score (optional).
        warnings: List of risk/alert strings to include (optional).

    Returns:
        Raw PDF bytes.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
        )
    except ImportError:
        return _pdf_fallback_text(org_name, total_spend, n_employees, avg_impact)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
    )

    styles = getSampleStyleSheet()
    navy = colors.HexColor("#003366")
    gold  = colors.HexColor("#C8982A")
    light = colors.HexColor("#F4F6F9")
    gray  = colors.HexColor("#6B7280")
    green = colors.HexColor("#27B97C")
    orange = colors.HexColor("#F07020")

    h1 = ParagraphStyle("h1", fontSize=22, fontName="Helvetica-Bold",
                         textColor=navy, spaceAfter=6, leading=26)
    h2 = ParagraphStyle("h2", fontSize=13, fontName="Helvetica-Bold",
                         textColor=navy, spaceBefore=14, spaceAfter=4)
    body = ParagraphStyle("body", fontSize=9, fontName="Helvetica",
                           textColor=colors.HexColor("#374151"), leading=14)
    small = ParagraphStyle("small", fontSize=8, fontName="Helvetica",
                            textColor=gray, leading=12)
    warn_style = ParagraphStyle("warn", fontSize=9, fontName="Helvetica",
                                 textColor=orange, leading=13)

    today = date.today().strftime("%B %d, %Y")
    variance = (total_spend - total_budget) / total_budget * 100 if total_budget else 0.0
    variance_sign = "+" if variance >= 0 else ""

    elements = [
        Paragraph("OPB · Employee Impact & Budget Optimizer", small),
        Paragraph(f"Executive Summary — {today}", small),
        Spacer(1, 0.4 * cm),
        HRFlowable(width="100%", thickness=2, color=gold),
        Spacer(1, 0.3 * cm),

        Paragraph(f"Workforce Summary: {org_name}", h1),
        Paragraph(f"Scenario {scenario_id.upper()} · Generated {today}", small),
        Spacer(1, 0.5 * cm),

        Paragraph("Key Performance Indicators", h2),
    ]

    kpi_data = [
        ["Metric", "Value"],
        ["Total Headcount", f"{n_employees:,}"],
        ["Annual Payroll (Actual)", f"${total_spend/1_000_000:.2f}M"],
        ["Annual Budget (Approved)", f"${total_budget/1_000_000:.2f}M"],
        ["Budget Variance", f"{variance_sign}{variance:.1f}%"],
        ["Avg Impact Score", f"{avg_impact:.1f} / 100"],
        ["Organizational Nexus Employees", f"{n_nexus}"],
    ]
    kpi_table = Table(kpi_data, colWidths=[9 * cm, 5.5 * cm])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), navy),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 8),
        ("FONTSIZE",   (0, 1), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0EAF4")),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
    ]))
    elements += [kpi_table, Spacer(1, 0.6 * cm)]

    if not dept_summary.empty:
        elements.append(Paragraph("Department Overview", h2))
        display_cols = ["department", "headcount", "total_spend", "annual_budget",
                        "budget_variance_pct", "avg_impact"]
        display_cols = [c for c in display_cols if c in dept_summary.columns]
        dept_df = dept_summary[display_cols].copy()

        header_labels = {
            "department": "Department",
            "headcount": "Headcount",
            "total_spend": "Spend ($M)",
            "annual_budget": "Budget ($M)",
            "budget_variance_pct": "Variance %",
            "avg_impact": "Avg Impact",
        }
        dept_df.columns = [header_labels.get(c, c) for c in dept_df.columns]

        if "Spend ($M)" in dept_df.columns:
            dept_df["Spend ($M)"] = (dept_df["Spend ($M)"] / 1_000_000).round(2)
        if "Budget ($M)" in dept_df.columns:
            dept_df["Budget ($M)"] = (dept_df["Budget ($M)"] / 1_000_000).round(2)
        if "Variance %" in dept_df.columns:
            dept_df["Variance %"] = dept_df["Variance %"].round(1).astype(str) + "%"
        if "Avg Impact" in dept_df.columns:
            dept_df["Avg Impact"] = dept_df["Avg Impact"].round(1)

        dept_data = [dept_df.columns.tolist()] + dept_df.values.tolist()
        col_count = len(dept_df.columns)
        col_w = 14.6 / col_count
        dept_table = Table(dept_data, colWidths=[col_w * cm] * col_count)
        dept_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), navy),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E0EAF4")),
            ("LEFTPADDING",  (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING",   (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ]))
        elements += [dept_table, Spacer(1, 0.6 * cm)]

    if top_impact_employees is not None and not top_impact_employees.empty:
        elements.append(Paragraph("Top 10 Employees by Impact Score", h2))
        top10 = top_impact_employees.head(10)
        cols_to_show = [c for c in ["full_name", "role_title", "department",
                                    "impact_score", "total_cost"] if c in top10.columns]
        top10 = top10[cols_to_show].copy()
        top10.columns = [c.replace("_", " ").title() for c in top10.columns]
        if "Total Cost" in top10.columns:
            top10["Total Cost"] = top10["Total Cost"].apply(lambda v: f"${v:,.0f}")
        if "Impact Score" in top10.columns:
            top10["Impact Score"] = top10["Impact Score"].round(1)

        top_data = [top10.columns.tolist()] + top10.values.tolist()
        col_count = len(top10.columns)
        col_w = 14.6 / col_count
        top_table = Table(top_data, colWidths=[col_w * cm] * col_count)
        top_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), navy),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E0EAF4")),
            ("LEFTPADDING",  (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING",   (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ]))
        elements += [top_table, Spacer(1, 0.6 * cm)]

    if warnings:
        elements.append(Paragraph("Risk Warnings", h2))
        for w in warnings:
            elements.append(Paragraph(f"⚠  {w}", warn_style))
        elements.append(Spacer(1, 0.4 * cm))

    elements += [
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E0EAF4")),
        Spacer(1, 0.2 * cm),
        Paragraph(
            "This report was generated by EIBO (Employee Impact & Budget Optimizer). "
            "All recommendations are advisory. Final decisions remain with human leadership.",
            small,
        ),
        Paragraph("OPB · Octavio Pérez Bravo · From pipeline to decision.", small),
    ]

    doc.build(elements)
    return buf.getvalue()


def _pdf_fallback_text(
    org_name: str, total_spend: float, n_employees: int, avg_impact: float
) -> bytes:
    """Plain-text fallback if reportlab is not installed."""
    lines = [
        "EIBO Executive Summary",
        f"Organization: {org_name}",
        f"Headcount: {n_employees}",
        f"Total Spend: ${total_spend/1_000_000:.2f}M",
        f"Avg Impact: {avg_impact:.1f}",
        "",
        "Install reportlab to generate formatted PDF reports.",
    ]
    return "\n".join(lines).encode("utf-8")
