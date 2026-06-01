from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from datetime import date, timedelta
from sqlalchemy import func
import csv, io
from models import db, Customer, Delivery

deliveries_bp = Blueprint('deliveries', __name__)

@deliveries_bp.route('/')
@login_required
def index():
    filter_date = request.args.get('date', date.today().isoformat())
    customer_id = request.args.get('customer_id', '', type=str)
    page = request.args.get('page', 1, type=int)

    try:
        from datetime import datetime
        selected_date = datetime.strptime(filter_date, '%Y-%m-%d').date()
    except:
        selected_date = date.today()

    query = Delivery.query.join(Customer)

    if filter_date:
        query = query.filter(Delivery.delivery_date == selected_date)
    if customer_id:
        query = query.filter(Delivery.customer_id == int(customer_id))

    deliveries = query.order_by(Delivery.delivery_date.desc(), Customer.company_name).paginate(
        page=page, per_page=25, error_out=False)

    # Daily totals
    daily_stats = db.session.query(
        func.sum(Delivery.jars_delivered).label('total_out'),
        func.sum(Delivery.jars_returned).label('total_back')
    ).filter(Delivery.delivery_date == selected_date).first()

    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name).all()

    return render_template('deliveries/index.html',
        deliveries=deliveries,
        selected_date=selected_date,
        daily_stats=daily_stats,
        customers=customers,
        customer_id=customer_id
    )

@deliveries_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        delivery_date_str = request.form.get('delivery_date', date.today().isoformat())
        
        try:
            from datetime import datetime
            delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d').date()
        except:
            delivery_date = date.today()

        # Check for duplicate entry (same customer, same date)
        existing = Delivery.query.filter_by(
            customer_id=customer_id, delivery_date=delivery_date
        ).first()
        
        if existing and not request.form.get('force'):
            customer = Customer.query.get(customer_id)
            flash(f'Warning: A delivery entry already exists for {customer.company_name} on {delivery_date}. Submitting again will create a duplicate.', 'warning')

        delivery = Delivery(
            customer_id=customer_id,
            delivery_date=delivery_date,
            jars_delivered=int(request.form.get('jars_delivered', 0) or 0),
            jars_returned=int(request.form.get('jars_returned', 0) or 0),
            delivery_staff=request.form.get('delivery_staff', '').strip(),
            remarks=request.form.get('remarks', '').strip(),
            created_by=current_user.id
        )
        db.session.add(delivery)
        db.session.commit()
        flash('Delivery entry added successfully!', 'success')
        
        if request.form.get('add_another'):
            return redirect(url_for('deliveries.add') + f'?date={delivery_date_str}')
        return redirect(url_for('deliveries.index', date=delivery_date_str))

    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name).all()
    selected_date = request.args.get('date', date.today().isoformat())
    return render_template('deliveries/form.html',
        customers=customers,
        selected_date=selected_date,
        delivery=None,
        title='Add Delivery'
    )

@deliveries_bp.route('/bulk-entry', methods=['GET', 'POST'])
@login_required
def bulk_entry():
    """Enter deliveries for multiple customers at once"""
    if request.method == 'POST':
        delivery_date_str = request.form.get('delivery_date', date.today().isoformat())
        try:
            from datetime import datetime
            delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d').date()
        except:
            delivery_date = date.today()
        
        staff = request.form.get('delivery_staff', '').strip()
        customer_ids = request.form.getlist('customer_id[]')
        jars_delivered = request.form.getlist('jars_delivered[]')
        jars_returned = request.form.getlist('jars_returned[]')
        remarks_list = request.form.getlist('remarks[]')
        
        count = 0
        for i, cid in enumerate(customer_ids):
            if not cid:
                continue
            delivered = int(jars_delivered[i] or 0)
            returned = int(jars_returned[i] or 0)
            if delivered == 0 and returned == 0:
                continue
            
            delivery = Delivery(
                customer_id=int(cid),
                delivery_date=delivery_date,
                jars_delivered=delivered,
                jars_returned=returned,
                delivery_staff=staff,
                remarks=remarks_list[i] if i < len(remarks_list) else '',
                created_by=current_user.id
            )
            db.session.add(delivery)
            count += 1
        
        db.session.commit()
        flash(f'{count} delivery entries added successfully!', 'success')
        return redirect(url_for('deliveries.index', date=delivery_date_str))

    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name).all()
    selected_date = request.args.get('date', date.today().isoformat())
    return render_template('deliveries/bulk_entry.html',
        customers=customers,
        selected_date=selected_date
    )

@deliveries_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    delivery = Delivery.query.get_or_404(id)
    if request.method == 'POST':
        try:
            from datetime import datetime
            delivery.delivery_date = datetime.strptime(request.form.get('delivery_date'), '%Y-%m-%d').date()
        except:
            pass
        delivery.jars_delivered = int(request.form.get('jars_delivered', 0) or 0)
        delivery.jars_returned = int(request.form.get('jars_returned', 0) or 0)
        delivery.delivery_staff = request.form.get('delivery_staff', '').strip()
        delivery.remarks = request.form.get('remarks', '').strip()
        db.session.commit()
        flash('Delivery updated successfully!', 'success')
        return redirect(url_for('deliveries.index', date=delivery.delivery_date.isoformat()))

    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name).all()
    return render_template('deliveries/form.html',
        customers=customers,
        delivery=delivery,
        selected_date=delivery.delivery_date.isoformat(),
        title='Edit Delivery'
    )

@deliveries_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    delivery = Delivery.query.get_or_404(id)
    del_date = delivery.delivery_date.isoformat()
    db.session.delete(delivery)
    db.session.commit()
    flash('Delivery entry deleted.', 'info')
    return redirect(url_for('deliveries.index', date=del_date))

@deliveries_bp.route('/export/csv')
@login_required
def export_csv():
    start = request.args.get('start', '')
    end = request.args.get('end', '')
    
    query = Delivery.query.join(Customer)
    if start:
        query = query.filter(Delivery.delivery_date >= start)
    if end:
        query = query.filter(Delivery.delivery_date <= end)
    
    deliveries = query.order_by(Delivery.delivery_date.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Customer Code', 'Customer', 'Delivered', 'Returned', 'Net', 'Staff', 'Remarks'])
    for d in deliveries:
        writer.writerow([d.delivery_date, d.customer.customer_code, d.customer.company_name,
                         d.jars_delivered, d.jars_returned, d.net_jars,
                         d.delivery_staff, d.remarks])
    
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=deliveries.csv'})
