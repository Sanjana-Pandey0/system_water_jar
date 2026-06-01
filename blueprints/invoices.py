from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, current_app
from flask_login import login_required, current_user
from datetime import date
from sqlalchemy import func
import io
from models import db, Customer, Delivery, Invoice, Payment

invoices_bp = Blueprint('invoices', __name__)

def generate_invoice_number():
    year = date.today().year
    last = Invoice.query.filter(
        Invoice.invoice_number.like(f'INV-{year}-%')
    ).order_by(Invoice.id.desc()).first()
    
    if last:
        try:
            num = int(last.invoice_number.split('-')[-1]) + 1
        except:
            num = 1
    else:
        num = 1
    return f'INV-{year}-{num:04d}'

@invoices_bp.route('/')
@login_required
def index():
    status = request.args.get('status', '')
    month = request.args.get('month', '', type=str)
    year = request.args.get('year', '', type=str)
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Invoice.query.join(Customer)

    if status:
        query = query.filter(Invoice.payment_status == status)
    if month:
        query = query.filter(Invoice.billing_month == int(month))
    if year:
        query = query.filter(Invoice.billing_year == int(year))
    if search:
        query = query.filter(
            Customer.company_name.ilike(f'%{search}%') |
            Invoice.invoice_number.ilike(f'%{search}%')
        )

    invoices = query.order_by(Invoice.invoice_date.desc()).paginate(page=page, per_page=20, error_out=False)

    # Stats
    total_amount = db.session.query(func.sum(Invoice.total_amount)).scalar() or 0
    total_paid = db.session.query(func.sum(Invoice.paid_amount)).scalar() or 0
    total_outstanding = total_amount - total_paid

    years = list(range(date.today().year, date.today().year - 3, -1))

    return render_template('invoices/index.html',
        invoices=invoices,
        status=status, month=month, year=year, search=search,
        total_amount=total_amount,
        total_paid=total_paid,
        total_outstanding=total_outstanding,
        years=years
    )

@invoices_bp.route('/generate', methods=['GET', 'POST'])
@login_required
def generate():
    if request.method == 'POST':
        customer_id = int(request.form.get('customer_id'))
        billing_month = int(request.form.get('billing_month'))
        billing_year = int(request.form.get('billing_year'))
        
        # Check if invoice already exists
        existing = Invoice.query.filter_by(
            customer_id=customer_id,
            billing_month=billing_month,
            billing_year=billing_year
        ).first()
        if existing:
            flash(f'Invoice already exists for this customer and month: {existing.invoice_number}', 'warning')
            return redirect(url_for('invoices.view', id=existing.id))

        customer = Customer.query.get_or_404(customer_id)

        # Get deliveries for the month
        deliveries = Delivery.query.filter_by(customer_id=customer_id).filter(
            func.strftime('%m', Delivery.delivery_date) == f'{billing_month:02d}',
            func.strftime('%Y', Delivery.delivery_date) == str(billing_year)
        ).all()

        total_jars = sum(d.jars_delivered for d in deliveries)
        rate = float(request.form.get('rate_per_jar', customer.jar_rate))
        subtotal = total_jars * rate
        gst_pct = float(request.form.get('gst_percentage', 0))
        gst_amount = subtotal * gst_pct / 100
        total_amount = subtotal + gst_amount

        invoice = Invoice(
            invoice_number=generate_invoice_number(),
            customer_id=customer_id,
            invoice_date=date.today(),
            billing_month=billing_month,
            billing_year=billing_year,
            total_jars=total_jars,
            rate_per_jar=rate,
            subtotal=subtotal,
            gst_percentage=gst_pct,
            gst_amount=gst_amount,
            total_amount=total_amount,
            paid_amount=0,
            balance_amount=total_amount,
            payment_status='unpaid',
            notes=request.form.get('notes', '').strip(),
            created_by=current_user.id
        )
        db.session.add(invoice)
        db.session.commit()
        flash(f'Invoice {invoice.invoice_number} generated successfully!', 'success')
        return redirect(url_for('invoices.view', id=invoice.id))

    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name).all()
    today = date.today()
    return render_template('invoices/generate.html',
        customers=customers,
        today=today,
        current_month=today.month,
        current_year=today.year
    )

@invoices_bp.route('/bulk-generate', methods=['GET', 'POST'])
@login_required
def bulk_generate():
    """Generate invoices for all active customers for a given month"""
    if request.method == 'POST':
        billing_month = int(request.form.get('billing_month'))
        billing_year = int(request.form.get('billing_year'))
        gst_pct = float(request.form.get('gst_percentage', 0))
        
        customers = Customer.query.filter_by(is_active=True).all()
        created = 0
        skipped = 0
        
        for customer in customers:
            existing = Invoice.query.filter_by(
                customer_id=customer.id,
                billing_month=billing_month,
                billing_year=billing_year
            ).first()
            if existing:
                skipped += 1
                continue
            
            deliveries = Delivery.query.filter_by(customer_id=customer.id).filter(
                func.strftime('%m', Delivery.delivery_date) == f'{billing_month:02d}',
                func.strftime('%Y', Delivery.delivery_date) == str(billing_year)
            ).all()
            
            total_jars = sum(d.jars_delivered for d in deliveries)
            if total_jars == 0:
                skipped += 1
                continue
            
            rate = customer.jar_rate
            subtotal = total_jars * rate
            gst_amount = subtotal * gst_pct / 100
            total_amount = subtotal + gst_amount

            invoice = Invoice(
                invoice_number=generate_invoice_number(),
                customer_id=customer.id,
                invoice_date=date.today(),
                billing_month=billing_month,
                billing_year=billing_year,
                total_jars=total_jars,
                rate_per_jar=rate,
                subtotal=subtotal,
                gst_percentage=gst_pct,
                gst_amount=gst_amount,
                total_amount=total_amount,
                paid_amount=0,
                balance_amount=total_amount,
                payment_status='unpaid',
                created_by=current_user.id
            )
            db.session.add(invoice)
            created += 1
        
        db.session.commit()
        flash(f'Bulk generation complete: {created} invoices created, {skipped} skipped.', 'success')
        return redirect(url_for('invoices.index',
                                month=billing_month, year=billing_year))
    
    today = date.today()
    return render_template('invoices/bulk_generate.html',
        current_month=today.month, current_year=today.year)

@invoices_bp.route('/<int:id>')
@login_required
def view(id):
    invoice = Invoice.query.get_or_404(id)
    payments = Payment.query.filter_by(invoice_id=id).order_by(Payment.payment_date.desc()).all()
    return render_template('invoices/view.html', invoice=invoice, payments=payments)

@invoices_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    invoice = Invoice.query.get_or_404(id)
    if request.method == 'POST':
        invoice.rate_per_jar = float(request.form.get('rate_per_jar', invoice.rate_per_jar))
        invoice.total_jars = int(request.form.get('total_jars', invoice.total_jars))
        invoice.gst_percentage = float(request.form.get('gst_percentage', invoice.gst_percentage))
        invoice.subtotal = invoice.total_jars * invoice.rate_per_jar
        invoice.gst_amount = invoice.subtotal * invoice.gst_percentage / 100
        invoice.total_amount = invoice.subtotal + invoice.gst_amount
        invoice.notes = request.form.get('notes', '').strip()
        invoice.update_payment_status()
        db.session.commit()
        flash('Invoice updated!', 'success')
        return redirect(url_for('invoices.view', id=id))
    return render_template('invoices/edit.html', invoice=invoice)

@invoices_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    invoice = Invoice.query.get_or_404(id)
    num = invoice.invoice_number
    db.session.delete(invoice)
    db.session.commit()
    flash(f'Invoice {num} deleted.', 'info')
    return redirect(url_for('invoices.index'))

@invoices_bp.route('/<int:id>/pdf')
@login_required
def download_pdf(id):
    from utils.pdf_generator import generate_invoice_pdf
    invoice = Invoice.query.get_or_404(id)
    pdf_buffer = generate_invoice_pdf(invoice)
    return Response(
        pdf_buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename={invoice.invoice_number}.pdf'}
    )
