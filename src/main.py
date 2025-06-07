import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from flask import Flask, send_from_directory, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from src.models.user import db
from src.routes.auth import auth_bp
from src.routes.user import user_bp
from src.routes.room import room_bp
from src.routes.guest import guest_bp
from src.routes.payment import payment_bp
from src.routes.notification import notification_bp
from src.routes.report import report_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
CORS(app)

# Configuration
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'
app.config['JWT_SECRET_KEY'] = 'jwt-secret-string-change-in-production'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 86400  # 24 hours in seconds

# Database configuration - PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.getenv('DB_USERNAME', 'postgres')}:{os.getenv('DB_PASSWORD', 'postgres')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'pg_management')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
jwt = JWTManager(app)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
app.register_blueprint(user_bp, url_prefix='/api/v1')
app.register_blueprint(room_bp, url_prefix='/api/v1')
app.register_blueprint(guest_bp, url_prefix='/api/v1')
app.register_blueprint(payment_bp, url_prefix='/api/v1')
app.register_blueprint(notification_bp, url_prefix='/api/v1')
app.register_blueprint(report_bp, url_prefix='/api/v1')

# Create database tables
with app.app_context():
    db.create_all()

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': {
            'code': 'NOT_FOUND',
            'message': 'The requested resource was not found'
        }
    }), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({
        'success': False,
        'error': {
            'code': 'SERVER_ERROR',
            'message': 'An internal server error occurred'
        }
    }), 500

# Dashboard endpoint
@app.route('/api/v1/dashboard/summary', methods=['GET'])
@jwt_required()
def get_dashboard_summary():
    from src.models.guest import Guest
    from src.models.room import Room
    from src.models.payment import Payment
    from datetime import date
    
    # Get active guests count
    active_guests_count = Guest.query.filter_by(status='active').count()
    
    # Get vacant rooms count
    vacant_rooms_count = Room.query.filter_by(status='available').count()
    
    # Get total collected rent
    paid_payments = Payment.query.filter_by(status='paid').all()
    total_collected = sum(float(payment.amount) for payment in paid_payments)
    
    # Get pending dues
    pending_payments = Payment.query.filter(
        Payment.status.in_(['unpaid', 'partial'])
    ).all()
    pending_dues = sum(float(payment.amount) for payment in pending_payments)
    
    return jsonify({
        'success': True,
        'data': {
            'active_guests': active_guests_count,
            'vacant_rooms': vacant_rooms_count,
            'total_collected': total_collected,
            'pending_dues': pending_dues
        },
        'message': 'Dashboard summary retrieved successfully'
    }), 200

@app.route('/api/v1/dashboard/due-this-week', methods=['GET'])
@jwt_required()
def get_due_this_week():
    from src.models.payment import Payment
    from datetime import date, timedelta
    
    # Calculate date range for this week
    today = date.today()
    end_of_week = today + timedelta(days=7)
    
    # Get payments due this week
    payments = Payment.query.filter(
        Payment.status.in_(['unpaid', 'partial']),
        Payment.due_date >= today,
        Payment.due_date <= end_of_week
    ).all()
    
    payments_list = [payment.to_dict() for payment in payments]
    
    return jsonify({
        'success': True,
        'data': {
            'payments': payments_list
        },
        'message': 'Payments due this week retrieved successfully'
    }), 200

@app.route('/api/v1/dashboard/new-guests', methods=['GET'])
@jwt_required()
def get_new_guests():
    from src.models.guest import Guest
    from datetime import date, timedelta
    
    # Calculate date 30 days ago
    thirty_days_ago = date.today() - timedelta(days=30)
    
    # Get guests who checked in within the last 30 days
    guests = Guest.query.filter(
        Guest.check_in_date >= thirty_days_ago
    ).all()
    
    guests_list = [guest.to_dict() for guest in guests]
    
    return jsonify({
        'success': True,
        'data': {
            'guests': guests_list
        },
        'message': 'New guests retrieved successfully'
    }), 200

@app.route('/api/v1/dashboard/vacant-rooms', methods=['GET'])
@jwt_required()
def get_vacant_rooms():
    from src.models.room import Room
    
    # Get vacant rooms
    rooms = Room.query.filter_by(status='available').all()
    
    rooms_list = [room.to_dict() for room in rooms]
    
    return jsonify({
        'success': True,
        'data': {
            'rooms': rooms_list
        },
        'message': 'Vacant rooms retrieved successfully'
    }), 200

@app.route('/api/v1/dashboard/monthly-collection', methods=['GET'])
@jwt_required()
def get_monthly_collection():
    from src.models.payment import Payment
    from datetime import date
    import calendar
    
    # Get query parameters
    year = request.args.get('year')
    
    if not year:
        year = date.today().year
    else:
        try:
            year = int(year)
        except ValueError:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_YEAR',
                    'message': 'Year must be an integer'
                }
            }), 400
    
    # Prepare monthly data
    months_data = []
    
    for month in range(1, 13):
        # Get start and end date for the month
        _, last_day = calendar.monthrange(year, month)
        start_date = date(year, month, 1)
        end_date = date(year, month, last_day)
        
        # Get paid payments for the month
        payments = Payment.query.filter(
            Payment.status == 'paid',
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date
        ).all()
        
        # Calculate total amount
        total_amount = sum(float(payment.amount) for payment in payments)
        
        months_data.append({
            'month': month,
            'month_name': calendar.month_name[month],
            'amount': total_amount
        })
    
    return jsonify({
        'success': True,
        'data': {
            'year': year,
            'months': months_data
        },
        'message': 'Monthly collection retrieved successfully'
    }), 200

@app.route('/api/v1/dashboard/occupancy-rate', methods=['GET'])
@jwt_required()
def get_occupancy_rate():
    from src.models.room import Room
    
    # Get all rooms
    total_rooms = Room.query.count()
    occupied_rooms = Room.query.filter_by(status='occupied').count()
    
    # Calculate occupancy rate
    occupancy_rate = (occupied_rooms / total_rooms) * 100 if total_rooms > 0 else 0
    
    return jsonify({
        'success': True,
        'data': {
            'rate': occupancy_rate,
            'total_rooms': total_rooms,
            'occupied_rooms': occupied_rooms
        },
        'message': 'Occupancy rate retrieved successfully'
    }), 200

# Serve static files
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404
    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
