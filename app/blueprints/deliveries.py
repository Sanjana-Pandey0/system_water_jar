from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from app import db
from app.models.delivery import Delivery
from app.models.customer import Customer
from app.models.settings import Settings
from sqlalchemy import func
from datetime import date, timedelta
import csv, io

deliveries_bp = Blueprint('deliveries', __name__, url_prefix='/deliveries')

@deliveries_bp.route('/')
@login_required
def index():
    today = date.today()
    selected_date = request.args.get('date', today.strftime('%Y-%m-%d'))
    try:
        sel_date = date.fromisoformat(selected_date)
    except:
        sel_date = today
    deliveries = Delivery.query.filter_by(delivery_date=sel_date).order_by(Delivery.id.desc()).all()
    total_out = sum(d.jars_delivered for d in deliveries)
    total_in = sum(d.jars_returned for d in deliveries)
    prev_date = sel_date - timedelta(days=1)
    next_date = sel_date + timedelta(days=1)
    return render_template('deliveries/index.html',
        deliveries=deliveries, selected_date=sel_date,
        total_out=total_out, total_in=total_in,
        today=today, prev_date=prev_date, next_date=next_date)

@deliveries_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name).all()
    if request.method == 'POST':
        customer_id = int(request.form['customer_id'])
        delivery_date = date.fromisoformat(request.form['delivery_date'])
        jars_delivered = int(request.form.get('jars_delivered') or 0)
        jars_returned = int(request.form.get('jars_returned') or 0)
        d = Delivery(
            customer_id=customer_id,
            delivery_date=delivery_date,
            jars_delivered=jars_delivered,
            jars_returned=jars_returned,
            delivery_staff=request.form.get('delivery_staff', '').strip(),
            remarks=request.form.get('remarks', '').strip(),
            created_by=current_user.id,
        )
        db.session.add(d)
        db.session.commit()
        flash('Delivery recorded!', 'success')
        if request.form.get('add_another'):
            return redirect(url_for('deliveries.add') + f'?date={delivery_date}')
        return redirect(url_for('deliveries.index', date=delivery_date.isoformat()))
    default_date = request.args.get('date', date.today().isoformat())
    preselect = request.args.get('customer', '')
    return render_template('deliveries/form.html', customers=customers,
        default_date=default_date, delivery=None, preselect=preselect)

@deliveries_bp.route('/bulk', methods=['GET', 'POST'])
@login_required
def bulk():
    today = date.today()
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name).all()
    if request.method == 'POST':
        delivery_date = date.fromisoformat(request.form['delivery_date'])
        count = 0
        for c in customers:
            delivered = int(request.form.get(f'delivered_{c.id}') or 0)
            returned = int(request.form.get(f'returned_{c.id}') or 0)
            if delivered > 0 or returned > 0:
                existing = Delivery.query.filter_by(customer_id=c.id, delivery_date=delivery_date).first()
                if existing:
                    existing.jars_delivered += delivered
                    existing.jars_returned += returned
                else:
                    d = Delivery(customer_id=c.id, delivery_date=delivery_date,
                        jars_delivered=delivered, jars_returned=returned,
                        delivery_staff=request.form.get('delivery_staff', '').strip(),
                        created_by=current_user.id)
                    db.session.add(d)
                count += 1
        db.session.commit()
        flash(f'Bulk delivery saved for {count} customers!', 'success')
        return redirect(url_for('deliveries.index', date=delivery_date.isoformat()))
    existing = {d.customer_id: d for d in Delivery.query.filter_by(delivery_date=today).all()}
    return render_template('deliveries/bulk.html', customers=customers, today=today, existing=existing)

@deliveries_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    d = Delivery.query.get_or_404(id)
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name).all()
    if request.method == 'POST':
        d.customer_id = int(request.form['customer_id'])
        d.delivery_date = date.fromisoformat(request.form['delivery_date'])
        d.jars_delivered = int(request.form.get('jars_delivered') or 0)
        d.jars_returned = int(request.form.get('jars_returned') or 0)
        d.delivery_staff = request.form.get('delivery_staff', '').strip()
        d.remarks = request.form.get('remarks', '').strip()
        db.session.commit()
        flash('Delivery updated!', 'success')
        return redirect(url_for('deliveries.index', date=d.delivery_date.isoformat()))
    return render_template('deliveries/form.html', customers=customers, delivery=d,
        default_date=d.delivery_date.isoformat(), preselect=str(d.customer_id))

@deliveries_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    d = Delivery.query.get_or_404(id)
    date_str = d.delivery_date.isoformat()
    db.session.delete(d)
    db.session.commit()
    flash('Delivery deleted.', 'success')
    return redirect(url_for('deliveries.index', date=date_str))

@deliveries_bp.route('/export/csv')
@login_required
def export_csv():
    from_date = request.args.get('from', (date.today() - timedelta(days=30)).isoformat())
    to_date = request.args.get('to', date.today().isoformat())
    deliveries = Delivery.query.filter(
        Delivery.delivery_date >= from_date,
        Delivery.delivery_date <= to_date
    ).order_by(Delivery.delivery_date).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Customer', 'Jars Delivered', 'Jars Returned', 'Net', 'Staff', 'Remarks'])
    for d in deliveries:
        writer.writerow([d.delivery_date, d.customer.company_name,
            d.jars_delivered, d.jars_returned, d.net_jars,
            d.delivery_staff or '', d.remarks or ''])
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=deliveries.csv'})
