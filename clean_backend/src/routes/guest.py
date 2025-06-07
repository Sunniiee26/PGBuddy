from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.guest import db, Guest
from src.models.room import Room
from src.models.room_history import RoomHistory
from datetime import datetime, date

guest_bp = Blueprint('guest', __name__)

@guest_bp.route('/guests', methods=['GET'])
@jwt_required()
def get_guests():
    # Get query parameters for filtering
    status = request.args.get('status')
    room_id = request.args.get('room_id')
    check_in_after = request.args.get('check_in_after')
    check_in_before = request.args.get('check_in_before')
    
    # Base query
    query = Guest.query
    
    # Apply filters if provided
    if status:
        query = query.filter(Guest.status == status)
    if room_id:
        query = query.filter(Guest.room_id == room_id)
    if check_in_after:
        try:
            check_in_after_date = datetime.strptime(check_in_after, '%Y-%m-%d').date()
            query = query.filter(Guest.check_in_date >= check_in_after_date)
        except ValueError:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_DATE_FORMAT',
                    'message': 'Date format should be YYYY-MM-DD'
                }
            }), 400
    if check_in_before:
        try:
            check_in_before_date = datetime.strptime(check_in_before, '%Y-%m-%d').date()
            query = query.filter(Guest.check_in_date <= check_in_before_date)
        except ValueError:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_DATE_FORMAT',
                    'message': 'Date format should be YYYY-MM-DD'
                }
            }), 400
    
    # Execute query and get results
    guests = query.all()
    guests_list = [guest.to_dict() for guest in guests]
    
    return jsonify({
        'success': True,
        'data': {
            'guests': guests_list
        },
        'message': 'Guests retrieved successfully'
    }), 200

@guest_bp.route('/guests/active', methods=['GET'])
@jwt_required()
def get_active_guests():
    guests = Guest.query.filter_by(status='active').all()
    guests_list = [guest.to_dict() for guest in guests]
    
    return jsonify({
        'success': True,
        'data': {
            'guests': guests_list
        },
        'message': 'Active guests retrieved successfully'
    }), 200

@guest_bp.route('/guests/inactive', methods=['GET'])
@jwt_required()
def get_inactive_guests():
    guests = Guest.query.filter_by(status='inactive').all()
    guests_list = [guest.to_dict() for guest in guests]
    
    return jsonify({
        'success': True,
        'data': {
            'guests': guests_list
        },
        'message': 'Inactive guests retrieved successfully'
    }), 200

@guest_bp.route('/guests/<int:guest_id>', methods=['GET'])
@jwt_required()
def get_guest(guest_id):
    guest = Guest.query.get(guest_id)
    
    if not guest:
        return jsonify({
            'success': False,
            'error': {
                'code': 'GUEST_NOT_FOUND',
                'message': 'Guest not found'
            }
        }), 404
    
    return jsonify({
        'success': True,
        'data': {
            'guest': guest.to_dict()
        },
        'message': 'Guest retrieved successfully'
    }), 200

@guest_bp.route('/guests', methods=['POST'])
@jwt_required()
def create_guest():
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['full_name', 'contact_number', 'id_proof_url', 'check_in_date', 'rent_amount', 'room_id']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'MISSING_FIELDS',
                    'message': f'{field} is required'
                }
            }), 400
    
    # Validate room exists
    room = Room.query.get(data.get('room_id'))
    if not room:
        return jsonify({
            'success': False,
            'error': {
                'code': 'ROOM_NOT_FOUND',
                'message': 'Room not found'
            }
        }), 404
    
    # Check if room is available
    if room.status == 'occupied':
        # Check if room has capacity
        active_guests_count = Guest.query.filter_by(room_id=room.id, status='active').count()
        if active_guests_count >= room.capacity:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'ROOM_FULL',
                    'message': 'Room is at full capacity'
                }
            }), 400
    
    # Parse check-in date
    try:
        check_in_date = datetime.strptime(data.get('check_in_date'), '%Y-%m-%d').date()
    except ValueError:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_DATE_FORMAT',
                'message': 'Date format should be YYYY-MM-DD'
            }
        }), 400
    
    # Create new guest
    new_guest = Guest(
        full_name=data.get('full_name'),
        contact_number=data.get('contact_number'),
        id_proof_url=data.get('id_proof_url'),
        check_in_date=check_in_date,
        rent_amount=data.get('rent_amount'),
        status='active',
        room_id=data.get('room_id')
    )
    
    # Create room history entry
    room_history = RoomHistory(
        room_id=data.get('room_id'),
        guest_id=new_guest.id,
        start_date=check_in_date
    )
    
    # Update room status if it was available
    if room.status == 'available':
        room.status = 'occupied'
    
    db.session.add(new_guest)
    db.session.add(room_history)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': {
            'guest': new_guest.to_dict()
        },
        'message': 'Guest created successfully'
    }), 201

@guest_bp.route('/guests/<int:guest_id>', methods=['PUT'])
@jwt_required()
def update_guest(guest_id):
    guest = Guest.query.get(guest_id)
    
    if not guest:
        return jsonify({
            'success': False,
            'error': {
                'code': 'GUEST_NOT_FOUND',
                'message': 'Guest not found'
            }
        }), 404
    
    data = request.get_json()
    
    # Update fields if provided
    if data.get('full_name'):
        guest.full_name = data.get('full_name')
    
    if data.get('contact_number'):
        guest.contact_number = data.get('contact_number')
    
    if data.get('id_proof_url'):
        guest.id_proof_url = data.get('id_proof_url')
    
    if data.get('rent_amount'):
        guest.rent_amount = data.get('rent_amount')
    
    if data.get('status'):
        if data.get('status') not in ['active', 'inactive']:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_STATUS',
                    'message': 'Status must be either active or inactive'
                }
            }), 400
        
        # If changing from active to inactive, set check_out_date if not provided
        if guest.status == 'active' and data.get('status') == 'inactive' and not data.get('check_out_date'):
            guest.check_out_date = date.today()
            
            # Update room history
            room_history = RoomHistory.query.filter_by(
                guest_id=guest.id,
                room_id=guest.room_id,
                end_date=None
            ).first()
            
            if room_history:
                room_history.end_date = date.today()
            
            # Check if room is now empty
            active_guests_count = Guest.query.filter_by(room_id=guest.room_id, status='active').count()
            if active_guests_count <= 1:  # Only this guest is active
                room = Room.query.get(guest.room_id)
                if room:
                    room.status = 'available'
        
        guest.status = data.get('status')
    
    if data.get('check_in_date'):
        try:
            check_in_date = datetime.strptime(data.get('check_in_date'), '%Y-%m-%d').date()
            guest.check_in_date = check_in_date
            
            # Update room history
            room_history = RoomHistory.query.filter_by(
                guest_id=guest.id,
                room_id=guest.room_id,
                end_date=None
            ).first()
            
            if room_history:
                room_history.start_date = check_in_date
        except ValueError:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_DATE_FORMAT',
                    'message': 'Date format should be YYYY-MM-DD'
                }
            }), 400
    
    if data.get('check_out_date'):
        try:
            check_out_date = datetime.strptime(data.get('check_out_date'), '%Y-%m-%d').date()
            guest.check_out_date = check_out_date
            
            # Update room history
            room_history = RoomHistory.query.filter_by(
                guest_id=guest.id,
                room_id=guest.room_id,
                end_date=None
            ).first()
            
            if room_history:
                room_history.end_date = check_out_date
            
            # If setting check_out_date, also set status to inactive
            guest.status = 'inactive'
            
            # Check if room is now empty
            active_guests_count = Guest.query.filter_by(room_id=guest.room_id, status='active').count()
            if active_guests_count <= 1:  # Only this guest is active
                room = Room.query.get(guest.room_id)
                if room:
                    room.status = 'available'
        except ValueError:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_DATE_FORMAT',
                    'message': 'Date format should be YYYY-MM-DD'
                }
            }), 400
    
    # Handle room change
    if data.get('room_id') and int(data.get('room_id')) != guest.room_id:
        new_room = Room.query.get(data.get('room_id'))
        if not new_room:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'ROOM_NOT_FOUND',
                    'message': 'New room not found'
                }
            }), 404
        
        # Check if new room has capacity
        if guest.status == 'active':
            active_guests_count = Guest.query.filter_by(room_id=new_room.id, status='active').count()
            if active_guests_count >= new_room.capacity:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'ROOM_FULL',
                        'message': 'New room is at full capacity'
                    }
                }), 400
        
        # Close current room history
        current_room_history = RoomHistory.query.filter_by(
            guest_id=guest.id,
            room_id=guest.room_id,
            end_date=None
        ).first()
        
        if current_room_history:
            current_room_history.end_date = date.today()
        
        # Create new room history
        new_room_history = RoomHistory(
            room_id=new_room.id,
            guest_id=guest.id,
            start_date=date.today()
        )
        
        db.session.add(new_room_history)
        
        # Update old room status if needed
        old_room = Room.query.get(guest.room_id)
        if old_room and guest.status == 'active':
            active_guests_count = Guest.query.filter_by(room_id=old_room.id, status='active').count()
            if active_guests_count <= 1:  # Only this guest is active
                old_room.status = 'available'
        
        # Update new room status if needed
        if new_room.status == 'available' and guest.status == 'active':
            new_room.status = 'occupied'
        
        guest.room_id = new_room.id
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': {
            'guest': guest.to_dict()
        },
        'message': 'Guest updated successfully'
    }), 200

@guest_bp.route('/guests/<int:guest_id>', methods=['DELETE'])
@jwt_required()
def delete_guest(guest_id):
    # Only admins can delete guests
    current_user = get_jwt_identity()
    if current_user.get('role') != 'admin':
        return jsonify({
            'success': False,
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'Only admins can delete guests'
            }
        }), 403
    
    guest = Guest.query.get(guest_id)
    
    if not guest:
        return jsonify({
            'success': False,
            'error': {
                'code': 'GUEST_NOT_FOUND',
                'message': 'Guest not found'
            }
        }), 404
    
    # Check if guest has payments
    if guest.payments and len(guest.payments) > 0:
        return jsonify({
            'success': False,
            'error': {
                'code': 'GUEST_HAS_PAYMENTS',
                'message': 'Cannot delete guest with payment records. Consider marking as inactive instead.'
            }
        }), 400
    
    # Update room status if needed
    if guest.status == 'active':
        room = Room.query.get(guest.room_id)
        if room:
            active_guests_count = Guest.query.filter_by(room_id=room.id, status='active').count()
            if active_guests_count <= 1:  # Only this guest is active
                room.status = 'available'
    
    db.session.delete(guest)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Guest deleted successfully'
    }), 200

@guest_bp.route('/guests/<int:guest_id>/checkout', methods=['POST'])
@jwt_required()
def checkout_guest(guest_id):
    guest = Guest.query.get(guest_id)
    
    if not guest:
        return jsonify({
            'success': False,
            'error': {
                'code': 'GUEST_NOT_FOUND',
                'message': 'Guest not found'
            }
        }), 404
    
    if guest.status == 'inactive':
        return jsonify({
            'success': False,
            'error': {
                'code': 'ALREADY_CHECKED_OUT',
                'message': 'Guest has already checked out'
            }
        }), 400
    
    data = request.get_json()
    
    # Set check-out date
    if data and data.get('check_out_date'):
        try:
            check_out_date = datetime.strptime(data.get('check_out_date'), '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_DATE_FORMAT',
                    'message': 'Date format should be YYYY-MM-DD'
                }
            }), 400
    else:
        check_out_date = date.today()
    
    guest.check_out_date = check_out_date
    guest.status = 'inactive'
    
    # Update room history
    room_history = RoomHistory.query.filter_by(
        guest_id=guest.id,
        room_id=guest.room_id,
        end_date=None
    ).first()
    
    if room_history:
        room_history.end_date = check_out_date
    
    # Check if room is now empty
    active_guests_count = Guest.query.filter_by(room_id=guest.room_id, status='active').count()
    if active_guests_count <= 1:  # Only this guest is active
        room = Room.query.get(guest.room_id)
        if room:
            room.status = 'available'
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': {
            'guest': guest.to_dict()
        },
        'message': 'Guest checked out successfully'
    }), 200

@guest_bp.route('/guests/search', methods=['GET'])
@jwt_required()
def search_guests():
    # Get search query
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({
            'success': False,
            'error': {
                'code': 'MISSING_QUERY',
                'message': 'Search query is required'
            }
        }), 400
    
    # Search in name and contact number
    guests = Guest.query.filter(
        (Guest.full_name.ilike(f'%{query}%')) | 
        (Guest.contact_number.ilike(f'%{query}%'))
    ).all()
    
    guests_list = [guest.to_dict() for guest in guests]
    
    return jsonify({
        'success': True,
        'data': {
            'guests': guests_list
        },
        'message': 'Search results retrieved successfully'
    }), 200
