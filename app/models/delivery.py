from app import db
from datetime import datetime, date

class Delivery(db.Model):
    __tablename__ = 'deliveries'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    delivery_date = db.Column(db.Date, nullable=False, default=date.today)
    jars_delivered = db.Column(db.Integer, nullable=False, default=0)
    jars_returned = db.Column(db.Integer, nullable=False, default=0)
    delivery_staff = db.Column(db.String(100))
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    @property
    def net_jars(self):
        return self.jars_delivered - self.jars_returned

    def __repr__(self):
        return f'<Delivery {self.id} on {self.delivery_date}>'
