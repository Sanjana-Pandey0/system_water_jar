from app import db
from datetime import datetime

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), nullable=False)
    alt_mobile = db.Column(db.String(15))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pin_code = db.Column(db.String(10))
    gst_number = db.Column(db.String(20))
    jar_rate = db.Column(db.Float, nullable=False, default=30.0)
    security_deposit = db.Column(db.Float, default=0.0)
    opening_jar_balance = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    deliveries = db.relationship('Delivery', backref='customer', lazy='dynamic', cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='customer', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def total_delivered(self):
        from sqlalchemy import func
        result = db.session.query(func.sum(Delivery_import().jars_delivered)).filter_by(customer_id=self.id).scalar()
        return (result or 0) + self.opening_jar_balance

    def get_jar_balance(self):
        from app.models.delivery import Delivery
        from sqlalchemy import func
        delivered = db.session.query(func.sum(Delivery.jars_delivered)).filter_by(customer_id=self.id).scalar() or 0
        returned = db.session.query(func.sum(Delivery.jars_returned)).filter_by(customer_id=self.id).scalar() or 0
        return self.opening_jar_balance + delivered - returned

    def get_outstanding_amount(self):
        from app.models.invoice import Invoice
        total = db.session.query(db.func.sum(Invoice.balance_due)).filter_by(
            customer_id=self.id, status='unpaid').scalar() or 0
        partial = db.session.query(db.func.sum(Invoice.balance_due)).filter_by(
            customer_id=self.id, status='partial').scalar() or 0
        return total + partial

    def __repr__(self):
        return f'<Customer {self.company_name}>'
