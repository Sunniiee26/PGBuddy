from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.room import db, Room
from datetime import datetime

room_bp = Blueprint('room', __name__)

@room_bp.route('/rooms', methods=['GET'])
@jwt_required()
def get_rooms():
    # Get query parameters for filtering
    status = request.args.get('status')
    
    # Base query
    query = Room.query
    
    # Apply filters if provided
    if status:
        query = query.filter(Room.status == status)
    
    # Execute query and get results
    rooms = query.all()
    rooms_list = [room.to_dict() for room in rooms]
    
    return jsonify({
        'success': True,
        'data': {
            'rooms': rooms_list
        },
        'message': 'Rooms retrieved successfully'
    }), 200

@room_bp.route('/rooms/available', methods=['GET'])
@jwt_required()
def get_available_rooms():
    rooms = Room.query.filter_by(status='available').all()
    rooms_list = [room.to_dict() for room in rooms]
    
    return jsonify({
        'success': True,
        'data': {
            'rooms': rooms_list
        },
        'message': 'Available rooms retrieved successfully'
    }), 200

@room_bp.route('/rooms/occupied', methods=['GET'])
@jwt_required()
def get_occupied_rooms():
    rooms = Room.query.filter_by(status='occupied').all()
    rooms_list = [room.to_dict() for room in rooms]
    
    return jsonify({
        'success': True,
        'data': {
            'rooms': rooms_list
        },
        'message': 'Occupied rooms retrieved successfully'
    }), 200

@room_bp.route('/rooms/<int:room_id>', methods=['GET'])
@jwt_required()
def get_room(room_id):
    room = Room.query.get(room_id)
    
    if not room:
        return jsonify({
            'success': False,
            'error': {
                'code': 'ROOM_NOT_FOUND',
                'message': 'Room not found'
            }
        }), 404
    
    return jsonify({
        'success': True,
        'data': {
            'room': room.to_dict()
        },
        'message': 'Room retrieved successfully'
    }), 200

@room_bp.route('/rooms', methods=['POST'])
@jwt_required()
def create_room():
    # Only admins can create rooms
    current_user = get_jwt_identity()
    if current_user.get('role') != 'admin':
        return jsonify({
            'success': False,
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'Only admins can create rooms'
            }
        }), 403
    
    data = request.get_json()
    
    if not data or not data.get('room_number') or not data.get('capacity') or not data.get('status'):
        return jsonify({
            'success': False,
            'error': {
                'code': 'MISSING_FIELDS',
                'message': 'Room number, capacity, and status are required'
            }
        }), 400
    
    if data.get('status') not in ['available', 'occupied']:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_STATUS',
                'message': 'Status must be either available or occupied'
            }
        }), 400
    
    existing_room = Room.query.filter_by(room_number=data.get('room_number')).first()
    if existing_room:
        return jsonify({
            'success': False,
            'error': {
                'code': 'ROOM_EXISTS',
                'message': 'Room number already exists'
            }
        }), 409
    
    new_room = Room(
        room_number=data.get('room_number'),
        capacity=data.get('capacity'),
        status=data.get('status'),
        notes=data.get('notes')
    )
    
    db.session.add(new_room)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': {
            'room': new_room.to_dict()
        },
        'message': 'Room created successfully'
    }), 201

@room_bp.route('/rooms/<int:room_id>', methods=['PUT'])
@jwt_required()
def update_room(room_id):
    # Only admins can update rooms
    current_user = get_jwt_identity()
    if current_user.get('role') != 'admin':
        return jsonify({
            'success': False,
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'Only admins can update rooms'
            }
        }), 403
    
    room = Room.query.get(room_id)
    
    if not room:
        return jsonify({
            'success': False,
            'error': {
                'code': 'ROOM_NOT_FOUND',
                'message': 'Room not found'
            }
        }), 404
    
    data = request.get_json()
    
    if data.get('room_number'):
        existing_room = Room.query.filter_by(room_number=data.get('room_number')).first()
        if existing_room and existing_room.id != room_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'ROOM_EXISTS',
                    'message': 'Room number already exists'
                }
            }), 409
        room.room_number = data.get('room_number')
    
    if data.get('capacity'):
        room.capacity = data.get('capacity')
    
    if data.get('status'):
        if data.get('status') not in ['available', 'occupied']:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_STATUS',
                    'message': 'Status must be either available or occupied'
                }
            }), 400
        room.status = data.get('status')
    
    if 'notes' in data:
        room.notes = data.get('notes')
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': {
            'room': room.to_dict()
        },
        'message': 'Room updated successfully'
    }), 200

@room_bp.route('/rooms/<int:room_id>', methods=['DELETE'])
@jwt_required()
def delete_room(room_id):
    # Only admins can delete rooms
    current_user = get_jwt_identity()
    if current_user.get('role') != 'admin':
        return jsonify({
            'success': False,
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'Only admins can delete rooms'
            }
        }), 403
    
    room = Room.query.get(room_id)
    
    if not room:
        return jsonify({
            'success': False,
            'error': {
                'code': 'ROOM_NOT_FOUND',
                'message': 'Room not found'
            }
        }), 404
    
    # Check if room has active guests
    if room.guests and any(guest.status == 'active' for guest in room.guests):
        return jsonify({
            'success': False,
            'error': {
                'code': 'ROOM_OCCUPIED',
                'message': 'Cannot delete room with active guests'
            }
        }), 400
    
    db.session.delete(room)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Room deleted successfully'
    }), 200

@room_bp.route('/rooms/<int:room_id>/guests', methods=['GET'])
@jwt_required()
def get_room_guests(room_id):
    room = Room.query.get(room_id)
    
    if not room:
        return jsonify({
            'success': False,
            'error': {
                'code': 'ROOM_NOT_FOUND',
                'message': 'Room not found'
            }
        }), 404
    
    guests = room.guests
    guests_list = [guest.to_dict() for guest in guests]
    
    return jsonify({
        'success': True,
        'data': {
            'guests': guests_list
        },
        'message': 'Room guests retrieved successfully'
    }), 200
