from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.payment import db, Payment
from src.models.guest import Guest
from src.models.notification import Notification
from datetime import datetime, date, timedelta
import calendar

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/payments', methods=['GET'])
@jwt_required()
def get_payments():
    # Get query parameters for filtering
    status = request.args.get('status')
    guest_id = request.args.get('guest_id')
    due_before = request.args.get('due_before')
    due_after = request.args.get('due_after')
    
    # Base query
    query = Payment.query
    
    # Apply filters if provided
    if status:
        query = query.filter(Payment.status == status)
    if guest_id:
        query = query.filter(Payment.guest_id == guest_id)
    if due_before:
        try:
            due_before_date = datetime.strptime(due_before, '%Y-%m-%d').date()
            query = query.filter(Payment.due_date <= due_before_date)
        except ValueError:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_DATE_FORMAT',
                    'message': 'Date format should be YYYY-MM-DD'
                }
            }), 400
    if due_after:
        try:
            due_after_date = datetime.strptime(due_after, '%Y-%m-%d').date()
            query = query.filter(Payment.due_date >= due_after_date)
        except ValueError:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_DATE_FORMAT',
                    'message': 'Date format should be YYYY-MM-DD'
                }
            }), 400
    
    # Execute query and get results
    payments = query.all()
    payments_list = [payment.to_dict() for payment in payments]
    
    return jsonify({
        'success': True,
        'data': {
            'payments': payments_list
        },
        'message': 'Payments retrieved successfully'
    }), 200

@payment_bp.route('/payments/due', methods=['GET'])
@jwt_required()
def get_due_payments():
    # Get payments that are due but not paid
    payments = Payment.query.filter(
        Payment.status.in_(['unpaid', 'partial']),
        Payment.due_date >= date.today()
    ).all()
    
    payments_list = [payment.to_dict() for payment in payments]
    
    return jsonify({
        'success': True,
        'data': {
            'payments': payments_list
        },
        'message': 'Due payments retrieved successfully'
    }), 200

@payment_bp.route('/payments/overdue', methods=['GET'])
@jwt_required()
def get_overdue_payments():
    # Get payments that are overdue
    payments = Payment.query.filter(
        Payment.status.in_(['unpaid', 'partial']),
        Payment.due_date < date.today()
    ).all()
    
    payments_list = [payment.to_dict() for payment in payments]
    
    return jsonify({
        'success': True,
        'data': {
            'payments': payments_list
        },
        'message': 'Overdue payments retrieved successfully'
    }), 200

@payment_bp.route('/payments/<int:payment_id>', methods=['GET'])
@jwt_required()
def get_payment(payment_id):
    payment = Payment.query.get(payment_id)
    
    if not payment:
        return jsonify({
            'success': False,
            'error': {
                'code': 'PAYMENT_NOT_FOUND',
                'message': 'Payment not found'
            }
        }), 404
    
    return jsonify({
        'success': True,
        'data': {
            'payment': payment.to_dict()
        },
        'message': 'Payment retrieved successfully'
    }), 200

@payment_bp.route('/payments', methods=['POST'])
@jwt_required()
def create_payment():
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['guest_id', 'amount', 'payment_date', 'payment_type', 'status', 'due_date']
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
    
    # Validate payment type
    if data.get('payment_type') not in ['full', 'partial']:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_PAYMENT_TYPE',
                'message': 'Payment type must be either full or partial'
            }
        }), 400
    
    # Validate payment status
    if data.get('status') not in ['paid', 'unpaid', 'partial']:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_STATUS',
                'message': 'Status must be paid, unpaid, or partial'
            }
        }), 400
    
    # Parse dates
    try:
        payment_date = datetime.strptime(data.get('payment_date'), '%Y-%m-%d').date()
        due_date = datetime.strptime(data.get('due_date'), '%Y-%m-%d').date()
    except ValueError:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_DATE_FORMAT',
                'message': 'Date format should be YYYY-MM-DD'
            }
        }), 400
    
    # Create new payment
    new_payment = Payment(
        guest_id=data.get('guest_id'),
        amount=data.get('amount'),
        payment_date=payment_date,
        payment_type=data.get('payment_type'),
        status=data.get('status'),
        due_date=due_date
    )
    
    db.session.add(new_payment)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': {
            'payment': new_payment.to_dict()
        },
        'message': 'Payment created successfully'
    }), 201

@payment_bp.route('/payments/<int:payment_id>', methods=['PUT'])
@jwt_required()
def update_payment(payment_id):
    payment = Payment.query.get(payment_id)
    
    if not payment:
        return jsonify({
            'success': False,
            'error': {
                'code': 'PAYMENT_NOT_FOUND',
                'message': 'Payment not found'
            }
        }), 404
    
    data = request.get_json()
    
    # Update fields if provided
    if data.get('amount'):
        payment.amount = data.get('amount')
    
    if data.get('payment_type'):
        if data.get('payment_type') not in ['full', 'partial']:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_PAYMENT_TYPE',
                    'message': 'Payment type must be either full or partial'
                }
            }), 400
        payment.payment_type = data.get('payment_type')
    
    if data.get('status'):
        if data.get('status') not in ['paid', 'unpaid', 'partial']:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_STATUS',
                    'message': 'Status must be paid, unpaid, or partial'
                }
            }), 400
        payment.status = data.get('status')
    
    if data.get('payment_date'):
        try:
            payment_date = datetime.strptime(data.get('payment_date'), '%Y-%m-%d').date()
            payment.payment_date = payment_date
        except ValueError:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_DATE_FORMAT',
                    'message': 'Date format should be YYYY-MM-DD'
                }
            }), 400
    
    if data.get('due_date'):
        try:
            due_date = datetime.strptime(data.get('due_date'), '%Y-%m-%d').date()
            payment.due_date = due_date
        except ValueError:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_DATE_FORMAT',
                    'message': 'Date format should be YYYY-MM-DD'
                }
            }), 400
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': {
            'payment': payment.to_dict()
        },
        'message': 'Payment updated successfully'
    }), 200

@payment_bp.route('/payments/<int:payment_id>', methods=['DELETE'])
@jwt_required()
def delete_payment(payment_id):
    # Only admins can delete payments
    current_user = get_jwt_identity()
    if current_user.get('role') != 'admin':
        return jsonify({
            'success': False,
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'Only admins can delete payments'
            }
        }), 403
    
    payment = Payment.query.get(payment_id)
    
    if not payment:
        return jsonify({
            'success': False,
            'error': {
                'code': 'PAYMENT_NOT_FOUND',
                'message': 'Payment not found'
            }
        }), 404
    
    db.session.delete(payment)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Payment deleted successfully'
    }), 200

@payment_bp.route('/payments/guest/<int:guest_id>', methods=['GET'])
@jwt_required()
def get_guest_payments(guest_id):
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
    
    payments = Payment.query.filter_by(guest_id=guest_id).all()
    payments_list = [payment.to_dict() for payment in payments]
    
    return jsonify({
        'success': True,
        'data': {
            'payments': payments_list
        },
        'message': 'Guest payments retrieved successfully'
    }), 200

@payment_bp.route('/payments/generate-monthly', methods=['POST'])
@jwt_required()
def generate_monthly_payments():
    # Only admins can generate monthly payments
    current_user = get_jwt_identity()
    if current_user.get('role') != 'admin':
        return jsonify({
            'success': False,
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'Only admins can generate monthly payments'
            }
        }), 403
    
    data = request.get_json()
    
    # Validate month and year
    if not data or not data.get('month') or not data.get('year'):
        return jsonify({
            'success': False,
            'error': {
                'code': 'MISSING_FIELDS',
                'message': 'Month and year are required'
            }
        }), 400
    
    try:
        month = int(data.get('month'))
        year = int(data.get('year'))
        
        if month < 1 or month > 12:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_MONTH',
                    'message': 'Month must be between 1 and 12'
                }
            }), 400
    except ValueError:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_FORMAT',
                'message': 'Month and year must be integers'
            }
        }), 400
    
    # Get all active guests
    active_guests = Guest.query.filter_by(status='active').all()
    
    # Calculate due date (1st of the month)
    due_date = date(year, month, 1)
    
    # Get last day of the month for payment date
    _, last_day = calendar.monthrange(year, month)
    payment_date = date(year, month, last_day)
    
    # Generate payments for each active guest
    generated_payments = []
    
    for guest in active_guests:
        # Check if payment already exists for this month and guest
        existing_payment = Payment.query.filter(
            Payment.guest_id == guest.id,
            Payment.due_date == due_date
        ).first()
        
        if not existing_payment:
            new_payment = Payment(
                guest_id=guest.id,
                amount=guest.rent_amount,
                payment_date=payment_date,
                payment_type='full',
                status='unpaid',
                due_date=due_date
            )
            
            db.session.add(new_payment)
            generated_payments.append(new_payment)
    
    db.session.commit()
    
    # Convert to dict for response
    generated_list = [payment.to_dict() for payment in generated_payments]
    
    return jsonify({
        'success': True,
        'data': {
            'generated': generated_list
        },
        'message': f'Generated {len(generated_payments)} payments for {month}/{year}'
    }), 201
