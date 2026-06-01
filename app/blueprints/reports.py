from flask import Blueprint, render_template, request, Response
from flask_login import login_required
from app import db
from app.models.customer import Customer
from app.models.delivery import Delivery
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.settings import Settings
from sqlalchemy import func
from datetime import date, timedelta
import csv, io, calendar

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
@login_required
def index():
    return render_template('reports/index.html')

@reports_bp.route('/jar-status')
@login_required
def jar_status():
    threshold = int(Settings.get('jar_warning_threshold', 10))
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name).all()
    data = []
    for c in customers:
        delivered = db.session.query(func.sum(Delivery.jars_delivered)).filter_by(customer_id=c.id).scalar() or 0
        returned = db.session.query(func.sum(Delivery.jars_returned)).filter_by(customer_id=c.id).scalar() or 0
        balance = c.opening_jar_balance + delivered - returned
        data.append({
            'customer': c,
            'delivered': delivered,
            'returned': returned,
            'balance': balance,
            'warning': balance >= threshold,
        })
    data.sort(key=lambda x: x['balance'], reverse=True)
    total_in_market = sum(d['balance'] for d in data)
    return render_template('reports/jar_status.html', data=data,
        total_in_market=total_in_market, threshold=threshold)

@reports_bp.route('/outstanding')
@login_required
def outstanding():
    invoices = Invoice.query.filter(
        Invoice.status.in_(['unpaid', 'partial'])
    ).order_by(Invoice.invoice_date).all()
    total_due = sum(i.balance_due for i in invoices)
    return render_template('reports/outstanding.html', invoices=invoices, total_due=total_due)

@reports_bp.route('/monthly-summary')
@login_required
def monthly_summary():
    month = int(request.args.get('month', date.today().month))
    year = int(request.args.get('year', date.today().year))
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name).all()
    data = []
    for c in customers:
        jars = db.session.query(func.sum(Delivery.jars_delivered)).filter(
            Delivery.customer_id == c.id,
            func.strftime('%m', Delivery.delivery_date) == f'{month:02d}',
            func.strftime('%Y', Delivery.delivery_date) == str(year)
        ).scalar() or 0
        if jars == 0:
            continue
        amount = jars * c.jar_rate
        inv = Invoice.query.filter_by(customer_id=c.id, billing_month=month, billing_year=year).first()
        data.append({
            'customer': c,
            'jars': jars,
            'amount': amount,
            'invoiced': inv is not None,
            'invoice': inv,
        })
    total_jars = sum(d['jars'] for d in data)
    total_amount = sum(d['amount'] for d in data)
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]
    years = list(range(date.today().year - 2, date.today().year + 2))
    return render_template('reports/monthly_summary.html', data=data,
        month=month, year=year, months=months, years=years,
        total_jars=total_jars, total_amount=total_amount,
        month_name=calendar.month_name[month])

@reports_bp.route('/collections')
@login_required
def collections():
    month = int(request.args.get('month', date.today().month))
    year = int(request.args.get('year', date.today().year))
    month_start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    month_end = date(year, month, last_day)
    payments = Payment.query.filter(
        Payment.payment_date >= month_start,
        Payment.payment_date <= month_end
    ).order_by(Payment.payment_date).all()
    total = sum(p.amount for p in payments)
    by_method = {}
    for p in payments:
        by_method[p.method] = by_method.get(p.method, 0) + p.amount
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]
    years = list(range(date.today().year - 2, date.today().year + 2))
    return render_template('reports/collections.html', payments=payments,
        total=total, by_method=by_method, month=month, year=year,
        months=months, years=years, month_name=calendar.month_name[month])

@reports_bp.route('/export/jar-status.csv')
@login_required
def export_jar_status():
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Customer', 'Contact', 'Mobile', 'City', 'Opening Balance', 'Total Delivered', 'Total Returned', 'Current Balance'])
    for c in customers:
        delivered = db.session.query(func.sum(Delivery.jars_delivered)).filter_by(customer_id=c.id).scalar() or 0
        returned = db.session.query(func.sum(Delivery.jars_returned)).filter_by(customer_id=c.id).scalar() or 0
        balance = c.opening_jar_balance + delivered - returned
        writer.writerow([c.company_name, c.contact_person, c.mobile, c.city,
            c.opening_jar_balance, delivered, returned, balance])
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=jar_status.csv'})

@reports_bp.route('/export/outstanding.csv')
@login_required
def export_outstanding():
    invoices = Invoice.query.filter(Invoice.status.in_(['unpaid', 'partial'])).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Invoice No', 'Customer', 'Month', 'Year', 'Total', 'Paid', 'Balance', 'Status'])
    for i in invoices:
        writer.writerow([i.invoice_number, i.customer.company_name,
            calendar.month_name[i.billing_month], i.billing_year,
            i.grand_total, i.paid_amount, i.balance_due, i.status])
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=outstanding.csv'})
