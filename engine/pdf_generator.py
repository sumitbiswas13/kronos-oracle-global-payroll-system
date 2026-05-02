"""
PDF Payslip Generator
Generates a professional, branded payslip PDF for each employee.
Uses reportlab — no external dependencies beyond pip install reportlab.
"""

import os
from datetime import date
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

from engine.payroll_engine import PayrollResult

# ── Brand colors ──────────────────────────────────────────────
PRIMARY     = HexColor("#1a1a2e")   # Dark navy
ACCENT      = HexColor("#c2410c")   # Burnt orange
LIGHT_BG    = HexColor("#f7f5f0")   # Cream
MID_GRAY    = HexColor("#6b7280")   # Muted text
BORDER      = HexColor("#e5e7eb")   # Light border
GREEN       = HexColor("#15803d")   # Net pay highlight
ROW_ALT     = HexColor("#f9fafb")   # Alternating row


class PayslipPDFGenerator:

    def __init__(self, output_dir: str = "output/payslips"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, result: PayrollResult, company_name: str = "Acme Global Corp") -> str:
        """
        Generate a PDF payslip for a payroll result.
        Returns the file path of the generated PDF.
        """
        filename = (
            f"{result.employee_id:04d}_"
            f"{result.employee_name.replace(' ', '_')}_"
            f"{result.pay_period_start.strftime('%Y%m')}.pdf"
        )
        filepath = self.output_dir / filename

        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            leftMargin=15*mm,
            rightMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=15*mm,
        )

        styles = self._build_styles()
        story  = []

        # ── Header ────────────────────────────────────────────
        story += self._build_header(result, company_name, styles)
        story.append(Spacer(1, 5*mm))

        # ── Employee & pay period info ─────────────────────────
        story += self._build_info_block(result, styles)
        story.append(Spacer(1, 5*mm))

        # ── Earnings ──────────────────────────────────────────
        story += self._build_section("Earnings", self._earnings_rows(result), result.currency_code, styles)
        story.append(Spacer(1, 3*mm))

        # ── Pre-tax deductions ────────────────────────────────
        if result.pre_tax_deductions:
            story += self._build_section("Pre-tax deductions", self._pretax_rows(result), result.currency_code, styles)
            story.append(Spacer(1, 3*mm))

        # ── Taxes ─────────────────────────────────────────────
        if result.taxes:
            story += self._build_section("Taxes & statutory contributions", self._tax_rows(result), result.currency_code, styles)
            story.append(Spacer(1, 3*mm))

        # ── Post-tax deductions ───────────────────────────────
        if result.post_tax_deductions:
            story += self._build_section("Post-tax deductions", self._posttax_rows(result), result.currency_code, styles)
            story.append(Spacer(1, 3*mm))

        # ── Net pay summary ───────────────────────────────────
        story += self._build_net_pay(result, styles)
        story.append(Spacer(1, 5*mm))

        # ── Hours summary (hourly employees) ──────────────────
        if result.total_hours > 0 and result.employee_type in ("HOURLY", "PARTTIME"):
            story += self._build_hours_summary(result, styles)
            story.append(Spacer(1, 5*mm))

        # ── Footer ────────────────────────────────────────────
        story += self._build_footer(styles)

        doc.build(story)
        return str(filepath)

    def generate_batch(
        self,
        results: list[PayrollResult],
        company_name: str = "Acme Global Corp",
    ) -> list[str]:
        """Generate PDFs for a list of payroll results."""
        paths = []
        for result in results:
            path = self.generate(result, company_name)
            paths.append(path)
            print(f"  ✅ {result.employee_name:<25} → {Path(path).name}")
        return paths

    # ── Section builders ──────────────────────────────────────

    def _build_header(self, result, company_name, styles):
        header_data = [[
            Paragraph(f'<font color="#ffffff"><b>{company_name}</b></font>', styles["header_company"]),
            Paragraph('<font color="#c2410c"><b>PAYSLIP</b></font>', styles["header_payslip"]),
        ]]
        t = Table(header_data, colWidths=[120*mm, 60*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PRIMARY),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",  (0, 0), (0, -1), 6),
            ("RIGHTPADDING", (1, 0), (1, -1), 6),
        ]))
        return [t]

    def _build_info_block(self, result, styles):
        left = [
            [Paragraph("Employee", styles["label"]), Paragraph(result.employee_name, styles["value_bold"])],
            [Paragraph("Employee ID", styles["label"]), Paragraph(str(result.employee_id).zfill(4), styles["value"])],
            [Paragraph("Employee type", styles["label"]), Paragraph(result.employee_type.title(), styles["value"])],
            [Paragraph("Country", styles["label"]), Paragraph(result.country_code, styles["value"])],
        ]
        right = [
            [Paragraph("Pay period", styles["label"]), Paragraph(f"{result.pay_period_start.strftime('%d %b %Y')} – {result.pay_period_end.strftime('%d %b %Y')}", styles["value_bold"])],
            [Paragraph("Currency", styles["label"]), Paragraph(result.currency_code, styles["value"])],
            [Paragraph("Generated", styles["label"]), Paragraph(date.today().strftime("%d %b %Y"), styles["value"])],
        ]

        tl = Table(left,  colWidths=[35*mm, 55*mm])
        tr = Table(right, colWidths=[35*mm, 55*mm])
        for t in (tl, tr):
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("TOPPADDING",    (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ]))

        outer = Table([[tl, Spacer(5*mm, 1), tr]], colWidths=[90*mm, 5*mm, 90*mm])
        outer.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        return [outer]

    def _build_section(self, title, rows, currency, styles):
        elements = [Paragraph(title.upper(), styles["section_title"]), Spacer(1, 1*mm)]
        col_widths = [120*mm, 60*mm]
        table_data = []
        for i, (desc, amount) in enumerate(rows):
            bg = ROW_ALT if i % 2 == 0 else white
            table_data.append([
                Paragraph(desc, styles["row_desc"]),
                Paragraph(f"{currency} {amount:,.2f}", styles["row_amount"]),
            ])
        t = Table(table_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), ROW_ALT),
            ("ROWBACKGROUNDS",(0, 0), (-1, -1), [ROW_ALT, white]),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (0, -1),  6),
            ("RIGHTPADDING",  (1, 0), (1, -1),  6),
            ("LINEBELOW",     (0, -1), (-1, -1), 0.5, BORDER),
            ("LINEABOVE",     (0, 0),  (-1, 0),  0.5, BORDER),
        ]))
        elements.append(t)
        return elements

    def _build_net_pay(self, result, styles):
        data = [
            [Paragraph("Gross pay",          styles["summary_label"]), Paragraph(f"{result.currency_code} {result.gross_pay:,.2f}",              styles["summary_value"])],
            [Paragraph("Total deductions",   styles["summary_label"]), Paragraph(f"− {result.currency_code} {result.total_pre_tax_deductions + result.total_post_tax_deductions:,.2f}", styles["summary_value_neg"])],
            [Paragraph("Total tax",          styles["summary_label"]), Paragraph(f"− {result.currency_code} {result.total_employee_tax:,.2f}",    styles["summary_value_neg"])],
            [Paragraph("NET PAY",            styles["net_label"]),     Paragraph(f"{result.currency_code} {result.net_pay:,.2f}",                 styles["net_value"])],
        ]
        t = Table(data, colWidths=[120*mm, 60*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 2), LIGHT_BG),
            ("BACKGROUND",    (0, 3), (-1, 3), PRIMARY),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (0, -1),  6),
            ("RIGHTPADDING",  (1, 0), (1, -1),  6),
            ("LINEABOVE",     (0, 3), (-1, 3),  1, ACCENT),
        ]))
        return [t]

    def _build_hours_summary(self, result, styles):
        data = [[
            Paragraph(f"Regular hours: <b>{result.regular_hours:.1f}</b>", styles["hours"]),
            Paragraph(f"Overtime hours: <b>{result.overtime_hours:.1f}</b>", styles["hours"]),
            Paragraph(f"Total hours: <b>{result.total_hours:.1f}</b>", styles["hours"]),
        ]]
        t = Table(data, colWidths=[60*mm, 60*mm, 60*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_BG),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))
        return [t]

    def _build_footer(self, styles):
        text = "This payslip is computer generated and does not require a signature. " \
               "Please contact HR if you have any queries regarding this document."
        return [
            HRFlowable(width="100%", thickness=0.5, color=BORDER),
            Spacer(1, 2*mm),
            Paragraph(text, styles["footer"]),
        ]

    # ── Row data helpers ──────────────────────────────────────

    def _earnings_rows(self, result):
        rows = [(e.description, e.amount) for e in result.earnings]
        rows.append(("Gross pay", result.gross_pay))
        return rows

    def _pretax_rows(self, result):
        rows = [(d.description, d.amount) for d in result.pre_tax_deductions]
        rows.append(("Taxable income", result.taxable_income))
        return rows

    def _tax_rows(self, result):
        rows = [(t.description, t.employee_amount) for t in result.taxes]
        rows.append(("Total tax", result.total_employee_tax))
        return rows

    def _posttax_rows(self, result):
        rows = [(d.description, d.amount) for d in result.post_tax_deductions]
        rows.append(("Total post-tax deductions", result.total_post_tax_deductions))
        return rows

    # ── Styles ────────────────────────────────────────────────

    def _build_styles(self):
        base = getSampleStyleSheet()
        def s(name, **kwargs):
            return ParagraphStyle(name, parent=base["Normal"], **kwargs)

        return {
            "header_company": s("hc", fontSize=13, textColor=white, fontName="Helvetica-Bold"),
            "header_payslip": s("hp", fontSize=16, textColor=ACCENT, fontName="Helvetica-Bold", alignment=TA_RIGHT),
            "section_title":  s("st", fontSize=8,  textColor=ACCENT, fontName="Helvetica-Bold", spaceBefore=2, spaceAfter=1),
            "label":          s("lb", fontSize=8,  textColor=MID_GRAY),
            "value":          s("vl", fontSize=9,  textColor=PRIMARY),
            "value_bold":     s("vb", fontSize=9,  textColor=PRIMARY, fontName="Helvetica-Bold"),
            "row_desc":       s("rd", fontSize=9,  textColor=PRIMARY),
            "row_amount":     s("ra", fontSize=9,  textColor=PRIMARY, alignment=TA_RIGHT),
            "summary_label":  s("sl", fontSize=9,  textColor=MID_GRAY),
            "summary_value":  s("sv", fontSize=9,  textColor=PRIMARY, alignment=TA_RIGHT),
            "summary_value_neg": s("sn", fontSize=9, textColor=ACCENT, alignment=TA_RIGHT),
            "net_label":      s("nl", fontSize=11, textColor=white, fontName="Helvetica-Bold"),
            "net_value":      s("nv", fontSize=11, textColor=ACCENT, fontName="Helvetica-Bold", alignment=TA_RIGHT),
            "hours":          s("hr", fontSize=8,  textColor=MID_GRAY),
            "footer":         s("ft", fontSize=7,  textColor=MID_GRAY, alignment=TA_CENTER),
        }
