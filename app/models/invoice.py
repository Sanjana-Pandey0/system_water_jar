from app import db
from datetime import datetime, date
import calendar

class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(30), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    invoice_date = db.Column(db.Date, nullable=False, default=date.today)
    billing_month = db.Column(db.Integer, nullable=False)   # 1-12
    billing_year = db.Column(db.Integer, nullable=False)
    total_jars = db.Column(db.Integer, nullable=False, default=0)
    rate_per_jar = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    gst_percent = db.Column(db.Float, default=0.0)
    gst_amount = db.Column(db.Float, default=0.0)
    grand_total = db.Column(db.Float, nullable=False, default=0.0)
    paid_amount = db.Column(db.Float, default=0.0)
    balance_due = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='unpaid')  # unpaid, partial, paid
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    payments = db.relationship('Payment', backref='invoice', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def billing_month_name(self):
        return calendar.month_name[self.billing_month]

    @staticmethod
    def generate_invoice_number(year=None):
        if year is None:
            year = date.today().year
        last = Invoice.query.filter(
            Invoice.invoice_number.like(f'INV-{year}-%')
        ).order_by(Invoice.id.desc()).first()
        if last:
            try:
                seq = int(last.invoice_number.split('-')[-1]) + 1
            except:
                seq = 1
        else:
            seq = 1
        return f'INV-{year}-{seq:04d}'

    def update_status(self):
        if self.paid_amount <= 0:
            self.status = 'unpaid'
        elif self.paid_amount >= self.grand_total:
            self.status = 'paid'
            self.balance_due = 0
        else:
            self.status = 'partial'
        self.balance_due = max(0, self.grand_total - self.paid_amount)

    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'
