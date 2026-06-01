from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import io, calendar

PRIMARY = colors.HexColor('#1a56db')
DARK = colors.HexColor('#1e2939')
LIGHT_BG = colors.HexColor('#f0f4ff')
ACCENT = colors.HexColor('#0e9f6e')
GRAY = colors.HexColor('#6b7280')
LIGHT_GRAY = colors.HexColor('#f3f4f6')
RED = colors.HexColor('#e02424')
WHITE = colors.white

def generate_invoice_pdf(inv, biz, deliveries):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        rightMargin=15*mm, leftMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm)

    styles = getSampleStyleSheet()
    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    header_data = [[
        Paragraph(f'<font size="20" color="#1a56db"><b>{biz["name"]}</b></font>', styles['Normal']),
        Paragraph(f'<font size="18" color="#1e2939"><b>INVOICE</b></font><br/>'
                  f'<font size="10" color="#6b7280">{inv.invoice_number}</font>', 
                  ParagraphStyle('r', alignment=TA_RIGHT, parent=styles['Normal']))
    ]]
    header_table = Table(header_data, colWidths=[110*mm, 65*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    story.append(header_table)

    # Business address line
    biz_addr = f'{biz["address"]}, {biz["city"]} - {biz["pin"]} | {biz["mobile"]} | {biz["email"]}'
    if biz.get('gst'):
        biz_addr += f' | GST: {biz["gst"]}'
    story.append(Paragraph(f'<font size="8" color="#6b7280">{biz_addr}</font>', styles['Normal']))
    story.append(HRFlowable(width='100%', thickness=2, color=PRIMARY, spaceAfter=4*mm))

    # ── Invoice Meta + Customer ───────────────────────────────────────────────
    c = inv.customer
    status_color = '#0e9f6e' if inv.status == 'paid' else ('#f59e0b' if inv.status == 'partial' else '#e02424')
    status_label = inv.status.upper()

    bill_to = f'<b>BILL TO</b><br/><b>{c.company_name}</b><br/>{c.contact_person}<br/>{c.mobile}'
    if c.address:
        bill_to += f'<br/>{c.address}'
    if c.city:
        bill_to += f', {c.city}'
    if c.gst_number:
        bill_to += f'<br/>GST: {c.gst_number}'

    inv_details = (
        f'<b>Invoice Date:</b> {inv.invoice_date.strftime("%d %b %Y")}<br/>'
        f'<b>Billing Period:</b> {calendar.month_name[inv.billing_month]} {inv.billing_year}<br/>'
        f'<b>Status:</b> <font color="{status_color}"><b>{status_label}</b></font>'
    )

    meta_data = [[
        Paragraph(bill_to, ParagraphStyle('bt', fontSize=9, leading=14, parent=styles['Normal'])),
        Paragraph(inv_details, ParagraphStyle('id', fontSize=9, leading=14, alignment=TA_RIGHT, parent=styles['Normal'])),
    ]]
    meta_table = Table(meta_data, colWidths=[95*mm, 80*mm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), LIGHT_BG),
        ('BACKGROUND', (1, 0), (1, 0), LIGHT_BG),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ROUNDEDCORNERS', [4]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(Spacer(1, 4*mm))
    story.append(meta_table)

    # ── Delivery Table ─────────────────────────────────────────────────────────
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph('<b>Delivery Details</b>',
        ParagraphStyle('h3', fontSize=11, textColor=DARK, parent=styles['Normal'])))
    story.append(Spacer(1, 2*mm))

    if deliveries:
        del_headers = ['Date', 'Jars Delivered', 'Jars Returned', 'Staff', 'Remarks']
        del_data = [del_headers]
        for d in deliveries:
            del_data.append([
                d.delivery_date.strftime('%d %b'),
                str(d.jars_delivered),
                str(d.jars_returned),
                d.delivery_staff or '—',
                d.remarks or '—',
            ])
        del_table = Table(del_data, colWidths=[25*mm, 35*mm, 35*mm, 35*mm, None])
        del_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (2, -1), 'CENTER'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#d1d5db')),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(del_table)
    else:
        story.append(Paragraph('<i>No delivery records found for this period.</i>',
            ParagraphStyle('note', fontSize=9, textColor=GRAY, parent=styles['Normal'])))

    # ── Totals ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 6*mm))
    totals_data = [
        ['Total Jars Delivered', f'{inv.total_jars}'],
        ['Rate per Jar', f'₹ {inv.rate_per_jar:.2f}'],
        ['Subtotal', f'₹ {inv.subtotal:.2f}'],
    ]
    if inv.gst_percent > 0:
        totals_data.append([f'GST @ {inv.gst_percent}%', f'₹ {inv.gst_amount:.2f}'])
    totals_data.append(['GRAND TOTAL', f'₹ {inv.grand_total:.2f}'])
    totals_data.append(['Amount Paid', f'₹ {inv.paid_amount:.2f}'])
    totals_data.append(['Balance Due', f'₹ {inv.balance_due:.2f}'])

    totals_table = Table(totals_data, colWidths=[90*mm, 45*mm])
    ts = TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('LINEABOVE', (0, -3), (-1, -3), 1, DARK),
        ('FONTNAME', (0, -3), (-1, -3), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -3), (-1, -3), DARK),
        ('TEXTCOLOR', (0, -3), (-1, -3), WHITE),
        ('FONTSIZE', (0, -3), (-1, -3), 11),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, -1), (-1, -1), RED if inv.balance_due > 0 else ACCENT),
    ])
    totals_table.setStyle(ts)

    # Right-align totals table
    outer = Table([[None, totals_table]], colWidths=[40*mm, 135*mm])
    outer.setStyle(TableStyle([('ALIGN', (1, 0), (1, 0), 'RIGHT'), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story.append(outer)

    # ── Footer ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=GRAY))
    story.append(Spacer(1, 2*mm))
    footer_text = 'Thank you for your business! Please pay within 30 days of invoice date.'
    if biz.get('mobile'):
        footer_text += f' For queries: {biz["mobile"]}'
    story.append(Paragraph(f'<font size="8" color="#6b7280"><i>{footer_text}</i></font>',
        ParagraphStyle('footer', alignment=TA_CENTER, parent=styles['Normal'])))

    doc.build(story)
    return buffer.getvalue()
