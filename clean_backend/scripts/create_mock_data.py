import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random
import json

# Create a Flask app context for database operations
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.getenv('DB_USERNAME', 'postgres')}:{os.getenv('DB_PASSWORD', 'postgres')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'pg_management')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create a new SQLAlchemy instance for this script
db = SQLAlchemy(app)

# Define models here to avoid circular imports
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin or manager
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Room(db.Model):
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(20), unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # available or occupied
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Guest(db.Model):
    __tablename__ = 'guests'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(20), nullable=False)
    id_proof_url = db.Column(db.String(255), nullable=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=True)
    rent_amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # active or inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guests.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.Date, nullable=True)
    payment_type = db.Column(db.String(20), nullable=False)  # full or partial
    status = db.Column(db.String(20), nullable=False)  # paid, unpaid, or partial
    due_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class RoomHistory(db.Model):
    __tablename__ = 'room_history'
    
    id = db.Column(db.Integer, primary_key=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guests.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guests.id'), nullable=False)
    notification_date = db.Column(db.DateTime, nullable=False)
    notification_type = db.Column(db.String(20), nullable=False)  # rent_due or overdue
    channel = db.Column(db.String(20), nullable=False)  # email or sms
    status = db.Column(db.String(20), nullable=False)  # sent or failed
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Sample data
room_numbers = ["101", "102", "103", "104", "105", "201", "202", "203", "204", "205"]
guest_names = [
    "John Smith", "Emma Johnson", "Michael Brown", "Sophia Williams", "James Jones",
    "Olivia Davis", "Robert Miller", "Ava Wilson", "David Moore", "Isabella Taylor",
    "Joseph Anderson", "Mia Thomas", "Charles Jackson", "Charlotte White", "Daniel Harris"
]
contact_numbers = [
    "9876543210", "8765432109", "7654321098", "6543210987", "5432109876",
    "4321098765", "3210987654", "2109876543", "1098765432", "0987654321",
    "9876543211", "8765432100", "7654321099", "6543210988", "5432109877"
]

def create_mock_data():
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Clear existing data
        Notification.query.delete()
        Payment.query.delete()
        RoomHistory.query.delete()
        Guest.query.delete()
        Room.query.delete()
        User.query.delete()
        
        # Create admin and manager users
        admin = User(
            email="admin@pgmanagement.com",
            password_hash=generate_password_hash("admin123"),
            full_name="Admin User",
            role="admin"
        )
        
        manager = User(
            email="manager@pgmanagement.com",
            password_hash=generate_password_hash("manager123"),
            full_name="Manager User",
            role="manager"
        )
        
        db.session.add(admin)
        db.session.add(manager)
        
        # Create rooms
        rooms = []
        for room_number in room_numbers:
            capacity = random.choice([1, 2, 3])
            status = random.choice(["available", "occupied"])
            room = Room(
                room_number=room_number,
                capacity=capacity,
                status=status,
                notes=f"Room {room_number} with capacity for {capacity} people"
            )
            db.session.add(room)
            rooms.append(room)
        
        db.session.commit()
        
        # Create guests
        guests = []
        for i, name in enumerate(guest_names):
            # Assign to a random room
            room = random.choice(rooms)
            
            # Set check-in date between 1-6 months ago
            days_ago = random.randint(30, 180)
            check_in_date = datetime.now() - timedelta(days=days_ago)
            
            # Some guests have checked out
            status = "active"
            check_out_date = None
            if i < 3:  # Make 3 guests inactive
                status = "inactive"
                check_out_date = check_in_date + timedelta(days=random.randint(30, 90))
            
            rent_amount = random.choice([5000, 6000, 7000, 8000, 9000])
            
            guest = Guest(
                full_name=name,
                contact_number=contact_numbers[i],
                id_proof_url=f"https://example.com/id/{i+1}.jpg",
                room_id=room.id,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                rent_amount=rent_amount,
                status=status
            )
            
            db.session.add(guest)
            guests.append(guest)
            
            # Update room status if guest is active
            if status == "active":
                room.status = "occupied"
        
        db.session.commit()
        
        # Create room history
        for guest in guests:
            room_history = RoomHistory(
                guest_id=guest.id,
                room_id=guest.room_id,
                check_in_date=guest.check_in_date,
                check_out_date=guest.check_out_date
            )
            db.session.add(room_history)
        
        db.session.commit()
        
        # Create payments
        for guest in guests:
            # Skip inactive guests
            if guest.status == "inactive":
                continue
                
            # Create 3-6 payments for each active guest
            num_payments = random.randint(3, 6)
            for j in range(num_payments):
                # Payment date is monthly from check-in
                payment_date = guest.check_in_date + timedelta(days=30 * j)
                
                # Due date is a few days before payment date
                due_date = payment_date - timedelta(days=5)
                
                # If payment date is in the future, mark as unpaid
                status = "paid"
                if payment_date > datetime.now():
                    status = "unpaid"
                    payment_date = None
                # Some random payments are partial
                elif random.random() < 0.2:
                    status = "partial"
                
                # Amount is usually the rent amount, but can be partial
                amount = guest.rent_amount
                if status == "partial":
                    amount = round(guest.rent_amount * random.uniform(0.4, 0.8))
                
                payment = Payment(
                    guest_id=guest.id,
                    amount=amount,
                    payment_date=payment_date,
                    payment_type="full" if status != "partial" else "partial",
                    status=status,
                    due_date=due_date
                )
                db.session.add(payment)
        
        db.session.commit()
        
        # Create notifications
        for guest in guests:
            # Skip inactive guests
            if guest.status == "inactive":
                continue
                
            # Create 2-4 notifications for each active guest
            num_notifications = random.randint(2, 4)
            for j in range(num_notifications):
                # Notification date is random
                notification_date = datetime.now() - timedelta(days=random.randint(1, 60))
                
                # Type is either rent_due or overdue
                notification_type = random.choice(["rent_due", "overdue"])
                
                # Channel is either email or sms
                channel = random.choice(["email", "sms"])
                
                # Status is either sent or failed
                status = random.choice(["sent", "failed"])
                
                notification = Notification(
                    guest_id=guest.id,
                    notification_date=notification_date,
                    notification_type=notification_type,
                    channel=channel,
                    status=status,
                    content=f"Notification for {guest.full_name} about {notification_type}"
                )
                db.session.add(notification)
        
        db.session.commit()
        
        print("Mock data created successfully!")
        
        # Return summary of created data
        return {
            "users": User.query.count(),
            "rooms": Room.query.count(),
            "guests": Guest.query.count(),
            "payments": Payment.query.count(),
            "room_history": RoomHistory.query.count(),
            "notifications": Notification.query.count()
        }

if __name__ == "__main__":
    summary = create_mock_data()
    print(json.dumps(summary, indent=2))
