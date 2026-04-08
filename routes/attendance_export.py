"""
routes/attendance_export.py - Advanced Attendance Export with Pivot Format
"""

from flask import Blueprint, request, jsonify, Response
from database import db, AttendanceRecord, Employee, LeaveRequest
from routes.auth import token_required, company_admin_required
from datetime import datetime, date, timedelta
import csv
import io

attendance_export_bp = Blueprint('attendance_export', __name__)


@attendance_export_bp.route('/admin/export-pivot', methods=['GET'])
@token_required
@company_admin_required
def export_pivot_format():
    """
    Export attendance in pivot format:
    Rows = Dates, Columns = Employees
    Each cell = Check-in | Check-out | Status (Late/Leave/Present/Absent)
    
    Query params:
    - type: "day" or "range"
    - date_from: start date (for both types)
    - date_to: end date (for range type)
    """
    company = request.current_company
    export_type = request.args.get('type', 'day')  # day or range
    date_from_str = request.args.get('date_from')
    date_to_str = request.args.get('date_to')
    
    # Validate date inputs
    if not date_from_str or not date_to_str:
        return jsonify({'success': False, 'message': 'date_from and date_to required'}), 400
    
    try:
        start_date = date.fromisoformat(date_from_str)
        end_date = date.fromisoformat(date_to_str)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    if start_date > end_date:
        return jsonify({'success': False, 'message': 'start_date must be before end_date'}), 400
    
    # Generate filename
    if export_type == 'day':
        filename = f"attendance_{date_from_str}.csv"
    else:  # range
        filename = f"attendance_{date_from_str}_to_{date_to_str}.csv"
    # Get all active employees
    employees = Employee.query.filter_by(
        company_id=company.id,
        is_active=True,
        role='employee'
    ).order_by(Employee.name).all()
    
    if not employees:
        return jsonify({'success': False, 'message': 'No employees found'}), 404
    
    # Get all records in date range
    records = AttendanceRecord.query.filter(
        AttendanceRecord.company_id == company.id,
        AttendanceRecord.date >= start_date,
        AttendanceRecord.date <= end_date
    ).all()
    
    # Get all approved leaves
    leaves = LeaveRequest.query.filter(
        LeaveRequest.company_id == company.id,
        LeaveRequest.status == 'approved',
        LeaveRequest.start_date <= end_date,
        LeaveRequest.end_date >= start_date
    ).all()
    
    # Create records map
    records_by_emp_date = {}
    for record in records:
        key = (record.employee_id, record.date)
        records_by_emp_date[key] = record
    
    # Create leaves map
    leaves_by_emp_date = {}
    for leave in leaves:
        current = leave.start_date
        while current <= leave.end_date:
            key = (leave.employee_id, current)
            leaves_by_emp_date[key] = leave.leave_type
            current += timedelta(days=1)
    
    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header row: Date | Employee1 | Employee2 | ...
    header = ['Date'] + [emp.employee_id for emp in employees]
    writer.writerow(header)
    
    # Data rows: one row per date
    current_date = start_date
    while current_date <= end_date:
        row = [current_date.strftime('%Y-%m-%d')]
        
        for emp in employees:
            emp_id = emp.id
            
            # Check if on leave
            leave_key = (emp_id, current_date)
            if leave_key in leaves_by_emp_date:
                leave_type = leaves_by_emp_date[leave_key].upper()
                row.append(f"LEAVE: {leave_type}")
            else:
                # Check attendance record
                record_key = (emp_id, current_date)
                record = records_by_emp_date.get(record_key)
                
                if record and record.check_in:
                    check_in_time = record.check_in.strftime('%H:%M')
                    check_out_time = record.check_out.strftime('%H:%M') if record.check_out else '—'
                    status = record.status.upper()
                    cell_value = f"{check_in_time} | {check_out_time} | {status}"
                    row.append(cell_value)
                else:
                    # Not checked in = Absent
                    row.append('ABSENT')
        
        writer.writerow(row)
        current_date += timedelta(days=1)
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    ), 200