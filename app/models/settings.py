from app import db
from datetime import datetime

class Settings(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get(key, default=None):
        s = Settings.query.filter_by(key=key).first()
        return s.value if s else default

    @staticmethod
    def set(key, value):
        s = Settings.query.filter_by(key=key).first()
        if s:
            s.value = str(value)
        else:
            s = Settings(key=key, value=str(value))
            db.session.add(s)
        db.session.commit()
