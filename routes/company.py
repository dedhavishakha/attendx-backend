"""
routes/company.py - Company management and signup
"""

from flask import Blueprint, request, jsonify
from database import db, Company, Employee
from routes.auth import token_required
from datetime import datetime

company_bp = Blueprint('company', __name__)


@company_bp.route('/signup', methods=['POST'])
def company_signup():
    """
    Create new company with owner account only
    
    Request:
    {
        "company_name": "My Company",
        "company_email": "admin@company.com",
        "owner_name": "John Doe",
        "owner_id": "OWNER001",
        "owner_email": "john@company.com",
        "password": "Password@123"
    }
    
    Returns:
    - Company created
    - Owner account created with custom owner_id
    """
    try:
        data = request.get_json()
        
        # Validation
        required = ['company_name', 'company_email', 'owner_name', 'owner_id', 'owner_email', 'password']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        owner_id = data['owner_id'].strip()
        
        # Validate owner ID
        if len(owner_id) < 3:
            return jsonify({'success': False, 'message': 'Owner ID must be at least 3 characters'}), 400
        
        # Check if company email exists
        existing_company = Company.query.filter_by(email=data['company_email']).first()
        if existing_company:
            return jsonify({'success': False, 'message': 'Company email already exists'}), 409
        
        # Check if owner email exists
        existing_employee = Employee.query.filter_by(email=data['owner_email']).first()
        if existing_employee:
            return jsonify({'success': False, 'message': 'Owner email already in use'}), 409
        
        # Check if owner ID already exists
        existing_owner_id = Employee.query.filter_by(employee_id=owner_id).first()
        if existing_owner_id:
            return jsonify({'success': False, 'message': 'Owner ID already exists'}), 409
        
        # Create company
        company = Company(
            company_id=f"COMP{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            name=data['company_name'],
            email=data['company_email'],
            subscription_plan='free'
        )
        db.session.add(company)
        db.session.flush()
        
        # Create OWNER account with custom owner ID
        owner = Employee(
            company_id=company.id,
            employee_id=owner_id,
            name=data['owner_name'],
            email=data['owner_email'],
            department='Management',
            role='owner'
        )
        owner.set_password(data['password'])
        db.session.add(owner)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Company created successfully!',
            'company': {
                'id': company.id,
                'company_id': company.company_id,
                'name': company.name,
                'email': company.email,
                'subscription_plan': company.subscription_plan,
                'is_active': company.is_active,
                'created_at': company.created_at.isoformat() if company.created_at else None
            },
            'owner': {
                'id': owner.id,
                'employee_id': owner.employee_id,
                'name': owner.name,
                'email': owner.email,
                'role': owner.role
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@company_bp.route('/info', methods=['GET'])
@token_required
def get_company_info():
    """Get current company information"""
    try:
        company = request.current_user.company
        return jsonify({
            'success': True,
            'company': {
                'id': company.id,
                'company_id': company.company_id,
                'name': company.name,
                'email': company.email,
                'subscription_plan': company.subscription_plan,
                'is_active': company.is_active
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@company_bp.route('/stats', methods=['GET'])
@token_required
def get_company_stats():
    """Get company statistics"""
    if request.current_user.role not in ('admin', 'owner'):
        return jsonify({'success': False, 'message': 'Admin only'}), 403
    
    try:
        company = request.current_user.company
        employees = company.employees if hasattr(company, 'employees') else []
        
        active = len([e for e in employees if e.is_active])
        
        return jsonify({
            'success': True,
            'stats': {
                'total_employees': len(employees),
                'active_employees': active,
                'inactive_employees': len(employees) - active
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400