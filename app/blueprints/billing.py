from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from app import db
from app.models.invoice import Invoice
from app.models.customer import Customer
from app.models.delivery import Delivery
from app.models.settings import Settings
from sqlalchemy import func
from datetime import date
import calendar, io

billing_bp = Blueprint('billing', __name__, url_prefix='/billing')

@billing_bp.route('/')
@login_required
def index():
    month = int(request.args.get('month', date.today().month))
    year = int(request.args.get('year', date.today().year))
    status = request.args.get('status', '')
    query = Invoice.query.filter_by(billing_month=month, billing_year=year)
    if status:
        query = query.filter_by(status=status)
    invoices = query.order_by(Invoice.invoice_date.desc()).all()
    total_invoiced = sum(i.grand_total for i in invoices)
    total_paid = sum(i.paid_amount for i in invoices)
    total_due = sum(i.balance_due for i in invoices)
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]
    years = list(range(date.today().year - 2, date.today().year + 2))
    return render_template('billing/index.html',
        invoices=invoices, month=month, year=year, status=status,
        months=months, years=years,
        total_invoiced=total_invoiced, total_paid=total_paid, total_due=total_due)

@billing_bp.route('/generate', methods=['GET', 'POST'])
@login_required
def generate():
    today = date.today()
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]
    years = list(range(today.year - 1, today.year + 2))
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name).all()
    
    if request.method == 'POST':
        month = int(request.form['billing_month'])
        year = int(request.form['billing_year'])
        gst_pct = float(request.form.get('gst_percent') or Settings.get('gst_percent', '0'))
        selected_ids = request.form.getlist('customer_ids')
        
        if not selected_ids:
            flash('Please select at least one customer.', 'warning')
            return redirect(request.url)

        created = 0
        skipped = 0
        for cid in selected_ids:
            cid = int(cid)
            c = Customer.query.get(cid)
            if not c:
                continue
            # Check if invoice already exists
            existing = Invoice.query.filter_by(
                customer_id=cid, billing_month=month, billing_year=year).first()
            if existing:
                skipped += 1
                continue
            # Calculate deliveries for that month
            jars = db.session.query(func.sum(Delivery.jars_delivered)).filter(
                Delivery.customer_id == cid,
                func.strftime('%m', Delivery.delivery_date) == f'{month:02d}',
                func.strftime('%Y', Delivery.delivery_date) == str(year)
            ).scalar() or 0
            if jars == 0:
                skipped += 1
                continue
            subtotal = jars * c.jar_rate
            gst_amount = round(subtotal * gst_pct / 100, 2)
            grand_total = round(subtotal + gst_amount, 2)
            inv = Invoice(
                invoice_number=Invoice.generate_invoice_number(year),
                customer_id=cid,
                invoice_date=date.today(),
                billing_month=month,
                billing_year=year,
                total_jars=jars,
                rate_per_jar=c.jar_rate,
                subtotal=round(subtotal, 2),
                gst_percent=gst_pct,
                gst_amount=gst_amount,
                grand_total=grand_total,
                balance_due=grand_total,
                status='unpaid',
                created_by=current_user.id,
            )
            db.session.add(inv)
            created += 1
        db.session.commit()
        flash(f'Generated {created} invoices. {skipped} skipped (already exist or no deliveries).', 'success')
        return redirect(url_for('billing.index', month=month, year=year))

    return render_template('billing/generate.html',
        customers=customers, months=months, years=years,
        today=today)

@billing_bp.route('/<int:id>')
@login_required
def view(id):
    inv = Invoice.query.get_or_404(id)
    biz = _get_biz_settings()
    deliveries = Delivery.query.filter(
        Delivery.customer_id == inv.customer_id,
        func.strftime('%m', Delivery.delivery_date) == f'{inv.billing_month:02d}',
        func.strftime('%Y', Delivery.delivery_date) == str(inv.billing_year)
    ).order_by(Delivery.delivery_date).all()
    return render_template('billing/view.html', inv=inv, biz=biz, deliveries=deliveries)

@billing_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    inv = Invoice.query.get_or_404(id)
    if request.method == 'POST':
        inv.total_jars = int(request.form.get('total_jars') or inv.total_jars)
        inv.rate_per_jar = float(request.form.get('rate_per_jar') or inv.rate_per_jar)
        inv.gst_percent = float(request.form.get('gst_percent') or 0)
        inv.subtotal = round(inv.total_jars * inv.rate_per_jar, 2)
        inv.gst_amount = round(inv.subtotal * inv.gst_percent / 100, 2)
        inv.grand_total = round(inv.subtotal + inv.gst_amount, 2)
        inv.notes = request.form.get('notes', '').strip()
        inv.balance_due = max(0, inv.grand_total - inv.paid_amount)
        inv.update_status()
        db.session.commit()
        flash('Invoice updated!', 'success')
        return redirect(url_for('billing.view', id=inv.id))
    return render_template('billing/edit.html', inv=inv)

@billing_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    inv = Invoice.query.get_or_404(id)
    if inv.paid_amount > 0:
        flash('Cannot delete invoice with payments. Remove payments first.', 'danger')
        return redirect(url_for('billing.view', id=id))
    db.session.delete(inv)
    db.session.commit()
    flash('Invoice deleted.', 'success')
    return redirect(url_for('billing.index'))

@billing_bp.route('/<int:id>/pdf')
@login_required
def pdf(id):
    inv = Invoice.query.get_or_404(id)
    biz = _get_biz_settings()
    deliveries = Delivery.query.filter(
        Delivery.customer_id == inv.customer_id,
        func.strftime('%m', Delivery.delivery_date) == f'{inv.billing_month:02d}',
        func.strftime('%Y', Delivery.delivery_date) == str(inv.billing_year)
    ).order_by(Delivery.delivery_date).all()
    from app.utils.pdf_generator import generate_invoice_pdf
    pdf_bytes = generate_invoice_pdf(inv, biz, deliveries)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=request.args.get('download') == '1',
        download_name=f'Invoice_{inv.invoice_number}.pdf'
    )

def _get_biz_settings():
    return {
        'name': Settings.get('business_name', 'AquaFlow Water Supply'),
        'address': Settings.get('business_address', ''),
        'city': Settings.get('business_city', ''),
        'state': Settings.get('business_state', ''),
        'pin': Settings.get('business_pin', ''),
        'mobile': Settings.get('business_mobile', ''),
        'email': Settings.get('business_email', ''),
        'gst': Settings.get('business_gst', ''),
    }
