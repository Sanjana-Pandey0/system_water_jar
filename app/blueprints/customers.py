from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.customer import Customer
from app.models.delivery import Delivery
from app.models.invoice import Invoice
from app.models.settings import Settings
from sqlalchemy import func

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')

@customers_bp.route('/')
@login_required
def index():
    q = request.args.get('q', '').strip()
    status = request.args.get('status', 'active')
    query = Customer.query
    if q:
        query = query.filter(
            (Customer.company_name.ilike(f'%{q}%')) |
            (Customer.contact_person.ilike(f'%{q}%')) |
            (Customer.mobile.ilike(f'%{q}%')) |
            (Customer.city.ilike(f'%{q}%'))
        )
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)
    customers = query.order_by(Customer.company_name).all()
    # Add jar balance to each
    customer_data = []
    for c in customers:
        customer_data.append({
            'customer': c,
            'jar_balance': c.get_jar_balance(),
            'outstanding': c.get_outstanding_amount(),
        })
    return render_template('customers/index.html', customer_data=customer_data, q=q, status=status)

@customers_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    default_rate = Settings.get('default_jar_rate', '30')
    if request.method == 'POST':
        c = Customer(
            company_name=request.form['company_name'].strip(),
            contact_person=request.form['contact_person'].strip(),
            mobile=request.form['mobile'].strip(),
            alt_mobile=request.form.get('alt_mobile', '').strip(),
            email=request.form.get('email', '').strip(),
            address=request.form.get('address', '').strip(),
            city=request.form.get('city', '').strip(),
            state=request.form.get('state', '').strip(),
            pin_code=request.form.get('pin_code', '').strip(),
            gst_number=request.form.get('gst_number', '').strip(),
            jar_rate=float(request.form.get('jar_rate') or default_rate),
            security_deposit=float(request.form.get('security_deposit') or 0),
            opening_jar_balance=int(request.form.get('opening_jar_balance') or 0),
            notes=request.form.get('notes', '').strip(),
            is_active=True,
        )
        db.session.add(c)
        db.session.commit()
        flash(f'Customer "{c.company_name}" added successfully!', 'success')
        return redirect(url_for('customers.view', id=c.id))
    return render_template('customers/form.html', customer=None, default_rate=default_rate, action='Add')

@customers_bp.route('/<int:id>')
@login_required
def view(id):
    c = Customer.query.get_or_404(id)
    jar_balance = c.get_jar_balance()
    outstanding = c.get_outstanding_amount()
    recent_deliveries = Delivery.query.filter_by(customer_id=id).order_by(
        Delivery.delivery_date.desc()).limit(20).all()
    invoices = Invoice.query.filter_by(customer_id=id).order_by(
        Invoice.billing_year.desc(), Invoice.billing_month.desc()).all()
    total_delivered = db.session.query(func.sum(Delivery.jars_delivered)).filter_by(customer_id=id).scalar() or 0
    total_returned = db.session.query(func.sum(Delivery.jars_returned)).filter_by(customer_id=id).scalar() or 0
    total_invoiced = db.session.query(func.sum(Invoice.grand_total)).filter_by(customer_id=id).scalar() or 0
    total_paid = db.session.query(func.sum(Invoice.paid_amount)).filter_by(customer_id=id).scalar() or 0
    threshold = int(Settings.get('jar_warning_threshold', 10))
    return render_template('customers/view.html',
        c=c, jar_balance=jar_balance, outstanding=outstanding,
        recent_deliveries=recent_deliveries, invoices=invoices,
        total_delivered=total_delivered, total_returned=total_returned,
        total_invoiced=total_invoiced, total_paid=total_paid,
        threshold=threshold)

@customers_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    c = Customer.query.get_or_404(id)
    if request.method == 'POST':
        c.company_name = request.form['company_name'].strip()
        c.contact_person = request.form['contact_person'].strip()
        c.mobile = request.form['mobile'].strip()
        c.alt_mobile = request.form.get('alt_mobile', '').strip()
        c.email = request.form.get('email', '').strip()
        c.address = request.form.get('address', '').strip()
        c.city = request.form.get('city', '').strip()
        c.state = request.form.get('state', '').strip()
        c.pin_code = request.form.get('pin_code', '').strip()
        c.gst_number = request.form.get('gst_number', '').strip()
        c.jar_rate = float(request.form.get('jar_rate') or c.jar_rate)
        c.security_deposit = float(request.form.get('security_deposit') or 0)
        c.opening_jar_balance = int(request.form.get('opening_jar_balance') or 0)
        c.notes = request.form.get('notes', '').strip()
        c.is_active = 'is_active' in request.form
        db.session.commit()
        flash('Customer updated successfully!', 'success')
        return redirect(url_for('customers.view', id=c.id))
    return render_template('customers/form.html', customer=c, action='Edit')

@customers_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    c = Customer.query.get_or_404(id)
    name = c.company_name
    db.session.delete(c)
    db.session.commit()
    flash(f'Customer "{name}" deleted.', 'success')
    return redirect(url_for('customers.index'))

@customers_bp.route('/<int:id>/toggle-status', methods=['POST'])
@login_required
def toggle_status(id):
    c = Customer.query.get_or_404(id)
    c.is_active = not c.is_active
    db.session.commit()
    status = 'activated' if c.is_active else 'deactivated'
    flash(f'Customer {status}.', 'success')
    return redirect(url_for('customers.view', id=c.id))

@customers_bp.route('/<int:id>/ledger')
@login_required
def ledger(id):
    c = Customer.query.get_or_404(id)
    deliveries = Delivery.query.filter_by(customer_id=id).order_by(Delivery.delivery_date).all()
    invoices = Invoice.query.filter_by(customer_id=id).order_by(
        Invoice.billing_year, Invoice.billing_month).all()
    from app.models.payment import Payment
    payments = Payment.query.filter_by(customer_id=id).order_by(Payment.payment_date).all()
    jar_balance = c.get_jar_balance()
    outstanding = c.get_outstanding_amount()
    return render_template('customers/ledger.html',
        c=c, deliveries=deliveries, invoices=invoices,
        payments=payments, jar_balance=jar_balance, outstanding=outstanding)

@customers_bp.route('/api/search')
@login_required
def api_search():
    q = request.args.get('q', '')
    customers = Customer.query.filter(
        Customer.is_active == True,
        (Customer.company_name.ilike(f'%{q}%')) | (Customer.mobile.ilike(f'%{q}%'))
    ).limit(10).all()
    return jsonify([{'id': c.id, 'name': c.company_name, 'rate': c.jar_rate} for c in customers])
