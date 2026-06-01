from flask import Blueprint, render_template, current_app
from flask_login import login_required
from app import db
from app.models.customer import Customer
from app.models.delivery import Delivery
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.settings import Settings
from sqlalchemy import func, extract
from datetime import date, timedelta
import calendar

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    today = date.today()
    month_start = today.replace(day=1)

    # KPIs
    total_customers = Customer.query.filter_by(is_active=True).count()
    
    today_deliveries = Delivery.query.filter_by(delivery_date=today).count()
    today_jars_out = db.session.query(func.sum(Delivery.jars_delivered)).filter_by(delivery_date=today).scalar() or 0
    today_jars_in = db.session.query(func.sum(Delivery.jars_returned)).filter_by(delivery_date=today).scalar() or 0

    # Total jars in market (all time)
    total_delivered_all = db.session.query(func.sum(Delivery.jars_delivered)).scalar() or 0
    total_returned_all = db.session.query(func.sum(Delivery.jars_returned)).scalar() or 0
    opening_balance_total = db.session.query(func.sum(Customer.opening_jar_balance)).scalar() or 0
    total_jars_market = opening_balance_total + total_delivered_all - total_returned_all

    # Outstanding payments
    unpaid_amount = db.session.query(func.sum(Invoice.balance_due)).filter(
        Invoice.status.in_(['unpaid', 'partial'])).scalar() or 0
    
    # This month collections
    month_collected = db.session.query(func.sum(Payment.amount)).filter(
        Payment.payment_date >= month_start).scalar() or 0

    # This month invoiced
    month_invoiced = db.session.query(func.sum(Invoice.grand_total)).filter(
        Invoice.billing_month == today.month,
        Invoice.billing_year == today.year).scalar() or 0

    # Customers with high pending jars
    threshold = int(Settings.get('jar_warning_threshold', 10))
    customers_all = Customer.query.filter_by(is_active=True).all()
    warning_customers = []
    for c in customers_all:
        bal = c.get_jar_balance()
        if bal >= threshold:
            warning_customers.append({'customer': c, 'balance': bal})
    warning_customers.sort(key=lambda x: x['balance'], reverse=True)
    warning_customers = warning_customers[:5]

    # Recent deliveries (last 7 days)
    week_ago = today - timedelta(days=6)
    recent_deliveries = Delivery.query.filter(
        Delivery.delivery_date >= week_ago
    ).order_by(Delivery.delivery_date.desc()).limit(10).all()

    # Unpaid invoices
    unpaid_invoices = Invoice.query.filter(
        Invoice.status.in_(['unpaid', 'partial'])
    ).order_by(Invoice.invoice_date.desc()).limit(8).all()

    # Chart: last 7 days deliveries
    chart_labels = []
    chart_delivered = []
    chart_returned = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        chart_labels.append(d.strftime('%d %b'))
        del_sum = db.session.query(func.sum(Delivery.jars_delivered)).filter_by(delivery_date=d).scalar() or 0
        ret_sum = db.session.query(func.sum(Delivery.jars_returned)).filter_by(delivery_date=d).scalar() or 0
        chart_delivered.append(del_sum)
        chart_returned.append(ret_sum)

    # Monthly revenue chart (last 6 months)
    rev_labels = []
    rev_data = []
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        rev_labels.append(calendar.month_abbr[m])
        rev = db.session.query(func.sum(Invoice.grand_total)).filter_by(
            billing_month=m, billing_year=y).scalar() or 0
        rev_data.append(round(rev, 2))

    biz = {
        'name': Settings.get('business_name', 'AquaFlow Water Supply'),
    }

    return render_template('dashboard/index.html',
        total_customers=total_customers,
        today_deliveries=today_deliveries,
        today_jars_out=today_jars_out,
        today_jars_in=today_jars_in,
        total_jars_market=total_jars_market,
        unpaid_amount=unpaid_amount,
        month_collected=month_collected,
        month_invoiced=month_invoiced,
        warning_customers=warning_customers,
        recent_deliveries=recent_deliveries,
        unpaid_invoices=unpaid_invoices,
        chart_labels=chart_labels,
        chart_delivered=chart_delivered,
        chart_returned=chart_returned,
        rev_labels=rev_labels,
        rev_data=rev_data,
        today=today,
        biz=biz,
    )
