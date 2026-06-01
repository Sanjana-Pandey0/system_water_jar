from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.payment import Payment
from app.models.invoice import Invoice
from app.models.customer import Customer
from datetime import date
from sqlalchemy import func

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')

@payments_bp.route('/')
@login_required
def index():
    from_date = request.args.get('from', '')
    to_date = request.args.get('to', '')
    q = Payment.query
    if from_date:
        q = q.filter(Payment.payment_date >= from_date)
    if to_date:
        q = q.filter(Payment.payment_date <= to_date)
    payments = q.order_by(Payment.payment_date.desc()).limit(100).all()
    total_amount = sum(p.amount for p in payments)
    return render_template('payments/index.html',
        payments=payments, total_amount=total_amount,
        from_date=from_date, to_date=to_date)

@payments_bp.route('/add/<int:invoice_id>', methods=['GET', 'POST'])
@login_required
def add(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    if request.method == 'POST':
        amount = float(request.form['amount'])
        if amount <= 0:
            flash('Amount must be positive.', 'danger')
            return redirect(request.url)
        p = Payment(
            invoice_id=inv.id,
            customer_id=inv.customer_id,
            payment_date=date.fromisoformat(request.form['payment_date']),
            amount=amount,
            method=request.form.get('method', 'cash'),
            reference=request.form.get('reference', '').strip(),
            notes=request.form.get('notes', '').strip(),
            created_by=current_user.id,
        )
        db.session.add(p)
        inv.paid_amount = (inv.paid_amount or 0) + amount
        inv.update_status()
        db.session.commit()
        flash(f'Payment of ₹{amount:.2f} recorded!', 'success')
        return redirect(url_for('billing.view', id=inv.id))
    return render_template('payments/form.html', inv=inv, today=date.today())

@payments_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    p = Payment.query.get_or_404(id)
    inv = p.invoice
    inv.paid_amount = max(0, (inv.paid_amount or 0) - p.amount)
    inv.update_status()
    invoice_id = p.invoice_id
    db.session.delete(p)
    db.session.commit()
    flash('Payment deleted.', 'success')
    return redirect(url_for('billing.view', id=invoice_id))
