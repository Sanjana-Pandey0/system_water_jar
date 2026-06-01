from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from datetime import date
from sqlalchemy import func, or_
import csv, io
from models import db, Customer, Delivery, Invoice, Payment

customers_bp = Blueprint('customers', __name__)

def generate_customer_code():
    last = Customer.query.order_by(Customer.id.desc()).first()
    num = (last.id + 1) if last else 1
    return f'CUST-{num:04d}'

@customers_bp.route('/')
@login_required
def index():
    search = request.args.get('search', '').strip()
    status = request.args.get('status', 'active')
    page = request.args.get('page', 1, type=int)

    query = Customer.query
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)

    if search:
        query = query.filter(or_(
            Customer.company_name.ilike(f'%{search}%'),
            Customer.contact_person.ilike(f'%{search}%'),
            Customer.mobile.ilike(f'%{search}%'),
            Customer.customer_code.ilike(f'%{search}%'),
            Customer.city.ilike(f'%{search}%'),
        ))

    customers = query.order_by(Customer.company_name).paginate(page=page, per_page=20, error_out=False)
    return render_template('customers/index.html', customers=customers, search=search, status=status)

@customers_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        customer = Customer(
            customer_code=generate_customer_code(),
            company_name=request.form.get('company_name', '').strip(),
            contact_person=request.form.get('contact_person', '').strip(),
            mobile=request.form.get('mobile', '').strip(),
            alternate_mobile=request.form.get('alternate_mobile', '').strip(),
            email=request.form.get('email', '').strip(),
            address=request.form.get('address', '').strip(),
            city=request.form.get('city', '').strip(),
            state=request.form.get('state', '').strip(),
            pin_code=request.form.get('pin_code', '').strip(),
            gst_number=request.form.get('gst_number', '').strip(),
            jar_rate=float(request.form.get('jar_rate', 60) or 60),
            security_deposit=float(request.form.get('security_deposit', 0) or 0),
            opening_jar_balance=int(request.form.get('opening_jar_balance', 0) or 0),
            notes=request.form.get('notes', '').strip(),
            is_active=True
        )
        db.session.add(customer)
        db.session.commit()
        flash(f'Customer "{customer.company_name}" added successfully!', 'success')
        return redirect(url_for('customers.view', id=customer.id))
    
    return render_template('customers/form.html', customer=None, title='Add Customer')

@customers_bp.route('/<int:id>')
@login_required
def view(id):
    customer = Customer.query.get_or_404(id)
    
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)

    # Monthly delivery summary
    monthly_deliveries = Delivery.query.filter_by(customer_id=id).filter(
        func.strftime('%m', Delivery.delivery_date) == f'{month:02d}',
        func.strftime('%Y', Delivery.delivery_date) == str(year)
    ).order_by(Delivery.delivery_date.desc()).all()

    month_delivered = sum(d.jars_delivered for d in monthly_deliveries)
    month_returned = sum(d.jars_returned for d in monthly_deliveries)

    # Invoice history
    invoices = Invoice.query.filter_by(customer_id=id).order_by(
        Invoice.billing_year.desc(), Invoice.billing_month.desc()
    ).limit(12).all()

    # Recent payments
    payments = Payment.query.join(Invoice).filter(Invoice.customer_id == id).order_by(
        Payment.payment_date.desc()
    ).limit(10).all()

    years = list(range(date.today().year, date.today().year - 3, -1))

    return render_template('customers/view.html',
        customer=customer,
        monthly_deliveries=monthly_deliveries,
        month_delivered=month_delivered,
        month_returned=month_returned,
        invoices=invoices,
        payments=payments,
        month=month,
        year=year,
        years=years
    )

@customers_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    customer = Customer.query.get_or_404(id)
    if request.method == 'POST':
        customer.company_name = request.form.get('company_name', '').strip()
        customer.contact_person = request.form.get('contact_person', '').strip()
        customer.mobile = request.form.get('mobile', '').strip()
        customer.alternate_mobile = request.form.get('alternate_mobile', '').strip()
        customer.email = request.form.get('email', '').strip()
        customer.address = request.form.get('address', '').strip()
        customer.city = request.form.get('city', '').strip()
        customer.state = request.form.get('state', '').strip()
        customer.pin_code = request.form.get('pin_code', '').strip()
        customer.gst_number = request.form.get('gst_number', '').strip()
        customer.jar_rate = float(request.form.get('jar_rate', 60) or 60)
        customer.security_deposit = float(request.form.get('security_deposit', 0) or 0)
        customer.opening_jar_balance = int(request.form.get('opening_jar_balance', 0) or 0)
        customer.notes = request.form.get('notes', '').strip()
        customer.is_active = request.form.get('is_active') == 'on'
        db.session.commit()
        flash('Customer updated successfully!', 'success')
        return redirect(url_for('customers.view', id=customer.id))
    
    return render_template('customers/form.html', customer=customer, title='Edit Customer')

@customers_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    customer = Customer.query.get_or_404(id)
    name = customer.company_name
    db.session.delete(customer)
    db.session.commit()
    flash(f'Customer "{name}" deleted.', 'info')
    return redirect(url_for('customers.index'))

@customers_bp.route('/<int:id>/toggle-status', methods=['POST'])
@login_required
def toggle_status(id):
    customer = Customer.query.get_or_404(id)
    customer.is_active = not customer.is_active
    db.session.commit()
    status = 'activated' if customer.is_active else 'deactivated'
    flash(f'Customer "{customer.company_name}" {status}.', 'success')
    return redirect(url_for('customers.view', id=id))

@customers_bp.route('/<int:id>/ledger')
@login_required
def ledger(id):
    customer = Customer.query.get_or_404(id)
    year = request.args.get('year', date.today().year, type=int)
    
    # All deliveries for the year
    deliveries = Delivery.query.filter_by(customer_id=id).filter(
        func.strftime('%Y', Delivery.delivery_date) == str(year)
    ).order_by(Delivery.delivery_date.asc()).all()

    # All invoices for the year
    invoices = Invoice.query.filter_by(customer_id=id, billing_year=year).order_by(
        Invoice.billing_month.asc()
    ).all()

    years = list(range(date.today().year, date.today().year - 3, -1))

    # Monthly summary
    monthly = {}
    for d in deliveries:
        m = d.delivery_date.month
        if m not in monthly:
            monthly[m] = {'delivered': 0, 'returned': 0, 'days': 0}
        monthly[m]['delivered'] += d.jars_delivered
        monthly[m]['returned'] += d.jars_returned
        monthly[m]['days'] += 1

    return render_template('customers/ledger.html',
        customer=customer,
        deliveries=deliveries,
        invoices=invoices,
        monthly=monthly,
        year=year,
        years=years
    )

@customers_bp.route('/export/csv')
@login_required
def export_csv():
    customers = Customer.query.order_by(Customer.company_name).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Code', 'Company', 'Contact', 'Mobile', 'Email', 'City', 'State',
                     'Rate', 'Security Deposit', 'Pending Jars', 'Outstanding', 'Status'])
    for c in customers:
        writer.writerow([c.customer_code, c.company_name, c.contact_person, c.mobile,
                         c.email, c.city, c.state, c.jar_rate, c.security_deposit,
                         c.pending_jars, c.total_outstanding, 'Active' if c.is_active else 'Inactive'])
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=customers.csv'}
    )
