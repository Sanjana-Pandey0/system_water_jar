from flask import Blueprint, render_template, request, Response, current_app
from flask_login import login_required
from datetime import date, datetime
from sqlalchemy import func
import csv, io
from models import db, Customer, Delivery, Invoice, Payment

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
@login_required
def index():
    return render_template('reports/index.html')

@reports_bp.route('/jar-inventory')
@login_required
def jar_inventory():
    warning_threshold = int(current_app.config.get('PENDING_JAR_WARNING', 10))
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name).all()
    
    inventory = []
    total_delivered = 0
    total_returned = 0
    
    for c in customers:
        d = c.total_delivered
        r = c.total_returned
        p = c.pending_jars
        total_delivered += d
        total_returned += r
        inventory.append({
            'customer': c,
            'delivered': d,
            'returned': r,
            'pending': p,
            'warning': p >= warning_threshold
        })
    
    inventory.sort(key=lambda x: x['pending'], reverse=True)
    
    return render_template('reports/jar_inventory.html',
        inventory=inventory,
        total_delivered=total_delivered,
        total_returned=total_returned,
        total_pending=total_delivered - total_returned,
        warning_threshold=warning_threshold
    )

@reports_bp.route('/monthly-summary')
@login_required
def monthly_summary():
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)

    # Per-customer summary
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name).all()
    summary = []

    for c in customers:
        deliveries = Delivery.query.filter_by(customer_id=c.id).filter(
            func.strftime('%m', Delivery.delivery_date) == f'{month:02d}',
            func.strftime('%Y', Delivery.delivery_date) == str(year)
        ).all()
        
        total_d = sum(d.jars_delivered for d in deliveries)
        total_r = sum(d.jars_returned for d in deliveries)
        
        invoice = Invoice.query.filter_by(
            customer_id=c.id, billing_month=month, billing_year=year
        ).first()
        
        if total_d > 0 or invoice:
            summary.append({
                'customer': c,
                'delivered': total_d,
                'returned': total_r,
                'net': total_d - total_r,
                'invoice': invoice,
                'amount': invoice.total_amount if invoice else total_d * c.jar_rate,
                'status': invoice.payment_status if invoice else 'no_invoice'
            })
    
    total_jars = sum(s['delivered'] for s in summary)
    total_amount = sum(s['amount'] for s in summary)
    
    years = list(range(date.today().year, date.today().year - 3, -1))

    return render_template('reports/monthly_summary.html',
        summary=summary,
        month=month, year=year,
        total_jars=total_jars,
        total_amount=total_amount,
        years=years
    )

@reports_bp.route('/daily-summary')
@login_required
def daily_summary():
    start_str = request.args.get('start', '')
    end_str = request.args.get('end', '')
    
    today = date.today()
    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else date(today.year, today.month, 1)
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date() if end_str else today
    except:
        start_date = date(today.year, today.month, 1)
        end_date = today

    daily = db.session.query(
        Delivery.delivery_date,
        func.count(Delivery.id).label('entries'),
        func.sum(Delivery.jars_delivered).label('delivered'),
        func.sum(Delivery.jars_returned).label('returned')
    ).filter(
        Delivery.delivery_date.between(start_date, end_date)
    ).group_by(Delivery.delivery_date).order_by(Delivery.delivery_date.desc()).all()

    return render_template('reports/daily_summary.html',
        daily=daily,
        start_date=start_date,
        end_date=end_date
    )

@reports_bp.route('/payment-summary')
@login_required
def payment_summary():
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)

    invoices = Invoice.query.filter_by(billing_month=month, billing_year=year).join(Customer).order_by(
        Customer.company_name).all()
    
    total_invoiced = sum(i.total_amount for i in invoices)
    total_collected = sum(i.paid_amount for i in invoices)
    total_outstanding = total_invoiced - total_collected
    
    paid_count = sum(1 for i in invoices if i.payment_status == 'paid')
    partial_count = sum(1 for i in invoices if i.payment_status == 'partial')
    unpaid_count = sum(1 for i in invoices if i.payment_status == 'unpaid')
    
    years = list(range(date.today().year, date.today().year - 3, -1))

    return render_template('reports/payment_summary.html',
        invoices=invoices,
        month=month, year=year,
        total_invoiced=total_invoiced,
        total_collected=total_collected,
        total_outstanding=total_outstanding,
        paid_count=paid_count,
        partial_count=partial_count,
        unpaid_count=unpaid_count,
        years=years
    )

@reports_bp.route('/export/jar-inventory-csv')
@login_required
def export_jar_inventory():
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Customer Code', 'Company', 'City', 'Total Delivered', 'Total Returned', 'Pending Jars', 'Rate'])
    for c in customers:
        writer.writerow([c.customer_code, c.company_name, c.city,
                         c.total_delivered, c.total_returned, c.pending_jars, c.jar_rate])
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=jar_inventory.csv'})

@reports_bp.route('/export/monthly-csv')
@login_required
def export_monthly_csv():
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)
    
    invoices = Invoice.query.filter_by(billing_month=month, billing_year=year).join(Customer).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Invoice No.', 'Customer', 'Jars', 'Rate', 'Amount', 'Paid', 'Balance', 'Status'])
    for i in invoices:
        writer.writerow([i.invoice_number, i.customer.company_name, i.total_jars,
                         i.rate_per_jar, i.total_amount, i.paid_amount, i.balance_amount, i.payment_status])
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=monthly_{year}_{month:02d}.csv'})
