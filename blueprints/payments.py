from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from datetime import date
from sqlalchemy import func
import csv, io
from models import db, Customer, Invoice, Payment

payments_bp = Blueprint('payments', __name__)

@payments_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    method = request.args.get('method', '')

    query = Payment.query.join(Invoice).join(Customer)
    if search:
        query = query.filter(Customer.company_name.ilike(f'%{search}%'))
    if method:
        query = query.filter(Payment.payment_method == method)

    payments = query.order_by(Payment.payment_date.desc(), Payment.created_at.desc()).paginate(
        page=page, per_page=25, error_out=False)

    total_collected = db.session.query(func.sum(Payment.amount)).scalar() or 0

    return render_template('payments/index.html',
        payments=payments, total_collected=total_collected,
        search=search, method=method)

@payments_bp.route('/record', methods=['GET', 'POST'])
@login_required
def record():
    invoice_id = request.args.get('invoice_id', type=int)
    
    if request.method == 'POST':
        invoice_id = int(request.form.get('invoice_id'))
        invoice = Invoice.query.get_or_404(invoice_id)
        
        amount = float(request.form.get('amount', 0))
        if amount <= 0:
            flash('Payment amount must be greater than 0.', 'danger')
            return redirect(url_for('payments.record', invoice_id=invoice_id))

        if amount > invoice.balance_amount + 0.01:
            flash(f'Payment amount cannot exceed balance of ₹{invoice.balance_amount:.2f}.', 'danger')
            return redirect(url_for('payments.record', invoice_id=invoice_id))

        payment = Payment(
            invoice_id=invoice_id,
            payment_date=date.fromisoformat(request.form.get('payment_date', date.today().isoformat())),
            amount=amount,
            payment_method=request.form.get('payment_method', 'cash'),
            reference_number=request.form.get('reference_number', '').strip(),
            notes=request.form.get('notes', '').strip(),
            created_by=current_user.id
        )
        db.session.add(payment)
        db.session.flush()
        invoice.update_payment_status()
        db.session.commit()
        flash(f'Payment of ₹{amount:,.2f} recorded successfully!', 'success')
        return redirect(url_for('invoices.view', id=invoice_id))

    invoice = None
    if invoice_id:
        invoice = Invoice.query.get_or_404(invoice_id)

    unpaid_invoices = Invoice.query.filter(
        Invoice.payment_status.in_(['unpaid', 'partial'])
    ).join(Customer).order_by(Customer.company_name).all()

    return render_template('payments/record.html',
        invoice=invoice,
        unpaid_invoices=unpaid_invoices,
        today=date.today().isoformat()
    )

@payments_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    payment = Payment.query.get_or_404(id)
    invoice = payment.invoice
    db.session.delete(payment)
    db.session.flush()
    invoice.update_payment_status()
    db.session.commit()
    flash('Payment deleted and invoice balance updated.', 'info')
    return redirect(url_for('invoices.view', id=invoice.id))

@payments_bp.route('/outstanding')
@login_required
def outstanding():
    customers = Customer.query.filter_by(is_active=True).all()
    outstanding_list = []
    for c in customers:
        balance = c.total_outstanding
        if balance > 0:
            oldest_invoice = Invoice.query.filter_by(customer_id=c.id).filter(
                Invoice.payment_status.in_(['unpaid', 'partial'])
            ).order_by(Invoice.invoice_date.asc()).first()
            outstanding_list.append({
                'customer': c,
                'balance': balance,
                'oldest_invoice': oldest_invoice
            })
    
    outstanding_list.sort(key=lambda x: x['balance'], reverse=True)
    total_outstanding = sum(x['balance'] for x in outstanding_list)

    return render_template('payments/outstanding.html',
        outstanding_list=outstanding_list,
        total_outstanding=total_outstanding
    )

@payments_bp.route('/export/csv')
@login_required
def export_csv():
    payments = Payment.query.join(Invoice).join(Customer).order_by(
        Payment.payment_date.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Invoice No.', 'Customer', 'Amount', 'Method', 'Reference', 'Notes'])
    for p in payments:
        writer.writerow([p.payment_date, p.invoice.invoice_number,
                         p.invoice.customer.company_name, p.amount,
                         p.payment_method, p.reference_number, p.notes])
    
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=payments.csv'})
