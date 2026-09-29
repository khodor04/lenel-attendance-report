from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas as rl_canvas
from datetime import date, datetime
from pathlib import Path
from typing import List
from attendance import AttendanceRecord


class _PageNumCanvas(rl_canvas.Canvas):
    """Draws 'Page X of Y' footer on every page."""

    def __init__(self, *args, **kwargs):
        rl_canvas.Canvas.__init__(self, *args, **kwargs)
        self._pages = []

    def showPage(self):
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._pages)
        for page in self._pages:
            self.__dict__.update(page)
            self._draw_page_number(page_count)
            rl_canvas.Canvas.showPage(self)
        rl_canvas.Canvas.save(self)

    def _draw_page_number(self, total):
        w, h = self._pagesize
        self.setFont('Helvetica', 7)
        self.setFillColor(HexColor('#888888'))
        text = f"Page {self._pageNumber} of {total}"
        self.drawRightString(w - 1 * cm, 0.7 * cm, text)

DARK_BLUE = HexColor('#1F3864')
YELLOW    = HexColor('#FFD700')
LIGHT_RED = HexColor('#FFE0E0')
MID_GREY  = HexColor('#CCCCCC')
DARK_GREY = HexColor('#888888')


def generate_pdf(records: List[AttendanceRecord], report_title: str,
                 period_start: date, period_end: date, output_path: str,
                 include_remarks: bool = True) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        rightMargin=1 * cm, leftMargin=1 * cm,
        topMargin=0.8 * cm, bottomMargin=1.0 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('rTitle', parent=styles['Normal'],
                                  fontSize=14, fontName='Helvetica-Bold',
                                  textColor=DARK_BLUE, alignment=TA_CENTER, spaceAfter=3)
    period_style = ParagraphStyle('rPeriod', parent=styles['Normal'],
                                   fontSize=9, fontName='Helvetica-Oblique',
                                   textColor=HexColor('#555555'), alignment=TA_CENTER, spaceAfter=8)
    footer_style = ParagraphStyle('rFooter', parent=styles['Normal'],
                                   fontSize=7, fontName='Helvetica',
                                   textColor=DARK_GREY)
    cell_style = ParagraphStyle('rCell', parent=styles['Normal'],
                                 fontSize=7.5, fontName='Helvetica', leading=10)

    period_text = period_start.strftime('%d-%b-%Y')
    if period_end != period_start:
        period_text += f" to {period_end.strftime('%d-%b-%Y')}"

    elements = [
        Paragraph(report_title, title_style),
        Paragraph(f"Period: {period_text}", period_style),
        Spacer(1, 0.1 * cm),
    ]

    if include_remarks:
        headers = ['Group\nPerson ID', 'Name', 'Date',
                   'First\nPunch In', 'Last\nPunch Out',
                   'Effective\nHours', 'Total\nHours',
                   'Company\nName', 'Remarks']
        col_widths = [1.8*cm, 4.5*cm, 2.5*cm, 2.0*cm, 2.0*cm,
                      2.2*cm, 2.0*cm, 3.5*cm, 5.5*cm]
    else:
        headers = ['Group\nPerson ID', 'Name', 'Date',
                   'First\nPunch In', 'Last\nPunch Out',
                   'Effective\nHours', 'Total\nHours',
                   'Company\nName']
        col_widths = [2.0*cm, 5.5*cm, 2.8*cm, 2.2*cm, 2.2*cm,
                      2.5*cm, 2.3*cm, 4.2*cm]

    data = [headers]
    row_fills = []

    for i, rec in enumerate(records, 1):
        row = [
            rec.ssno,
            Paragraph(rec.name, cell_style),
            rec.report_date.strftime('%d-%b-%Y') if rec.report_date else '',
            rec.first_punch_str,
            rec.last_punch_str,
            rec.effective_hours_str,
            rec.total_hours_str,
            Paragraph(rec.company_name, cell_style) if rec.company_name else '',
        ]
        if include_remarks:
            remarks_text = rec.remarks_str
            row.append(Paragraph(remarks_text, cell_style) if remarks_text else '')
            remarks_col = 8
            if rec.has_out_2hr:
                row_fills.append(('BACKGROUND', (remarks_col, i), (remarks_col, i), YELLOW))
            elif rec.has_any_remark:
                row_fills.append(('BACKGROUND', (remarks_col, i), (remarks_col, i), LIGHT_RED))
        data.append(row)

    base_style = [
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
        ('TEXTCOLOR',  (0, 0), (-1, 0), white),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, 0), 8),
        ('ALIGN',      (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME',   (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',   (0, 1), (-1, -1), 7.5),
        ('GRID',       (0, 0), (-1, -1), 0.3, MID_GREY),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        # All data rows left-aligned
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
    ]

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle(base_style + row_fills))

    elements.append(table)
    elements.append(Spacer(1, 0.4 * cm))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%d-%b-%Y %H:%M')}", footer_style))

    doc.build(elements, canvasmaker=_PageNumCanvas)
    return output_path
