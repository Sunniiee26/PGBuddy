from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import db, User

user_bp = Blueprint('user', __name__)

@user_bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    # Only admins can view all users
    current_user = get_jwt_identity()
    if current_user.get('role') != 'admin':
        return jsonify({
            'success': False,
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'Only admins can view all users'
            }
        }), 403
    
    users = User.query.all()
    users_list = [user.to_dict() for user in users]
    
    return jsonify({
        'success': True,
        'data': {
            'users': users_list
        },
        'message': 'Users retrieved successfully'
    }), 200

@user_bp.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    # Admins can view any user, managers can only view themselves
    current_user = get_jwt_identity()
    if current_user.get('role') != 'admin' and current_user.get('id') != user_id:
        return jsonify({
            'success': False,
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'You are not authorized to view this user'
            }
        }), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({
            'success': False,
            'error': {
                'code': 'USER_NOT_FOUND',
                'message': 'User not found'
            }
        }), 404
    
    return jsonify({
        'success': True,
        'data': {
            'user': user.to_dict()
        },
        'message': 'User retrieved successfully'
    }), 200

@user_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    # Admins can update any user, managers can only update themselves
    current_user = get_jwt_identity()
    if current_user.get('role') != 'admin' and current_user.get('id') != user_id:
        return jsonify({
            'success': False,
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'You are not authorized to update this user'
            }
        }), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({
            'success': False,
            'error': {
                'code': 'USER_NOT_FOUND',
                'message': 'User not found'
            }
        }), 404
    
    data = request.get_json()
    
    # Only admins can change roles
    if data.get('role') and current_user.get('role') == 'admin':
        if data.get('role') not in ['admin', 'manager']:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_ROLE',
                    'message': 'Role must be either admin or manager'
                }
            }), 400
        user.role = data.get('role')
    
    if data.get('full_name'):
        user.full_name = data.get('full_name')
    
    if data.get('email'):
        existing_user = User.query.filter_by(email=data.get('email')).first()
        if existing_user and existing_user.id != user.id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'EMAIL_EXISTS',
                    'message': 'Email already exists'
                }
            }), 409
        user.email = data.get('email')
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': {
            'user': user.to_dict()
        },
        'message': 'User updated successfully'
    }), 200

@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    # Only admins can delete users
    current_user = get_jwt_identity()
    if current_user.get('role') != 'admin':
        return jsonify({
            'success': False,
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'Only admins can delete users'
            }
        }), 403
    
    # Prevent deleting yourself
    if current_user.get('id') == user_id:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_OPERATION',
                'message': 'You cannot delete your own account'
            }
        }), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({
            'success': False,
            'error': {
                'code': 'USER_NOT_FOUND',
                'message': 'User not found'
            }
        }), 404
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'User deleted successfully'
    }), 200
