from flask import Blueprint, render_template, current_app
from flask_login import login_required
from datetime import date, datetime
from sqlalchemy import func
from models import db, Customer, Delivery, Invoice, Payment

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    today = date.today()
    current_month = today.month
    current_year = today.year

    # Customer stats
    total_customers = Customer.query.filter_by(is_active=True).count()
    
    # Today's deliveries
    today_deliveries = Delivery.query.filter_by(delivery_date=today).count()
    today_jars_out = db.session.query(func.sum(Delivery.jars_delivered)).filter_by(delivery_date=today).scalar() or 0
    today_jars_back = db.session.query(func.sum(Delivery.jars_returned)).filter_by(delivery_date=today).scalar() or 0

    # Outstanding amounts
    total_outstanding = db.session.query(func.sum(Invoice.balance_amount)).filter(
        Invoice.payment_status.in_(['unpaid', 'partial'])
    ).scalar() or 0

    # This month invoices
    month_invoices = Invoice.query.filter_by(billing_month=current_month, billing_year=current_year).count()
    month_revenue = db.session.query(func.sum(Invoice.total_amount)).filter_by(
        billing_month=current_month, billing_year=current_year
    ).scalar() or 0

    # Total jars in market (all time)
    total_delivered = db.session.query(func.sum(Delivery.jars_delivered)).scalar() or 0
    total_returned = db.session.query(func.sum(Delivery.jars_returned)).scalar() or 0
    total_in_market = total_delivered - total_returned
    
    # Opening balances
    opening_balances = db.session.query(func.sum(Customer.opening_jar_balance)).scalar() or 0
    total_in_market += opening_balances

    # Customers with high pending jars
    warning_threshold = current_app.config.get('PENDING_JAR_WARNING', 10)
    
    # Recent deliveries
    recent_deliveries = db.session.query(Delivery).join(Customer).order_by(
        Delivery.delivery_date.desc(), Delivery.created_at.desc()
    ).limit(10).all()

    # Unpaid invoices
    unpaid_invoices = Invoice.query.filter(
        Invoice.payment_status.in_(['unpaid', 'partial'])
    ).order_by(Invoice.invoice_date.asc()).limit(10).all()

    # Monthly delivery chart data (last 6 months)
    chart_data = []
    for i in range(5, -1, -1):
        m = current_month - i
        y = current_year
        if m <= 0:
            m += 12
            y -= 1
        delivered = db.session.query(func.sum(Delivery.jars_delivered)).filter(
            func.strftime('%m', Delivery.delivery_date) == f'{m:02d}',
            func.strftime('%Y', Delivery.delivery_date) == str(y)
        ).scalar() or 0
        revenue = db.session.query(func.sum(Invoice.total_amount)).filter_by(
            billing_month=m, billing_year=y
        ).scalar() or 0
        month_name = datetime(y, m, 1).strftime('%b %Y')
        chart_data.append({'month': month_name, 'jars': int(delivered), 'revenue': float(revenue)})

    return render_template('dashboard/index.html',
        total_customers=total_customers,
        today_deliveries=today_deliveries,
        today_jars_out=today_jars_out,
        today_jars_back=today_jars_back,
        total_outstanding=total_outstanding,
        month_invoices=month_invoices,
        month_revenue=month_revenue,
        total_in_market=total_in_market,
        recent_deliveries=recent_deliveries,
        unpaid_invoices=unpaid_invoices,
        chart_data=chart_data,
        today=today
    )

@dashboard_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    from flask import request, flash
    from models import BusinessSettings
    
    if request.method == 'POST':
        fields = ['business_name', 'business_address', 'business_city', 'business_state',
                  'business_pin', 'business_mobile', 'business_email', 'business_gst',
                  'default_jar_rate', 'gst_rate', 'pending_jar_warning']
        for field in fields:
            val = request.form.get(field, '').strip()
            if val:
                BusinessSettings.set(field, val)
        flash('Settings saved successfully!', 'success')
    
    settings_data = {
        'business_name': BusinessSettings.get('business_name', current_app.config['BUSINESS_NAME']),
        'business_address': BusinessSettings.get('business_address', current_app.config['BUSINESS_ADDRESS']),
        'business_city': BusinessSettings.get('business_city', current_app.config['BUSINESS_CITY']),
        'business_state': BusinessSettings.get('business_state', current_app.config['BUSINESS_STATE']),
        'business_pin': BusinessSettings.get('business_pin', current_app.config['BUSINESS_PIN']),
        'business_mobile': BusinessSettings.get('business_mobile', current_app.config['BUSINESS_MOBILE']),
        'business_email': BusinessSettings.get('business_email', current_app.config['BUSINESS_EMAIL']),
        'business_gst': BusinessSettings.get('business_gst', current_app.config['BUSINESS_GST']),
        'default_jar_rate': BusinessSettings.get('default_jar_rate', current_app.config['DEFAULT_JAR_RATE']),
        'gst_rate': BusinessSettings.get('gst_rate', current_app.config['GST_RATE']),
        'pending_jar_warning': BusinessSettings.get('pending_jar_warning', current_app.config['PENDING_JAR_WARNING']),
    }
    
    return render_template('dashboard/settings.html', settings=settings_data)
