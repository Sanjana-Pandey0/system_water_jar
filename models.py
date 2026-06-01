from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120))
    role = db.Column(db.String(20), default='admin')  # admin, staff
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    customer_code = db.Column(db.String(20), unique=True, nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(120))
    mobile = db.Column(db.String(20), nullable=False)
    alternate_mobile = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    city = db.Column(db.String(80))
    state = db.Column(db.String(80))
    pin_code = db.Column(db.String(10))
    gst_number = db.Column(db.String(20))
    jar_rate = db.Column(db.Float, default=60.0)
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
        result = db.session.query(db.func.sum(Delivery.jars_delivered)).filter_by(customer_id=self.id).scalar()
        return (result or 0) + self.opening_jar_balance

    @property
    def total_returned(self):
        result = db.session.query(db.func.sum(Delivery.jars_returned)).filter_by(customer_id=self.id).scalar()
        return result or 0

    @property
    def pending_jars(self):
        return self.total_delivered - self.total_returned

    @property
    def total_outstanding(self):
        result = db.session.query(db.func.sum(Invoice.balance_amount)).filter_by(
            customer_id=self.id).scalar()
        return result or 0.0

    def __repr__(self):
        return f'<Customer {self.company_name}>'


class Delivery(db.Model):
    __tablename__ = 'deliveries'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    delivery_date = db.Column(db.Date, nullable=False, default=date.today)
    jars_delivered = db.Column(db.Integer, default=0)
    jars_returned = db.Column(db.Integer, default=0)
    delivery_staff = db.Column(db.String(120))
    remarks = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def net_jars(self):
        return self.jars_delivered - self.jars_returned

    def __repr__(self):
        return f'<Delivery {self.delivery_date} - {self.customer_id}>'


class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(30), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    invoice_date = db.Column(db.Date, nullable=False, default=date.today)
    billing_month = db.Column(db.Integer, nullable=False)
    billing_year = db.Column(db.Integer, nullable=False)
    total_jars = db.Column(db.Integer, default=0)
    rate_per_jar = db.Column(db.Float, default=0.0)
    subtotal = db.Column(db.Float, default=0.0)
    gst_percentage = db.Column(db.Float, default=0.0)
    gst_amount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0)
    paid_amount = db.Column(db.Float, default=0.0)
    balance_amount = db.Column(db.Float, default=0.0)
    payment_status = db.Column(db.String(20), default='unpaid')  # paid, unpaid, partial
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    payments = db.relationship('Payment', backref='invoice', lazy='dynamic', cascade='all, delete-orphan')

    def update_payment_status(self):
        total_paid = db.session.query(db.func.sum(Payment.amount)).filter_by(invoice_id=self.id).scalar() or 0
        self.paid_amount = total_paid
        self.balance_amount = self.total_amount - total_paid
        if self.balance_amount <= 0:
            self.payment_status = 'paid'
            self.balance_amount = 0
        elif self.paid_amount > 0:
            self.payment_status = 'partial'
        else:
            self.payment_status = 'unpaid'

    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    payment_date = db.Column(db.Date, nullable=False, default=date.today)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(30), default='cash')  # cash, bank_transfer, upi, cheque
    reference_number = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Payment {self.amount} for Invoice {self.invoice_id}>'


class BusinessSettings(db.Model):
    __tablename__ = 'business_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get(cls, key, default=None):
        record = cls.query.filter_by(key=key).first()
        return record.value if record else default

    @classmethod
    def set(cls, key, value):
        record = cls.query.filter_by(key=key).first()
        if record:
            record.value = str(value)
        else:
            record = cls(key=key, value=str(value))
            db.session.add(record)
        db.session.commit()
