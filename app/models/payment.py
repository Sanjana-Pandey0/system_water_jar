from app import db
from datetime import datetime, date

class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    payment_date = db.Column(db.Date, nullable=False, default=date.today)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50), default='cash')  # cash, upi, bank, cheque
    reference = db.Column(db.String(100))  # cheque/transaction number
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    customer = db.relationship('Customer', foreign_keys=[customer_id])

    def __repr__(self):
        return f'<Payment {self.id} ₹{self.amount}>'
