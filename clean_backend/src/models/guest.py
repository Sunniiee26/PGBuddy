from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

from src.models.room import db

class Guest(db.Model):
    __tablename__ = 'guests'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    contact_number = db.Column(db.String(50), nullable=False)
    id_proof_url = db.Column(db.String(255), nullable=False)
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=True)
    rent_amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(50), nullable=False)  # 'active' or 'inactive'
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    payments = db.relationship('Payment', backref='guest', lazy=True)
    room_history = db.relationship('RoomHistory', backref='guest', lazy=True)
    notifications = db.relationship('Notification', backref='guest', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'contact_number': self.contact_number,
            'id_proof_url': self.id_proof_url,
            'check_in_date': self.check_in_date.isoformat() if self.check_in_date else None,
            'check_out_date': self.check_out_date.isoformat() if self.check_out_date else None,
            'rent_amount': float(self.rent_amount),
            'status': self.status,
            'room_id': self.room_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
