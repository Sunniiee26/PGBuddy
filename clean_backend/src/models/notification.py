from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

from src.models.guest import db
from src.models.payment import Payment

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guests.id'), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=True)
    type = db.Column(db.String(50), nullable=False)  # 'sms' or 'email'
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False)  # 'sent', 'failed', or 'pending'
    sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'guest_id': self.guest_id,
            'payment_id': self.payment_id,
            'type': self.type,
            'message': self.message,
            'status': self.status,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
