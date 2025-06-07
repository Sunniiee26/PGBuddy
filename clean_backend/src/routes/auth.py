from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from src.models.user import db, User
from datetime import timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({
            'success': False,
            'error': {
                'code': 'MISSING_FIELDS',
                'message': 'Email and password are required'
            }
        }), 400
    
    user = User.query.filter_by(email=data.get('email')).first()
    
    if not user or not check_password_hash(user.password_hash, data.get('password')):
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_CREDENTIALS',
                'message': 'Invalid email or password'
            }
        }), 401
    
    access_token = create_access_token(
        identity={'id': user.id, 'role': user.role},
        expires_delta=timedelta(days=1)
    )
    
    return jsonify({
        'success': True,
        'data': {
            'token': access_token,
            'user': user.to_dict()
        },
        'message': 'Login successful'
    }), 200

@auth_bp.route('/register', methods=['POST'])
@jwt_required()
def register():
    # Only admins can register new users
    current_user = get_jwt_identity()
    if current_user.get('role') != 'admin':
        return jsonify({
            'success': False,
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'Only admins can register new users'
            }
        }), 403
    
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password') or not data.get('full_name') or not data.get('role'):
        return jsonify({
            'success': False,
            'error': {
                'code': 'MISSING_FIELDS',
                'message': 'Email, password, full name, and role are required'
            }
        }), 400
    
    if data.get('role') not in ['admin', 'manager']:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_ROLE',
                'message': 'Role must be either admin or manager'
            }
        }), 400
    
    existing_user = User.query.filter_by(email=data.get('email')).first()
    if existing_user:
        return jsonify({
            'success': False,
            'error': {
                'code': 'EMAIL_EXISTS',
                'message': 'Email already exists'
            }
        }), 409
    
    hashed_password = generate_password_hash(data.get('password'))
    
    new_user = User(
        email=data.get('email'),
        password_hash=hashed_password,
        full_name=data.get('full_name'),
        role=data.get('role')
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': {
            'user': new_user.to_dict()
        },
        'message': 'User registered successfully'
    }), 201

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    current_user_id = get_jwt_identity().get('id')
    user = User.query.get(current_user_id)
    
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

@auth_bp.route('/update', methods=['PUT'])
@jwt_required()
def update_user():
    current_user_id = get_jwt_identity().get('id')
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({
            'success': False,
            'error': {
                'code': 'USER_NOT_FOUND',
                'message': 'User not found'
            }
        }), 404
    
    data = request.get_json()
    
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
    
    if data.get('current_password') and data.get('new_password'):
        if not check_password_hash(user.password_hash, data.get('current_password')):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_PASSWORD',
                    'message': 'Current password is incorrect'
                }
            }), 401
        user.password_hash = generate_password_hash(data.get('new_password'))
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': {
            'user': user.to_dict()
        },
        'message': 'User updated successfully'
    }), 200

# First-time setup endpoint to create initial admin user
@auth_bp.route('/setup', methods=['POST'])
def setup():
    # Check if any users exist
    if User.query.count() > 0:
        return jsonify({
            'success': False,
            'error': {
                'code': 'ALREADY_SETUP',
                'message': 'Setup has already been completed'
            }
        }), 400
    
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password') or not data.get('full_name'):
        return jsonify({
            'success': False,
            'error': {
                'code': 'MISSING_FIELDS',
                'message': 'Email, password, and full name are required'
            }
        }), 400
    
    hashed_password = generate_password_hash(data.get('password'))
    
    admin_user = User(
        email=data.get('email'),
        password_hash=hashed_password,
        full_name=data.get('full_name'),
        role='admin'
    )
    
    db.session.add(admin_user)
    db.session.commit()
    
    access_token = create_access_token(
        identity={'id': admin_user.id, 'role': admin_user.role},
        expires_delta=timedelta(days=1)
    )
    
    return jsonify({
        'success': True,
        'data': {
            'token': access_token,
            'user': admin_user.to_dict()
        },
        'message': 'Initial admin user created successfully'
    }), 201
