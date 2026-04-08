"""
routes/auth.py - Multi-Tenant JWT Authentication
"""

from flask import Blueprint, request, jsonify
from database import db, Employee
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps

auth_bp = Blueprint('auth', __name__)
SECRET = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')


def create_token(employee_id, company_id):
    """Create JWT token with company context"""
    payload = {
        'sub': employee_id,
        'company_id': company_id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET, algorithm='HS256')


def token_required(f):
    """Verify JWT token and load current user"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        
        if not token:
            token = request.args.get('token')
        
        if not token:
            return jsonify({'success': False, 'message': 'Token missing'}), 401
        
        try:
            data = jwt.decode(token, SECRET, algorithms=['HS256'])
            
            emp = Employee.query.filter_by(employee_id=data['sub']).first()
            
            if not emp or not emp.is_active:
                return jsonify({'success': False, 'message': 'User not found'}), 401
            
            # SECURITY: Verify company_id matches (prevent token swapping)
            if emp.company_id != data['company_id']:
                return jsonify({'success': False, 'message': 'Invalid company context'}), 401
            
            request.current_user = emp
            request.current_company = emp.company
            
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'message': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'message': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    
    return decorated


def company_admin_required(f):
    """Require admin or owner role"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.current_user.role not in ['owner', 'admin', 'hr']:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    
    return decorated


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login with email/ID + password"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    identifier = data.get('employee_id') or data.get('identifier') or data.get('email')
    password = data.get('password')
    
    if not identifier or not password:
        return jsonify({'success': False, 'message': 'Email/ID and password required'}), 400
    
    emp = Employee.query.filter(
        (Employee.employee_id == identifier) | (Employee.email == identifier)
    ).first()
    
    if not emp or not emp.check_password(password):
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    
    if not emp.is_active:
        return jsonify({'success': False, 'message': 'Account is inactive'}), 403
    
    token = create_token(emp.employee_id, emp.company_id)
    
    return jsonify({
        'success': True,
        'token': token,
        'user': emp.to_dict(include_company=True),
        'company': emp.company.to_dict()
    }), 200


@auth_bp.route('/me', methods=['GET'])
@token_required
def me():
    """Get current user info"""
    return jsonify({
        'success': True,
        'user': request.current_user.to_dict(include_company=True),
        'company': request.current_company.to_dict()
    }), 200


@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password():
    """Change password"""
    data = request.get_json()
    
    if not data.get('old_password') or not data.get('new_password'):
        return jsonify({'success': False, 'message': 'Both passwords required'}), 400
    
    emp = request.current_user
    
    if not emp.check_password(data['old_password']):
        return jsonify({'success': False, 'message': 'Current password is incorrect'}), 401
    
    emp.set_password(data['new_password'])
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Password changed successfully'}), 200


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """Logout (token deleted on client)"""
    return jsonify({'success': True, 'message': 'Logged out successfully'}), 200