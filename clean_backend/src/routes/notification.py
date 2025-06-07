from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.notification import db, Notification
from src.models.guest import Guest
from src.models.payment import Payment
from datetime import datetime, date, timedelta
import os

notification_bp = Blueprint('notification', __name__)

@notification_bp.route('/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    # Get query parameters for filtering
    status = request.args.get('status')
    guest_id = request.args.get('guest_id')
    type = request.args.get('type')
    
    # Base query
    query = Notification.query
    
    # Apply filters if provided
    if status:
        query = query.filter(Notification.status == status)
    if guest_id:
        query = query.filter(Notification.guest_id == guest_id)
    if type:
        query = query.filter(Notification.type == type)
    
    # Execute query and get results
    notifications = query.all()
    notifications_list = [notification.to_dict() for notification in notifications]
    
    return jsonify({
        'success': True,
        'data': {
            'notifications': notifications_list
        },
        'message': 'Notifications retrieved successfully'
    }), 200

@notification_bp.route('/notifications/<int:notification_id>', methods=['GET'])
@jwt_required()
def get_notification(notification_id):
    notification = Notification.query.get(notification_id)
    
    if not notification:
        return jsonify({
            'success': False,
            'error': {
                'code': 'NOTIFICATION_NOT_FOUND',
                'message': 'Notification not found'
            }
        }), 404
    
    return jsonify({
        'success': True,
        'data': {
            'notification': notification.to_dict()
        },
        'message': 'Notification retrieved successfully'
    }), 200

@notification_bp.route('/notifications', methods=['POST'])
@jwt_required()
def create_notification():
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['guest_id', 'type', 'message']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'MISSING_FIELDS',
                    'message': f'{field} is required'
                }
            }), 400
    
    # Validate guest exists
    guest = Guest.query.get(data.get('guest_id'))
    if not guest:
        return jsonify({
            'success': False,
            'error': {
                'code': 'GUEST_NOT_FOUND',
                'message': 'Guest not found'
            }
        }), 404
    
    # Validate payment exists if payment_id is provided
    if data.get('payment_id'):
        payment = Payment.query.get(data.get('payment_id'))
        if not payment:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'PAYMENT_NOT_FOUND',
                    'message': 'Payment not found'
                }
            }), 404
    
    # Validate notification type
    if data.get('type') not in ['sms', 'email']:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_TYPE',
                'message': 'Type must be either sms or email'
            }
        }), 400
    
    # Create new notification
    new_notification = Notification(
        guest_id=data.get('guest_id'),
        payment_id=data.get('payment_id'),
        type=data.get('type'),
        message=data.get('message'),
        status='pending'
    )
    
    db.session.add(new_notification)
    db.session.commit()
    
    # In a real application, we would send the notification here
    # For now, we'll simulate sending and update the status
    send_notification(new_notification)
    
    return jsonify({
        'success': True,
        'data': {
            'notification': new_notification.to_dict()
        },
        'message': 'Notification created successfully'
    }), 201

@notification_bp.route('/notifications/<int:notification_id>', methods=['PUT'])
@jwt_required()
def update_notification(notification_id):
    notification = Notification.query.get(notification_id)
    
    if not notification:
        return jsonify({
            'success': False,
            'error': {
                'code': 'NOTIFICATION_NOT_FOUND',
                'message': 'Notification not found'
            }
        }), 404
    
    data = request.get_json()
    
    # Update fields if provided
    if data.get('type'):
        if data.get('type') not in ['sms', 'email']:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_TYPE',
                    'message': 'Type must be either sms or email'
                }
            }), 400
        notification.type = data.get('type')
    
    if data.get('message'):
        notification.message = data.get('message')
    
    if data.get('status'):
        if data.get('status') not in ['sent', 'failed', 'pending']:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_STATUS',
                    'message': 'Status must be sent, failed, or pending'
                }
            }), 400
        notification.status = data.get('status')
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': {
            'notification': notification.to_dict()
        },
        'message': 'Notification updated successfully'
    }), 200

@notification_bp.route('/notifications/<int:notification_id>', methods=['DELETE'])
@jwt_required()
def delete_notification(notification_id):
    # Only admins can delete notifications
    current_user = get_jwt_identity()
    if current_user.get('role') != 'admin':
        return jsonify({
            'success': False,
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'Only admins can delete notifications'
            }
        }), 403
    
    notification = Notification.query.get(notification_id)
    
    if not notification:
        return jsonify({
            'success': False,
            'error': {
                'code': 'NOTIFICATION_NOT_FOUND',
                'message': 'Notification not found'
            }
        }), 404
    
    db.session.delete(notification)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Notification deleted successfully'
    }), 200

@notification_bp.route('/notifications/guest/<int:guest_id>', methods=['GET'])
@jwt_required()
def get_guest_notifications(guest_id):
    # Validate guest exists
    guest = Guest.query.get(guest_id)
    if not guest:
        return jsonify({
            'success': False,
            'error': {
                'code': 'GUEST_NOT_FOUND',
                'message': 'Guest not found'
            }
        }), 404
    
    notifications = Notification.query.filter_by(guest_id=guest_id).all()
    notifications_list = [notification.to_dict() for notification in notifications]
    
    return jsonify({
        'success': True,
        'data': {
            'notifications': notifications_list
        },
        'message': 'Guest notifications retrieved successfully'
    }), 200

@notification_bp.route('/notifications/send-reminders', methods=['POST'])
@jwt_required()
def send_reminders():
    # Only admins can send reminders
    current_user = get_jwt_identity()
    if current_user.get('role') != 'admin':
        return jsonify({
            'success': False,
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'Only admins can send reminders'
            }
        }), 403
    
    data = request.get_json()
    
    # Default to 3 days before due date if not specified
    days_before = data.get('days_before', 3) if data else 3
    
    # Calculate the target due date
    target_date = date.today() + timedelta(days=days_before)
    
    # Find payments due on the target date
    due_payments = Payment.query.filter(
        Payment.status.in_(['unpaid', 'partial']),
        Payment.due_date == target_date
    ).all()
    
    sent_notifications = []
    
    for payment in due_payments:
        guest = Guest.query.get(payment.guest_id)
        
        if guest and guest.status == 'active':
            # Create reminder message
            message = f"Dear {guest.full_name}, your rent payment of {payment.amount} is due on {payment.due_date.strftime('%Y-%m-%d')}. Please make the payment on time."
            
            # Create notification for SMS
            sms_notification = Notification(
                guest_id=guest.id,
                payment_id=payment.id,
                type='sms',
                message=message,
                status='pending'
            )
            
            # Create notification for Email
            email_notification = Notification(
                guest_id=guest.id,
                payment_id=payment.id,
                type='email',
                message=message,
                status='pending'
            )
            
            db.session.add(sms_notification)
            db.session.add(email_notification)
            
            # In a real application, we would send the notifications here
            # For now, we'll simulate sending and update the status
            send_notification(sms_notification)
            send_notification(email_notification)
            
            sent_notifications.extend([sms_notification, email_notification])
    
    db.session.commit()
    
    # Convert to dict for response
    sent_list = [notification.to_dict() for notification in sent_notifications]
    
    return jsonify({
        'success': True,
        'data': {
            'sent': sent_list
        },
        'message': f'Sent {len(sent_notifications)} reminders for payments due in {days_before} days'
    }), 200

@notification_bp.route('/notifications/send-overdue', methods=['POST'])
@jwt_required()
def send_overdue_alerts():
    # Only admins can send overdue alerts
    current_user = get_jwt_identity()
    if current_user.get('role') != 'admin':
        return jsonify({
            'success': False,
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'Only admins can send overdue alerts'
            }
        }), 403
    
    # Find overdue payments
    overdue_payments = Payment.query.filter(
        Payment.status.in_(['unpaid', 'partial']),
        Payment.due_date < date.today()
    ).all()
    
    sent_notifications = []
    
    for payment in overdue_payments:
        guest = Guest.query.get(payment.guest_id)
        
        if guest and guest.status == 'active':
            # Calculate days overdue
            days_overdue = (date.today() - payment.due_date).days
            
            # Create overdue message
            message = f"URGENT: Dear {guest.full_name}, your rent payment of {payment.amount} is overdue by {days_overdue} days. Please make the payment immediately to avoid any inconvenience."
            
            # Create notification for SMS
            sms_notification = Notification(
                guest_id=guest.id,
                payment_id=payment.id,
                type='sms',
                message=message,
                status='pending'
            )
            
            # Create notification for Email
            email_notification = Notification(
                guest_id=guest.id,
                payment_id=payment.id,
                type='email',
                message=message,
                status='pending'
            )
            
            db.session.add(sms_notification)
            db.session.add(email_notification)
            
            # In a real application, we would send the notifications here
            # For now, we'll simulate sending and update the status
            send_notification(sms_notification)
            send_notification(email_notification)
            
            sent_notifications.extend([sms_notification, email_notification])
    
    db.session.commit()
    
    # Convert to dict for response
    sent_list = [notification.to_dict() for notification in sent_notifications]
    
    return jsonify({
        'success': True,
        'data': {
            'sent': sent_list
        },
        'message': f'Sent {len(sent_notifications)} overdue payment alerts'
    }), 200

# Helper function to simulate sending notifications
def send_notification(notification):
    # In a real application, this would integrate with Twilio for SMS
    # or SendGrid for email
    
    # For now, we'll just simulate sending and update the status
    if notification.type == 'sms':
        # Simulate Twilio SMS integration
        # twilio_client = Client(account_sid, auth_token)
        # message = twilio_client.messages.create(
        #     body=notification.message,
        #     from_='+1234567890',
        #     to='+1' + notification.guest.contact_number
        # )
        
        # Simulate success
        notification.status = 'sent'
        notification.sent_at = datetime.utcnow()
    
    elif notification.type == 'email':
        # Simulate SendGrid email integration
        # sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
        # from_email = Email("noreply@pgmanagement.com")
        # to_email = To(notification.guest.email)
        # subject = "PG Management Notification"
        # content = Content("text/plain", notification.message)
        # mail = Mail(from_email, to_email, subject, content)
        # response = sg.client.mail.send.post(request_body=mail.get())
        
        # Simulate success
        notification.status = 'sent'
        notification.sent_at = datetime.utcnow()
    
    db.session.commit()
    
    return notification
