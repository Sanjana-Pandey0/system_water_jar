from flask import Blueprint, jsonify, request
from flask_login import login_required
from models import db, Customer, Delivery, Invoice
from sqlalchemy import func

api_bp = Blueprint('api', __name__)

@api_bp.route('/customers/search')
@login_required
def customers_search():
    q = request.args.get('q', '').strip()
    customers = Customer.query.filter(
        Customer.is_active == True,
        Customer.company_name.ilike(f'%{q}%')
    ).limit(10).all()
    return jsonify([{
        'id': c.id,
        'text': c.company_name,
        'code': c.customer_code,
        'rate': c.jar_rate,
        'pending_jars': c.pending_jars
    } for c in customers])

@api_bp.route('/customers/<int:id>/stats')
@login_required
def customer_stats(id):
    customer = Customer.query.get_or_404(id)
    return jsonify({
        'id': customer.id,
        'company_name': customer.company_name,
        'jar_rate': customer.jar_rate,
        'total_delivered': customer.total_delivered,
        'total_returned': customer.total_returned,
        'pending_jars': customer.pending_jars,
        'total_outstanding': customer.total_outstanding
    })

@api_bp.route('/deliveries/daily-totals')
@login_required
def daily_totals():
    from datetime import date
    delivery_date = request.args.get('date', date.today().isoformat())
    
    result = db.session.query(
        func.sum(Delivery.jars_delivered).label('delivered'),
        func.sum(Delivery.jars_returned).label('returned'),
        func.count(Delivery.id).label('count')
    ).filter(Delivery.delivery_date == delivery_date).first()
    
    return jsonify({
        'delivered': result.delivered or 0,
        'returned': result.returned or 0,
        'count': result.count or 0
    })

@api_bp.route('/invoices/month-preview')
@login_required
def month_preview():
    customer_id = request.args.get('customer_id', type=int)
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    if not all([customer_id, month, year]):
        return jsonify({'error': 'Missing parameters'}), 400
    
    customer = Customer.query.get_or_404(customer_id)
    
    deliveries = Delivery.query.filter_by(customer_id=customer_id).filter(
        func.strftime('%m', Delivery.delivery_date) == f'{month:02d}',
        func.strftime('%Y', Delivery.delivery_date) == str(year)
    ).all()
    
    total_jars = sum(d.jars_delivered for d in deliveries)
    amount = total_jars * customer.jar_rate
    
    return jsonify({
        'total_jars': total_jars,
        'rate': customer.jar_rate,
        'amount': amount,
        'delivery_days': len(deliveries)
    })
