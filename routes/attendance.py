"""
routes/attendance.py - Company-Isolated Attendance Tracking
"""

from flask import Blueprint, request, jsonify, Response
from database import db, AttendanceRecord, Employee, LeaveRequest
from routes.auth import token_required, company_admin_required
from datetime import datetime, date, timedelta, timezone
import csv
import io

attendance_bp = Blueprint('attendance', __name__)

# India Standard Time (IST) - UTC+5:30
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now():
    """Get current time in IST (India Standard Time)"""
    return datetime.now(IST)

def get_ist_today():
    """Get today's date in IST"""
    return get_ist_now().date()


@attendance_bp.route('/checkin', methods=['POST'])
@token_required
def checkin():
    """Employee check-in"""
    emp = request.current_user
    company = request.current_company
    today = get_ist_today()
    now = get_ist_now()
    
    # CHECK IF USER IS ON APPROVED LEAVE TODAY
    leave_today = LeaveRequest.query.filter(
        LeaveRequest.company_id == company.id,
        LeaveRequest.employee_id == emp.id,
        LeaveRequest.status == 'approved',
        LeaveRequest.start_date <= today,
        LeaveRequest.end_date >= today
    ).first()
    
    if leave_today:
        return jsonify({
            'success': False,
            'message': f'❌ You are on approved {leave_today.leave_type.upper()} leave today. You cannot check-in.'
        }), 403
    
    record = AttendanceRecord.query.filter_by(
        company_id=company.id,
        employee_id=emp.id,
        date=today
    ).first()
    
    if record and record.check_in:
        return jsonify({'success': False, 'message': 'Already checked in today'}), 400
    
    if not record:
        record = AttendanceRecord(
            company_id=company.id,
            employee_id=emp.id,
            date=today
        )
        db.session.add(record)
    
    # Convert timezone-aware datetime to naive datetime for storage
    record.check_in = now.replace(tzinfo=None)
    record.determine_status()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Checked in successfully',
        'record': record.to_dict()
    }), 200


@attendance_bp.route('/checkout', methods=['POST'])
@token_required
def checkout():
    """Employee check-out"""
    emp = request.current_user
    company = request.current_company
    today = get_ist_today()
    now = get_ist_now()
    
    record = AttendanceRecord.query.filter_by(
        company_id=company.id,
        employee_id=emp.id,
        date=today
    ).first()
    
    if not record or not record.check_in:
        return jsonify({'success': False, 'message': 'You have not checked in today'}), 400
    
    if record.check_out:
        return jsonify({'success': False, 'message': 'Already checked out today'}), 400
    
    # Convert timezone-aware datetime to naive datetime for storage
    record.check_out = now.replace(tzinfo=None)
    record.calculate_work_minutes()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Checked out successfully',
        'record': record.to_dict()
    }), 200


@attendance_bp.route('/today', methods=['GET'])
@token_required
def today_status():
    """Get today's status"""
    emp = request.current_user
    company = request.current_company
    today = get_ist_today()
    
    record = AttendanceRecord.query.filter_by(
        company_id=company.id,
        employee_id=emp.id,
        date=today
    ).first()
    
    return jsonify({
        'success': True,
        'record': record.to_dict() if record else None
    }), 200


@attendance_bp.route('/week', methods=['GET'])
@token_required
def week_summary():
    """Get week summary"""
    emp = request.current_user
    company = request.current_company
    today = get_ist_today()
    
    monday = today - timedelta(days=today.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]
    
    records = AttendanceRecord.query.filter(
        AttendanceRecord.company_id == company.id,
        AttendanceRecord.employee_id == emp.id,
        AttendanceRecord.date >= monday,
        AttendanceRecord.date <= monday + timedelta(days=6)
    ).all()
    
    records_by_date = {r.date: r for r in records}
    
    week_data = []
    for d in week_dates:
        rec = records_by_date.get(d)
        if rec and rec.check_in:
            h = (rec.work_minutes or 0) // 60
            m = (rec.work_minutes or 0) % 60
            week_data.append({
                'date': d.isoformat(),
                'day': d.strftime('%A'),
                'present': True,
                'hours': f"{h}h {m}m",
                'status': rec.status
            })
        else:
            week_data.append({
                'date': d.isoformat(),
                'day': d.strftime('%A'),
                'present': False,
                'hours': '',
                'status': 'absent' if d < today else 'future'
            })
    
    return jsonify({'success': True, 'week': week_data}), 200


@attendance_bp.route('/history', methods=['GET'])
@token_required
def history():
    """Get attendance history"""
    emp = request.current_user
    company = request.current_company
    limit = int(request.args.get('limit', 10))
    
    records = AttendanceRecord.query.filter_by(
        company_id=company.id,
        employee_id=emp.id
    ).order_by(AttendanceRecord.date.desc()).limit(limit).all()
    
    return jsonify({
        'success': True,
        'records': [r.to_dict() for r in records]
    }), 200


@attendance_bp.route('/admin/attendance', methods=['GET'])
@token_required
@company_admin_required
def admin_attendance():
    """[ADMIN] Get all employees' attendance for a date"""
    company = request.current_company
    date_str = request.args.get('date', get_ist_today().isoformat())
    
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date format'}), 400
    
    employees = Employee.query.filter_by(
        company_id=company.id,
        is_active=True,
        role='employee'
    ).all()
    
    records = AttendanceRecord.query.filter_by(
        company_id=company.id,
        date=target_date
    ).all()
    
    records_by_emp = {r.employee_id: r for r in records}
    
    result = []
    for emp in employees:
        rec = records_by_emp.get(emp.id)
        row = {
            'employee_id': emp.employee_id,
            'name': emp.name,
            'email': emp.email,
            'department': emp.department,
            'date': target_date.isoformat(),
            'check_in': rec.check_in.isoformat() if rec and rec.check_in else None,
            'check_out': rec.check_out.isoformat() if rec and rec.check_out else None,
            'work_minutes': rec.work_minutes if rec else None,
            'status': rec.status if rec else 'absent'
        }
        result.append(row)
    
    return jsonify({
        'success': True,
        'records': result,
        'date': date_str,
        'company': company.name
    }), 200


@attendance_bp.route('/admin/export', methods=['GET'])
@token_required
@company_admin_required
def export_csv():
    """[ADMIN] Export attendance as CSV"""
    company = request.current_company
    date_str = request.args.get('date', get_ist_today().isoformat())
    date_from = request.args.get('from')
    date_to = request.args.get('to')
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Employee ID', 'Name', 'Email', 'Department', 'Date',
                     'Check In', 'Check Out', 'Work Hours', 'Work Minutes', 'Status'])
    
    def fmt_time(iso):
        if not iso:
            return '—'
        return datetime.fromisoformat(iso).strftime('%I:%M %p')
    
    def fmt_hours(mins):
        if not mins:
            return '—'
        return f"{mins//60}h {mins%60}m"
    
    if date_from and date_to:
        start = date.fromisoformat(date_from)
        end = date.fromisoformat(date_to)
        current = start
        all_records = []
        while current <= end:
            records = AttendanceRecord.query.filter_by(
                company_id=company.id,
                date=current
            ).all()
            all_records.extend(records)
            current += timedelta(days=1)
        filename = f"attendance_{company.company_id}_{date_from}_to_{date_to}.csv"
    else:
        target_date = date.fromisoformat(date_str)
        all_records = AttendanceRecord.query.filter_by(
            company_id=company.id,
            date=target_date
        ).all()
        filename = f"attendance_{company.company_id}_{date_str}.csv"
    
    for r in all_records:
        emp = r.employee
        writer.writerow([
            emp.employee_id, emp.name, emp.email, emp.department,
            r.date.isoformat(), fmt_time(r.check_in.isoformat() if r.check_in else None),
            fmt_time(r.check_out.isoformat() if r.check_out else None),
            fmt_hours(r.work_minutes), r.work_minutes or 0, r.status
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    ), 200


@attendance_bp.route('/admin/stats', methods=['GET'])
@token_required
@company_admin_required
def monthly_stats():
    """[ADMIN] Get monthly statistics"""
    company = request.current_company
    today_ist = get_ist_today()
    month = int(request.args.get('month', today_ist.month))
    year = int(request.args.get('year', today_ist.year))
    
    employees = Employee.query.filter_by(
        company_id=company.id,
        is_active=True,
        role='employee'
    ).all()
    
    stats = []
    
    for emp in employees:
        records = AttendanceRecord.query.filter(
            AttendanceRecord.company_id == company.id,
            AttendanceRecord.employee_id == emp.id,
            db.extract('month', AttendanceRecord.date) == month,
            db.extract('year', AttendanceRecord.date) == year
        ).all()
        
        total_days = len(records)
        present = len([r for r in records if r.status in ('present', 'late')])
        late = len([r for r in records if r.status == 'late'])
        total_minutes = sum(r.work_minutes or 0 for r in records)
        
        stats.append({
            'employee_id': emp.employee_id,
            'name': emp.name,
            'department': emp.department,
            'present_days': present,
            'late_days': late,
            'absent_days': total_days - present,
            'total_work_hours': round(total_minutes / 60, 1) if total_minutes else 0
        })
    
    return jsonify({
        'success': True,
        'stats': stats,
        'month': month,
        'year': year,
        'company': company.name
    }), 200