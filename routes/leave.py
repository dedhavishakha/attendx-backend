"""
routes/leave.py - Leave Management System
Employees apply for leave, HR approves/rejects
"""

from flask import Blueprint, request, jsonify
from database import db, LeaveRequest, Employee, AttendanceRecord
from routes.auth import token_required, company_admin_required
from datetime import datetime, date, timedelta

leave_bp = Blueprint('leave', __name__)


@leave_bp.route('/request', methods=['POST'])
@token_required
def apply_for_leave():
    """Employee applies for leave"""
    emp = request.current_user
    company = request.current_company
    data = request.get_json()
    
    # Validation
    if not data.get('leave_type') or not data.get('start_date') or not data.get('end_date'):
        return jsonify({'success': False, 'message': 'leave_type, start_date, and end_date are required'}), 400
    
    try:
        start = date.fromisoformat(data['start_date'])
        end = date.fromisoformat(data['end_date'])
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    # Date validations
    if end < start:
        return jsonify({'success': False, 'message': 'End date must be after or equal to start date'}), 400
    
    if start < date.today():
        return jsonify({'success': False, 'message': 'Cannot apply for leave in the past'}), 400
    
    # Check for overlapping requests
    existing = LeaveRequest.query.filter(
        LeaveRequest.company_id == company.id,
        LeaveRequest.employee_id == emp.id,
        LeaveRequest.status.in_(['pending', 'approved']),
        LeaveRequest.start_date <= end,
        LeaveRequest.end_date >= start
    ).first()
    
    if existing:
        return jsonify({
            'success': False, 
            'message': f'You already have a {existing.status} leave request for these dates'
        }), 409
    
    # Create leave request
    leave_request = LeaveRequest(
        company_id=company.id,
        employee_id=emp.id,
        leave_type=data['leave_type'],
        start_date=start,
        end_date=end,
        reason=data.get('reason', '')
    )
    
    db.session.add(leave_request)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Leave request submitted successfully',
        'request_id': leave_request.id,
        'request': leave_request.to_dict()
    }), 201


@leave_bp.route('/my-requests', methods=['GET'])
@token_required
def get_my_requests():
    """Get employee's leave requests"""
    emp = request.current_user
    company = request.current_company
    status = request.args.get('status')  # 'pending', 'approved', 'rejected', or None for all
    
    query = LeaveRequest.query.filter_by(
        company_id=company.id,
        employee_id=emp.id
    )
    
    if status:
        query = query.filter_by(status=status)
    
    requests = query.order_by(LeaveRequest.created_at.desc()).all()
    
    return jsonify({
        'success': True,
        'requests': [r.to_dict(include_approver=True) for r in requests]
    }), 200


@leave_bp.route('/calendar', methods=['GET'])
@token_required
def get_leave_calendar():
    """Get leave calendar for employee"""
    emp = request.current_user
    company = request.current_company
    month = int(request.args.get('month', date.today().month))
    year = int(request.args.get('year', date.today().year))
    
    # Get first and last day of month
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    # Get approved leaves for this month
    leaves = LeaveRequest.query.filter(
        LeaveRequest.company_id == company.id,
        LeaveRequest.employee_id == emp.id,
        LeaveRequest.status == 'approved',
        LeaveRequest.start_date <= last_day,
        LeaveRequest.end_date >= first_day
    ).all()
    
    # Build calendar
    calendar = []
    current = first_day
    while current <= last_day:
        leave_info = None
        for leave in leaves:
            if leave.start_date <= current <= leave.end_date:
                leave_info = {
                    'leave_id': leave.id,
                    'leave_type': leave.leave_type,
                    'start_date': leave.start_date.isoformat(),
                    'end_date': leave.end_date.isoformat()
                }
                break
        
        calendar.append({
            'date': current.isoformat(),
            'leave': leave_info
        })
        current += timedelta(days=1)
    
    return jsonify({
        'success': True,
        'month': month,
        'year': year,
        'calendar': calendar
    }), 200


@leave_bp.route('/pending', methods=['GET'])
@token_required
@company_admin_required
def get_pending_requests():
    """Get all pending leave requests for HR"""
    company = request.current_company
    
    pending = LeaveRequest.query.filter_by(
        company_id=company.id,
        status='pending'
    ).order_by(LeaveRequest.created_at.asc()).all()
    
    return jsonify({
        'success': True,
        'pending_count': len(pending),
        'requests': [r.to_dict(include_employee=True) for r in pending]
    }), 200


@leave_bp.route('/approve', methods=['POST'])
@token_required
@company_admin_required
def approve_leave():
    """Approve a leave request"""
    hr = request.current_user
    company = request.current_company
    data = request.get_json()
    
    if not data.get('request_id'):
        return jsonify({'success': False, 'message': 'request_id is required'}), 400
    
    leave_request = LeaveRequest.query.filter_by(
        id=data['request_id'],
        company_id=company.id
    ).first()
    
    if not leave_request:
        return jsonify({'success': False, 'message': 'Leave request not found'}), 404
    
    if leave_request.status != 'pending':
        return jsonify({
            'success': False, 
            'message': f'Cannot approve a {leave_request.status} request'
        }), 400
    
    # Update request
    leave_request.status = 'approved'
    leave_request.approved_by = hr.id
    leave_request.approval_date = datetime.utcnow()
    db.session.commit()
    
    # Auto-create attendance records for each day of leave
    current = leave_request.start_date
    while current <= leave_request.end_date:
        # Check if attendance already exists
        existing = AttendanceRecord.query.filter_by(
            company_id=company.id,
            employee_id=leave_request.employee_id,
            date=current
        ).first()
        
        if not existing:
            attendance = AttendanceRecord(
                company_id=company.id,
                employee_id=leave_request.employee_id,
                date=current,
                status='leave',
                notes=f'{leave_request.leave_type.capitalize()} Leave - {leave_request.reason}'
            )
            db.session.add(attendance)
        
        current += timedelta(days=1)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Leave request approved',
        'request': leave_request.to_dict(include_approver=True)
    }), 200


@leave_bp.route('/reject', methods=['POST'])
@token_required
@company_admin_required
def reject_leave():
    """Reject a leave request"""
    hr = request.current_user
    company = request.current_company
    data = request.get_json()
    
    if not data.get('request_id'):
        return jsonify({'success': False, 'message': 'request_id is required'}), 400
    
    leave_request = LeaveRequest.query.filter_by(
        id=data['request_id'],
        company_id=company.id
    ).first()
    
    if not leave_request:
        return jsonify({'success': False, 'message': 'Leave request not found'}), 404
    
    if leave_request.status != 'pending':
        return jsonify({
            'success': False, 
            'message': f'Cannot reject a {leave_request.status} request'
        }), 400
    
    # Update request
    leave_request.status = 'rejected'
    leave_request.approved_by = hr.id
    leave_request.rejection_reason = data.get('reason', 'No reason provided')
    leave_request.approval_date = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Leave request rejected',
        'request': leave_request.to_dict(include_approver=True)
    }), 200


@leave_bp.route('/statistics', methods=['GET'])
@token_required
@company_admin_required
def get_leave_statistics():
    """Get leave statistics for admin"""
    company = request.current_company
    month = int(request.args.get('month', date.today().month))
    year = int(request.args.get('year', date.today().year))
    
    # Date range for the month
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    # Get all requests for this month
    requests = LeaveRequest.query.filter(
        LeaveRequest.company_id == company.id,
        LeaveRequest.start_date <= last_day,
        LeaveRequest.end_date >= first_day
    ).all()
    
    # Calculate statistics
    stats = {
        'total_requests': len(requests),
        'approved': len([r for r in requests if r.status == 'approved']),
        'pending': len([r for r in requests if r.status == 'pending']),
        'rejected': len([r for r in requests if r.status == 'rejected']),
        'by_type': {},
        'by_employee': {}
    }
    
    for req in requests:
        # Count by type
        leave_type = req.leave_type
        if leave_type not in stats['by_type']:
            stats['by_type'][leave_type] = 0
        stats['by_type'][leave_type] += 1
        
        # Count by employee
        emp_id = req.employee.employee_id
        if emp_id not in stats['by_employee']:
            stats['by_employee'][emp_id] = {
                'name': req.employee.name,
                'approved_days': 0,
                'pending_days': 0,
                'rejected_days': 0
            }
        
        days = req.days_requested()
        if req.status == 'approved':
            stats['by_employee'][emp_id]['approved_days'] += days
        elif req.status == 'pending':
            stats['by_employee'][emp_id]['pending_days'] += days
        elif req.status == 'rejected':
            stats['by_employee'][emp_id]['rejected_days'] += days
    
    return jsonify({
        'success': True,
        'month': month,
        'year': year,
        'statistics': stats
    }), 200


@leave_bp.route('/cancel/<int:request_id>', methods=['POST'])
@token_required
def cancel_leave_request(request_id):
    """Cancel own pending leave request"""
    emp = request.current_user
    company = request.current_company
    
    leave_request = LeaveRequest.query.filter_by(
        id=request_id,
        company_id=company.id,
        employee_id=emp.id
    ).first()
    
    if not leave_request:
        return jsonify({'success': False, 'message': 'Leave request not found'}), 404
    
    if leave_request.status != 'pending':
        return jsonify({
            'success': False, 
            'message': f'Cannot cancel a {leave_request.status} request'
        }), 400
    
    db.session.delete(leave_request)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Leave request cancelled'
    }), 200