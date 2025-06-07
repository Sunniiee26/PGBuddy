from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.payment import db, Payment
from src.models.guest import Guest
from src.models.room import Room
from datetime import datetime, date, timedelta
import calendar
import os
import csv
import tempfile
import io
import pandas as pd
from fpdf2 import FPDF

report_bp = Blueprint('report', __name__)

@report_bp.route('/reports/rent', methods=['GET'])
@jwt_required()
def get_rent_report():
    # Get query parameters for filtering
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    guest_id = request.args.get('guest_id')
    room_id = request.args.get('room_id')
    report_format = request.args.get('format', 'json')  # Default to JSON if not specified
    
    # Validate dates
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_DATE_FORMAT',
                    'message': 'Date format should be YYYY-MM-DD'
                }
            }), 400
    else:
        # Default to first day of current month
        today = date.today()
        start_date = date(today.year, today.month, 1)
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_DATE_FORMAT',
                    'message': 'Date format should be YYYY-MM-DD'
                }
            }), 400
    else:
        # Default to today
        end_date = date.today()
    
    # Base query
    query = Payment.query.filter(
        Payment.payment_date >= start_date,
        Payment.payment_date <= end_date
    )
    
    # Apply additional filters if provided
    if guest_id:
        query = query.filter(Payment.guest_id == guest_id)
    
    if room_id:
        # Join with Guest to filter by room_id
        query = query.join(Guest).filter(Guest.room_id == room_id)
    
    # Execute query and get results
    payments = query.all()
    
    # Prepare data for report
    report_data = []
    total_amount = 0
    
    for payment in payments:
        guest = Guest.query.get(payment.guest_id)
        room = Room.query.get(guest.room_id) if guest else None
        
        payment_data = {
            'payment_id': payment.id,
            'guest_name': guest.full_name if guest else 'Unknown',
            'room_number': room.room_number if room else 'Unknown',
            'amount': float(payment.amount),
            'payment_date': payment.payment_date.strftime('%Y-%m-%d'),
            'status': payment.status,
            'due_date': payment.due_date.strftime('%Y-%m-%d')
        }
        
        report_data.append(payment_data)
        
        if payment.status == 'paid':
            total_amount += float(payment.amount)
    
    # Generate report based on requested format
    if report_format == 'json':
        return jsonify({
            'success': True,
            'data': {
                'report': {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'total_amount': total_amount,
                    'payments': report_data
                }
            },
            'message': 'Rent report generated successfully'
        }), 200
    
    elif report_format == 'csv':
        # Create a temporary file
        fd, path = tempfile.mkstemp(suffix='.csv')
        
        try:
            with os.fdopen(fd, 'w', newline='') as temp_file:
                # Create CSV writer
                fieldnames = ['payment_id', 'guest_name', 'room_number', 'amount', 'payment_date', 'status', 'due_date']
                writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
                
                # Write header and data
                writer.writeheader()
                writer.writerows(report_data)
            
            # Send the file
            return send_file(
                path,
                as_attachment=True,
                download_name=f'rent_report_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.csv',
                mimetype='text/csv'
            )
        
        finally:
            # Clean up the temporary file
            os.remove(path)
    
    elif report_format == 'pdf':
        # Create PDF using FPDF2
        pdf = FPDF()
        pdf.add_page()
        
        # Set up fonts
        pdf.set_font("helvetica", size=16)
        
        # Title
        pdf.cell(200, 10, txt="Rent Report", ln=True, align='C')
        pdf.set_font("helvetica", size=10)
        pdf.cell(200, 10, txt=f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", ln=True, align='C')
        pdf.ln(10)
        
        # Table header
        pdf.set_font("helvetica", 'B', 10)
        pdf.cell(15, 10, txt="ID", border=1)
        pdf.cell(40, 10, txt="Guest Name", border=1)
        pdf.cell(25, 10, txt="Room", border=1)
        pdf.cell(25, 10, txt="Amount", border=1)
        pdf.cell(30, 10, txt="Payment Date", border=1)
        pdf.cell(25, 10, txt="Status", border=1)
        pdf.cell(30, 10, txt="Due Date", border=1, ln=True)
        
        # Table data
        pdf.set_font("helvetica", size=10)
        for data in report_data:
            pdf.cell(15, 10, txt=str(data['payment_id']), border=1)
            pdf.cell(40, 10, txt=data['guest_name'], border=1)
            pdf.cell(25, 10, txt=data['room_number'], border=1)
            pdf.cell(25, 10, txt=str(data['amount']), border=1)
            pdf.cell(30, 10, txt=data['payment_date'], border=1)
            pdf.cell(25, 10, txt=data['status'], border=1)
            pdf.cell(30, 10, txt=data['due_date'], border=1, ln=True)
        
        # Summary
        pdf.ln(10)
        pdf.set_font("helvetica", 'B', 12)
        pdf.cell(200, 10, txt=f"Total Amount Collected: {total_amount}", ln=True)
        
        # Create a temporary file
        fd, path = tempfile.mkstemp(suffix='.pdf')
        
        try:
            # Save PDF to temporary file
            pdf.output(path)
            
            # Send the file
            return send_file(
                path,
                as_attachment=True,
                download_name=f'rent_report_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.pdf',
                mimetype='application/pdf'
            )
        
        finally:
            # Clean up the temporary file
            os.remove(path)
    
    else:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_FORMAT',
                'message': 'Format must be json, csv, or pdf'
            }
        }), 400

@report_bp.route('/reports/occupancy', methods=['GET'])
@jwt_required()
def get_occupancy_report():
    # Get query parameters
    report_date = request.args.get('date')
    report_format = request.args.get('format', 'json')  # Default to JSON if not specified
    
    # Validate date
    if report_date:
        try:
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_DATE_FORMAT',
                    'message': 'Date format should be YYYY-MM-DD'
                }
            }), 400
    else:
        # Default to today
        report_date = date.today()
    
    # Get all rooms
    rooms = Room.query.all()
    
    # Prepare data for report
    report_data = []
    total_rooms = len(rooms)
    occupied_rooms = 0
    
    for room in rooms:
        # Get active guests in room
        active_guests = Guest.query.filter_by(room_id=room.id, status='active').all()
        
        room_data = {
            'room_id': room.id,
            'room_number': room.room_number,
            'capacity': room.capacity,
            'status': room.status,
            'occupancy': len(active_guests),
            'guests': [guest.full_name for guest in active_guests]
        }
        
        report_data.append(room_data)
        
        if room.status == 'occupied':
            occupied_rooms += 1
    
    # Calculate occupancy rate
    occupancy_rate = (occupied_rooms / total_rooms) * 100 if total_rooms > 0 else 0
    
    # Generate report based on requested format
    if report_format == 'json':
        return jsonify({
            'success': True,
            'data': {
                'report': {
                    'date': report_date.strftime('%Y-%m-%d'),
                    'total_rooms': total_rooms,
                    'occupied_rooms': occupied_rooms,
                    'occupancy_rate': occupancy_rate,
                    'rooms': report_data
                }
            },
            'message': 'Occupancy report generated successfully'
        }), 200
    
    elif report_format == 'csv':
        # Create a temporary file
        fd, path = tempfile.mkstemp(suffix='.csv')
        
        try:
            with os.fdopen(fd, 'w', newline='') as temp_file:
                # Create CSV writer
                fieldnames = ['room_id', 'room_number', 'capacity', 'status', 'occupancy', 'guests']
                writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
                
                # Write header and data
                writer.writeheader()
                writer.writerows(report_data)
            
            # Send the file
            return send_file(
                path,
                as_attachment=True,
                download_name=f'occupancy_report_{report_date.strftime("%Y%m%d")}.csv',
                mimetype='text/csv'
            )
        
        finally:
            # Clean up the temporary file
            os.remove(path)
    
    elif report_format == 'pdf':
        # Create PDF using FPDF2
        pdf = FPDF()
        pdf.add_page()
        
        # Set up fonts
        pdf.set_font("helvetica", size=16)
        
        # Title
        pdf.cell(200, 10, txt="Occupancy Report", ln=True, align='C')
        pdf.set_font("helvetica", size=10)
        pdf.cell(200, 10, txt=f"Date: {report_date.strftime('%Y-%m-%d')}", ln=True, align='C')
        pdf.ln(10)
        
        # Summary
        pdf.set_font("helvetica", 'B', 12)
        pdf.cell(200, 10, txt=f"Total Rooms: {total_rooms}", ln=True)
        pdf.cell(200, 10, txt=f"Occupied Rooms: {occupied_rooms}", ln=True)
        pdf.cell(200, 10, txt=f"Occupancy Rate: {occupancy_rate:.2f}%", ln=True)
        pdf.ln(10)
        
        # Table header
        pdf.set_font("helvetica", 'B', 10)
        pdf.cell(15, 10, txt="ID", border=1)
        pdf.cell(30, 10, txt="Room Number", border=1)
        pdf.cell(25, 10, txt="Capacity", border=1)
        pdf.cell(30, 10, txt="Status", border=1)
        pdf.cell(25, 10, txt="Occupancy", border=1)
        pdf.cell(65, 10, txt="Guests", border=1, ln=True)
        
        # Table data
        pdf.set_font("helvetica", size=10)
        for data in report_data:
            pdf.cell(15, 10, txt=str(data['room_id']), border=1)
            pdf.cell(30, 10, txt=data['room_number'], border=1)
            pdf.cell(25, 10, txt=str(data['capacity']), border=1)
            pdf.cell(30, 10, txt=data['status'], border=1)
            pdf.cell(25, 10, txt=str(data['occupancy']), border=1)
            pdf.cell(65, 10, txt=', '.join(data['guests'])[:40], border=1, ln=True)
        
        # Create a temporary file
        fd, path = tempfile.mkstemp(suffix='.pdf')
        
        try:
            # Save PDF to temporary file
            pdf.output(path)
            
            # Send the file
            return send_file(
                path,
                as_attachment=True,
                download_name=f'occupancy_report_{report_date.strftime("%Y%m%d")}.pdf',
                mimetype='application/pdf'
            )
        
        finally:
            # Clean up the temporary file
            os.remove(path)
    
    else:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_FORMAT',
                'message': 'Format must be json, csv, or pdf'
            }
        }), 400

@report_bp.route('/reports/guests', methods=['GET'])
@jwt_required()
def get_guests_report():
    # Get query parameters
    status = request.args.get('status')
    report_format = request.args.get('format', 'json')  # Default to JSON if not specified
    
    # Base query
    query = Guest.query
    
    # Apply filter if provided
    if status:
        query = query.filter(Guest.status == status)
    
    # Execute query and get results
    guests = query.all()
    
    # Prepare data for report
    report_data = []
    
    for guest in guests:
        room = Room.query.get(guest.room_id)
        
        guest_data = {
            'guest_id': guest.id,
            'full_name': guest.full_name,
            'contact_number': guest.contact_number,
            'room_number': room.room_number if room else 'Unknown',
            'check_in_date': guest.check_in_date.strftime('%Y-%m-%d'),
            'check_out_date': guest.check_out_date.strftime('%Y-%m-%d') if guest.check_out_date else 'N/A',
            'rent_amount': float(guest.rent_amount),
            'status': guest.status
        }
        
        report_data.append(guest_data)
    
    # Generate report based on requested format
    if report_format == 'json':
        return jsonify({
            'success': True,
            'data': {
                'report': {
                    'total_guests': len(report_data),
                    'guests': report_data
                }
            },
            'message': 'Guests report generated successfully'
        }), 200
    
    elif report_format == 'csv':
        # Create a temporary file
        fd, path = tempfile.mkstemp(suffix='.csv')
        
        try:
            with os.fdopen(fd, 'w', newline='') as temp_file:
                # Create CSV writer
                fieldnames = ['guest_id', 'full_name', 'contact_number', 'room_number', 'check_in_date', 'check_out_date', 'rent_amount', 'status']
                writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
                
                # Write header and data
                writer.writeheader()
                writer.writerows(report_data)
            
            # Send the file
            return send_file(
                path,
                as_attachment=True,
                download_name=f'guests_report_{date.today().strftime("%Y%m%d")}.csv',
                mimetype='text/csv'
            )
        
        finally:
            # Clean up the temporary file
            os.remove(path)
    
    elif report_format == 'pdf':
        # Create PDF using FPDF2
        pdf = FPDF()
        pdf.add_page(orientation='L')  # Landscape for more columns
        
        # Set up fonts
        pdf.set_font("helvetica", size=16)
        
        # Title
        pdf.cell(280, 10, txt="Guests Report", ln=True, align='C')
        pdf.set_font("helvetica", size=10)
        pdf.cell(280, 10, txt=f"Date: {date.today().strftime('%Y-%m-%d')}", ln=True, align='C')
        pdf.ln(10)
        
        # Summary
        pdf.set_font("helvetica", 'B', 12)
        pdf.cell(280, 10, txt=f"Total Guests: {len(report_data)}", ln=True)
        pdf.ln(10)
        
        # Table header
        pdf.set_font("helvetica", 'B', 10)
        pdf.cell(15, 10, txt="ID", border=1)
        pdf.cell(50, 10, txt="Full Name", border=1)
        pdf.cell(30, 10, txt="Contact", border=1)
        pdf.cell(25, 10, txt="Room", border=1)
        pdf.cell(30, 10, txt="Check In", border=1)
        pdf.cell(30, 10, txt="Check Out", border=1)
        pdf.cell(25, 10, txt="Rent", border=1)
        pdf.cell(25, 10, txt="Status", border=1, ln=True)
        
        # Table data
        pdf.set_font("helvetica", size=10)
        for data in report_data:
            pdf.cell(15, 10, txt=str(data['guest_id']), border=1)
            pdf.cell(50, 10, txt=data['full_name'], border=1)
            pdf.cell(30, 10, txt=data['contact_number'], border=1)
            pdf.cell(25, 10, txt=data['room_number'], border=1)
            pdf.cell(30, 10, txt=data['check_in_date'], border=1)
            pdf.cell(30, 10, txt=data['check_out_date'], border=1)
            pdf.cell(25, 10, txt=str(data['rent_amount']), border=1)
            pdf.cell(25, 10, txt=data['status'], border=1, ln=True)
        
        # Create a temporary file
        fd, path = tempfile.mkstemp(suffix='.pdf')
        
        try:
            # Save PDF to temporary file
            pdf.output(path)
            
            # Send the file
            return send_file(
                path,
                as_attachment=True,
                download_name=f'guests_report_{date.today().strftime("%Y%m%d")}.pdf',
                mimetype='application/pdf'
            )
        
        finally:
            # Clean up the temporary file
            os.remove(path)
    
    else:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_FORMAT',
                'message': 'Format must be json, csv, or pdf'
            }
        }), 400

@report_bp.route('/reports/payments', methods=['GET'])
@jwt_required()
def get_payments_report():
    # Get query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status = request.args.get('status')
    report_format = request.args.get('format', 'json')  # Default to JSON if not specified
    
    # Validate dates
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_DATE_FORMAT',
                    'message': 'Date format should be YYYY-MM-DD'
                }
            }), 400
    else:
        # Default to first day of current month
        today = date.today()
        start_date = date(today.year, today.month, 1)
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_DATE_FORMAT',
                    'message': 'Date format should be YYYY-MM-DD'
                }
            }), 400
    else:
        # Default to today
        end_date = date.today()
    
    # Base query
    query = Payment.query.filter(
        Payment.due_date >= start_date,
        Payment.due_date <= end_date
    )
    
    # Apply status filter if provided
    if status:
        query = query.filter(Payment.status == status)
    
    # Execute query and get results
    payments = query.all()
    
    # Prepare data for report
    report_data = []
    total_amount = 0
    paid_amount = 0
    pending_amount = 0
    
    for payment in payments:
        guest = Guest.query.get(payment.guest_id)
        
        payment_data = {
            'payment_id': payment.id,
            'guest_name': guest.full_name if guest else 'Unknown',
            'amount': float(payment.amount),
            'payment_date': payment.payment_date.strftime('%Y-%m-%d'),
            'payment_type': payment.payment_type,
            'status': payment.status,
            'due_date': payment.due_date.strftime('%Y-%m-%d')
        }
        
        report_data.append(payment_data)
        
        total_amount += float(payment.amount)
        
        if payment.status == 'paid':
            paid_amount += float(payment.amount)
        else:
            pending_amount += float(payment.amount)
    
    # Generate report based on requested format
    if report_format == 'json':
        return jsonify({
            'success': True,
            'data': {
                'report': {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'total_amount': total_amount,
                    'paid_amount': paid_amount,
                    'pending_amount': pending_amount,
                    'payments': report_data
                }
            },
            'message': 'Payments report generated successfully'
        }), 200
    
    elif report_format == 'csv':
        # Create a temporary file
        fd, path = tempfile.mkstemp(suffix='.csv')
        
        try:
            with os.fdopen(fd, 'w', newline='') as temp_file:
                # Create CSV writer
                fieldnames = ['payment_id', 'guest_name', 'amount', 'payment_date', 'payment_type', 'status', 'due_date']
                writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
                
                # Write header and data
                writer.writeheader()
                writer.writerows(report_data)
            
            # Send the file
            return send_file(
                path,
                as_attachment=True,
                download_name=f'payments_report_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.csv',
                mimetype='text/csv'
            )
        
        finally:
            # Clean up the temporary file
            os.remove(path)
    
    elif report_format == 'pdf':
        # Create PDF using FPDF2
        pdf = FPDF()
        pdf.add_page()
        
        # Set up fonts
        pdf.set_font("helvetica", size=16)
        
        # Title
        pdf.cell(200, 10, txt="Payments Report", ln=True, align='C')
        pdf.set_font("helvetica", size=10)
        pdf.cell(200, 10, txt=f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", ln=True, align='C')
        pdf.ln(10)
        
        # Summary
        pdf.set_font("helvetica", 'B', 12)
        pdf.cell(200, 10, txt=f"Total Amount: {total_amount}", ln=True)
        pdf.cell(200, 10, txt=f"Paid Amount: {paid_amount}", ln=True)
        pdf.cell(200, 10, txt=f"Pending Amount: {pending_amount}", ln=True)
        pdf.ln(10)
        
        # Table header
        pdf.set_font("helvetica", 'B', 10)
        pdf.cell(15, 10, txt="ID", border=1)
        pdf.cell(40, 10, txt="Guest Name", border=1)
        pdf.cell(25, 10, txt="Amount", border=1)
        pdf.cell(30, 10, txt="Payment Date", border=1)
        pdf.cell(25, 10, txt="Type", border=1)
        pdf.cell(25, 10, txt="Status", border=1)
        pdf.cell(30, 10, txt="Due Date", border=1, ln=True)
        
        # Table data
        pdf.set_font("helvetica", size=10)
        for data in report_data:
            pdf.cell(15, 10, txt=str(data['payment_id']), border=1)
            pdf.cell(40, 10, txt=data['guest_name'], border=1)
            pdf.cell(25, 10, txt=str(data['amount']), border=1)
            pdf.cell(30, 10, txt=data['payment_date'], border=1)
            pdf.cell(25, 10, txt=data['payment_type'], border=1)
            pdf.cell(25, 10, txt=data['status'], border=1)
            pdf.cell(30, 10, txt=data['due_date'], border=1, ln=True)
        
        # Create a temporary file
        fd, path = tempfile.mkstemp(suffix='.pdf')
        
        try:
            # Save PDF to temporary file
            pdf.output(path)
            
            # Send the file
            return send_file(
                path,
                as_attachment=True,
                download_name=f'payments_report_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.pdf',
                mimetype='application/pdf'
            )
        
        finally:
            # Clean up the temporary file
            os.remove(path)
    
    else:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_FORMAT',
                'message': 'Format must be json, csv, or pdf'
            }
        }), 400
