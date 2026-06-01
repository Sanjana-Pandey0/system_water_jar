from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import KeepTogether
import io
from datetime import date
from flask import current_app
from models import BusinessSettings

# Color scheme
BRAND_BLUE = colors.HexColor('#1a56db')
BRAND_DARK = colors.HexColor('#1a202c')
BRAND_LIGHT = colors.HexColor('#f0f4ff')
BRAND_GRAY = colors.HexColor('#6b7280')
BRAND_GREEN = colors.HexColor('#059669')
BRAND_RED = colors.HexColor('#dc2626')

def get_business_info():
    return {
        'name': BusinessSettings.get('business_name', current_app.config['BUSINESS_NAME']),
        'address': BusinessSettings.get('business_address', current_app.config['BUSINESS_ADDRESS']),
        'city': BusinessSettings.get('business_city', current_app.config['BUSINESS_CITY']),
        'state': BusinessSettings.get('business_state', current_app.config['BUSINESS_STATE']),
        'pin': BusinessSettings.get('business_pin', current_app.config['BUSINESS_PIN']),
        'mobile': BusinessSettings.get('business_mobile', current_app.config['BUSINESS_MOBILE']),
        'email': BusinessSettings.get('business_email', current_app.config['BUSINESS_EMAIL']),
        'gst': BusinessSettings.get('business_gst', current_app.config['BUSINESS_GST']),
    }

MONTH_NAMES = ['January','February','March','April','May','June',
               'July','August','September','October','November','December']

def generate_invoice_pdf(invoice):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm,
        title=f"Invoice {invoice.invoice_number}",
    )

    styles = getSampleStyleSheet()
    elements = []
    biz = get_business_info()

    # ─── HEADER ───────────────────────────────────────────────
    header_style = ParagraphStyle('Header', fontSize=22, textColor=colors.white,
                                   fontName='Helvetica-Bold', alignment=TA_LEFT, leading=28)
    sub_style = ParagraphStyle('Sub', fontSize=9, textColor=colors.HexColor('#d1d5db'),
                                fontName='Helvetica', alignment=TA_LEFT, leading=13)
    right_style = ParagraphStyle('Right', fontSize=9, textColor=colors.white,
                                  fontName='Helvetica', alignment=TA_RIGHT, leading=14)

    header_data = [
        [
            [Paragraph(biz['name'], header_style),
             Paragraph(biz['address'], sub_style),
             Paragraph(f"{biz['city']}, {biz['state']} - {biz['pin']}", sub_style),
             Paragraph(f"📞 {biz['mobile']}  |  ✉ {biz['email']}", sub_style),
             Paragraph(f"GSTIN: {biz['gst']}", sub_style)],
            [Paragraph('TAX INVOICE', ParagraphStyle('Inv', fontSize=14, textColor=colors.white,
                        fontName='Helvetica-Bold', alignment=TA_RIGHT)),
             Spacer(1, 4),
             Paragraph(invoice.invoice_number, ParagraphStyle('InvNum', fontSize=18, textColor=colors.HexColor('#fbbf24'),
                        fontName='Helvetica-Bold', alignment=TA_RIGHT)),
             Spacer(1, 4),
             Paragraph(f"Date: {invoice.invoice_date.strftime('%d %B %Y')}", right_style),
             Paragraph(f"Billing Period: {MONTH_NAMES[invoice.billing_month-1]} {invoice.billing_year}", right_style)]
        ]
    ]

    header_table = Table(header_data, colWidths=[11*cm, 7*cm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BRAND_BLUE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 14),
        ('TOPPADDING', (0, 0), (-1, -1), 18),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 18),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5*cm))

    # ─── BILL TO / STATUS ────────────────────────────────────
    cust = invoice.customer
    addr_lines = [cust.company_name]
    if cust.contact_person:
        addr_lines.append(f"Attn: {cust.contact_person}")
    if cust.address:
        addr_lines.append(cust.address)
    if cust.city:
        city_line = cust.city
        if cust.state: city_line += f", {cust.state}"
        if cust.pin_code: city_line += f" - {cust.pin_code}"
        addr_lines.append(city_line)
    if cust.mobile:
        addr_lines.append(f"Mobile: {cust.mobile}")
    if cust.gst_number:
        addr_lines.append(f"GSTIN: {cust.gst_number}")

    status_colors = {'paid': BRAND_GREEN, 'partial': colors.HexColor('#d97706'), 'unpaid': BRAND_RED}
    status_color = status_colors.get(invoice.payment_status, BRAND_GRAY)

    bill_to_style = ParagraphStyle('BillTo', fontSize=9, textColor=BRAND_DARK, fontName='Helvetica', leading=14)
    bill_to_header = ParagraphStyle('BillToH', fontSize=8, textColor=BRAND_GRAY, fontName='Helvetica-Bold', leading=12)

    addr_para = [Paragraph('BILL TO', bill_to_header), Spacer(1, 3)]
    for line in addr_lines:
        addr_para.append(Paragraph(line, bill_to_style))

    status_text = invoice.payment_status.upper().replace('_', ' ')
    status_para = [
        Paragraph('PAYMENT STATUS', bill_to_header),
        Spacer(1, 3),
        Paragraph(f'<font color="#{format(status_color.hexval(), "06x") if hasattr(status_color, "hexval") else "000000"}"><b>{status_text}</b></font>',
                  ParagraphStyle('Status', fontSize=14, fontName='Helvetica-Bold', leading=18))
    ]

    info_data = [[addr_para, status_para]]
    info_table = Table(info_data, colWidths=[11*cm, 7*cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), BRAND_LIGHT),
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#fafafa')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 12),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('LINEBEFORE', (1, 0), (1, -1), 0.5, colors.HexColor('#e5e7eb')),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.5*cm))

    # ─── ITEMS TABLE ──────────────────────────────────────────
    th_style = ParagraphStyle('TH', fontSize=9, textColor=colors.white,
                               fontName='Helvetica-Bold', alignment=TA_CENTER)
    td_style = ParagraphStyle('TD', fontSize=9, textColor=BRAND_DARK,
                               fontName='Helvetica', alignment=TA_CENTER, leading=14)
    td_left = ParagraphStyle('TDL', fontSize=9, textColor=BRAND_DARK,
                              fontName='Helvetica', alignment=TA_LEFT, leading=14)

    table_data = [
        [Paragraph('#', th_style),
         Paragraph('Description', th_style),
         Paragraph('Qty (Jars)', th_style),
         Paragraph('Rate (₹)', th_style),
         Paragraph('Amount (₹)', th_style)]
    ]

    desc = f"20-Liter Water Jar Supply\n{MONTH_NAMES[invoice.billing_month-1]} {invoice.billing_year}"
    table_data.append([
        Paragraph('1', td_style),
        Paragraph(desc, td_left),
        Paragraph(str(invoice.total_jars), td_style),
        Paragraph(f"{invoice.rate_per_jar:,.2f}", td_style),
        Paragraph(f"{invoice.subtotal:,.2f}", td_style),
    ])

    item_table = Table(table_data, colWidths=[1*cm, 8.5*cm, 2.5*cm, 2.5*cm, 3.5*cm])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_DARK),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e5e7eb')),
    ]))
    elements.append(item_table)
    elements.append(Spacer(1, 0.3*cm))

    # ─── TOTALS ───────────────────────────────────────────────
    total_style = ParagraphStyle('Total', fontSize=9, textColor=BRAND_DARK,
                                  fontName='Helvetica', alignment=TA_RIGHT, leading=16)
    total_label = ParagraphStyle('TotalL', fontSize=9, textColor=BRAND_GRAY,
                                  fontName='Helvetica', alignment=TA_LEFT, leading=16)
    grand_total_style = ParagraphStyle('Grand', fontSize=12, textColor=colors.white,
                                        fontName='Helvetica-Bold', alignment=TA_RIGHT, leading=18)

    totals_data = []
    totals_data.append(['', Paragraph('Subtotal:', total_label), Paragraph(f"₹ {invoice.subtotal:,.2f}", total_style)])
    if invoice.gst_percentage > 0:
        totals_data.append(['', Paragraph(f"GST ({invoice.gst_percentage:.1f}%):", total_label),
                            Paragraph(f"₹ {invoice.gst_amount:,.2f}", total_style)])
    totals_data.append(['', Paragraph('Total Amount:', total_label),
                         Paragraph(f"₹ {invoice.total_amount:,.2f}", total_style)])
    totals_data.append(['', Paragraph('Amount Paid:', total_label),
                         Paragraph(f"₹ {invoice.paid_amount:,.2f}", total_style)])

    totals_table = Table(totals_data, colWidths=[10*cm, 4*cm, 4*cm])
    totals_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LINEABOVE', (1, -2), (-1, -2), 0.5, colors.HexColor('#e5e7eb')),
    ]))
    elements.append(totals_table)

    # Grand total / balance row
    balance_bg = BRAND_GREEN if invoice.payment_status == 'paid' else BRAND_RED
    balance_data = [['', Paragraph('BALANCE DUE:', ParagraphStyle('BalL', fontSize=11, textColor=colors.white,
                        fontName='Helvetica-Bold', alignment=TA_LEFT)),
                      Paragraph(f"₹ {invoice.balance_amount:,.2f}",
                                ParagraphStyle('Bal', fontSize=13, textColor=colors.white,
                                               fontName='Helvetica-Bold', alignment=TA_RIGHT))]]
    balance_table = Table(balance_data, colWidths=[10*cm, 4*cm, 4*cm])
    balance_table.setStyle(TableStyle([
        ('BACKGROUND', (1, 0), (-1, -1), balance_bg),
        ('TOPPADDING', (1, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (1, 0), (-1, -1), 10),
        ('LEFTPADDING', (1, 0), (-1, -1), 10),
        ('RIGHTPADDING', (1, 0), (-1, -1), 10),
    ]))
    elements.append(balance_table)
    elements.append(Spacer(1, 0.5*cm))

    # ─── NOTES ────────────────────────────────────────────────
    if invoice.notes:
        elements.append(Paragraph('Notes:', ParagraphStyle('NotesH', fontSize=9, textColor=BRAND_GRAY,
                                                             fontName='Helvetica-Bold')))
        elements.append(Paragraph(invoice.notes, ParagraphStyle('Notes', fontSize=9, textColor=BRAND_DARK,
                                                                   fontName='Helvetica', leading=14)))
        elements.append(Spacer(1, 0.3*cm))

    # ─── FOOTER ───────────────────────────────────────────────
    elements.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e5e7eb')))
    elements.append(Spacer(1, 0.2*cm))
    footer_style = ParagraphStyle('Footer', fontSize=8, textColor=BRAND_GRAY,
                                   fontName='Helvetica', alignment=TA_CENTER, leading=12)
    elements.append(Paragraph(
        f"Thank you for your business! • {biz['name']} • {biz['mobile']} • {biz['email']}",
        footer_style))
    elements.append(Paragraph(
        "This is a computer-generated invoice and does not require a physical signature.",
        ParagraphStyle('FooterSub', fontSize=7, textColor=colors.HexColor('#9ca3af'),
                       fontName='Helvetica', alignment=TA_CENTER)))

    doc.build(elements)
    buffer.seek(0)
    return buffer
