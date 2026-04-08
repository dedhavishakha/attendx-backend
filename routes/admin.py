"""
routes/admin.py - Multi-Tenant Admin Management
"""

from flask import Blueprint, request, jsonify
from database import db, Employee, AttendanceRecord, Company
from routes.auth import token_required, company_admin_required
from datetime import date

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/employees', methods=['GET'])
@token_required
def list_employees():
    """List employees in company"""
    company = request.current_company
    
    employees = Employee.query.filter_by(
        company_id=company.id,
        is_active=True
    ).all()
    
    return jsonify({
        'success': True,
        'employees': [e.to_dict() for e in employees]
    }), 200


@admin_bp.route('/employees', methods=['POST'])
@token_required
@company_admin_required
def add_employee():
    """Add new employee to company"""
    company = request.current_company
    data = request.get_json()
    
    required = ['employee_id', 'name', 'email', 'password']
    for field in required:
        if not data.get(field):
            return jsonify({'success': False, 'message': f'{field} is required'}), 400
    
    # Check uniqueness within company
    if Employee.query.filter_by(company_id=company.id, employee_id=data['employee_id']).first():
        return jsonify({'success': False, 'message': 'Employee ID already exists in company'}), 409
    
    if Employee.query.filter_by(company_id=company.id, email=data['email']).first():
        return jsonify({'success': False, 'message': 'Email already exists in company'}), 409
    
    emp = Employee(
        company_id=company.id,
        employee_id=data['employee_id'],
        name=data['name'],
        email=data['email'],
        department=data.get('department', 'General'),
        role=data.get('role', 'employee')
    )
    emp.set_password(data['password'])
    db.session.add(emp)
    db.session.commit()
    
    return jsonify({'success': True, 'employee': emp.to_dict()}), 201


@admin_bp.route('/employees/<emp_id>', methods=['PUT'])
@token_required
@company_admin_required
def update_employee(emp_id):
    """Update employee"""
    company = request.current_company
    
    emp = Employee.query.filter_by(
        company_id=company.id,
        employee_id=emp_id
    ).first()
    
    if not emp:
        return jsonify({'success': False, 'message': 'Employee not found'}), 404
    
    data = request.get_json()
    
    for field in ['name', 'email', 'department', 'role']:
        if field in data:
            setattr(emp, field, data[field])
    
    if 'password' in data and data['password']:
        emp.set_password(data['password'])
    
    db.session.commit()
    
    return jsonify({'success': True, 'employee': emp.to_dict()}), 200


@admin_bp.route('/employees/<emp_id>', methods=['DELETE'])
@token_required
@company_admin_required
def deactivate_employee(emp_id):
    """Deactivate employee"""
    company = request.current_company
    
    emp = Employee.query.filter_by(
        company_id=company.id,
        employee_id=emp_id
    ).first()
    
    if not emp:
        return jsonify({'success': False, 'message': 'Employee not found'}), 404
    
    if emp.role == 'owner':
        return jsonify({'success': False, 'message': 'Cannot deactivate company owner'}), 400
    
    emp.is_active = False
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Employee deactivated'}), 200