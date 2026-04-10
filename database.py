"""
database.py - Multi-Tenant Database Models
Supports multiple companies with complete data isolation
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import bcrypt

db = SQLAlchemy()


# ===== COMPANY MODEL (NEW) =====
class Company(db.Model):
    """Represents a company/organization"""
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    subscription_plan = db.Column(db.String(20), default='free')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    employees = db.relationship('Employee', backref='company', lazy=True, cascade='all, delete-orphan')
    attendance_records = db.relationship('AttendanceRecord', backref='company', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'email': self.email,
            'subscription_plan': self.subscription_plan,
            'employee_count': len(self.employees),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }


# ===== EMPLOYEE MODEL (UPDATED) =====
class Employee(db.Model):
    """Represents an employee - NOW WITH COMPANY ISOLATION"""
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)  # ⭐ NEW
    employee_id = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    department = db.Column(db.String(100), default='General')
    role = db.Column(db.String(20), default='employee')  # 'employee', 'admin', 'owner'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    attendance_records = db.relationship('AttendanceRecord', backref='employee', lazy=True, cascade='all, delete-orphan')

    # Unique constraint: employee_id per company
    __table_args__ = (
        db.UniqueConstraint('company_id', 'employee_id', name='unique_company_employee_id'),
        db.UniqueConstraint('company_id', 'email', name='unique_company_email'),
    )

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def to_dict(self, include_company=False):
        data = {
            'id': self.id,
            'employee_id': self.employee_id,
            'name': self.name,
            'email': self.email,
            'department': self.department,
            'role': self.role,
            'is_active': self.is_active,
            'company_id': self.company_id
        }
        if include_company:
            data['company'] = self.company.to_dict()
        return data


# ===== ATTENDANCE RECORD MODEL (UPDATED) =====
class AttendanceRecord(db.Model):
    """Attendance records - NOW WITH COMPANY ISOLATION"""
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)  # ⭐ NEW
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    check_in = db.Column(db.DateTime, nullable=True)
    check_out = db.Column(db.DateTime, nullable=True)
    work_minutes = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default='absent')  # present, absent, late
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('company_id', 'employee_id', 'date', name='unique_company_employee_date'),
    )

    def calculate_work_minutes(self):
        if self.check_in and self.check_out:
            delta = self.check_out - self.check_in
            self.work_minutes = int(delta.total_seconds() / 60)

    def determine_status(self, late_threshold_hour=9, late_threshold_minute=30):
        """Mark as late if checked in after 9:30 AM"""
        if self.check_in:
            ci = self.check_in
            if ci.hour > late_threshold_hour or (ci.hour == late_threshold_hour and ci.minute > late_threshold_minute):
                self.status = 'late'
            else:
                self.status = 'present'

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'check_in': self.check_in.isoformat() if self.check_in else None,
            'check_out': self.check_out.isoformat() if self.check_out else None,
            'work_minutes': self.work_minutes,
            'status': self.status,
            'notes': self.notes
        }
# ===== LEAVE REQUEST MODEL (NEW) =====
class LeaveRequest(db.Model):
    """Leave requests by employees"""
    __tablename__ = 'leave_requests'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    leave_type = db.Column(db.String(20), nullable=False)  # 'sick', 'casual', 'earned', 'unpaid'
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    approved_by = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)  # HR who approved
    approval_date = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    employee = db.relationship('Employee', foreign_keys=[employee_id], backref='leave_requests')
    approved_by_employee = db.relationship('Employee', foreign_keys=[approved_by])

    # Unique constraint: one leave request per date range per employee per company
    __table_args__ = (
        db.UniqueConstraint('company_id', 'employee_id', 'start_date', 'end_date', 
                           name='unique_company_employee_dates'),
    )

    def days_requested(self):
        """Calculate number of days requested"""
        if self.start_date and self.end_date:
            delta = self.end_date - self.start_date
            return delta.days + 1
        return 0

    def to_dict(self, include_employee=False, include_approver=False):
        data = {
            'id': self.id,
            'leave_type': self.leave_type,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'reason': self.reason,
            'status': self.status,
            'days_requested': self.days_requested(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

        if include_employee:
            data['employee'] = {
                'id': self.employee.id,
                'employee_id': self.employee.employee_id,
                'name': self.employee.name,
                'email': self.employee.email,
                'department': self.employee.department
            }

        if include_approver and self.approved_by_employee:
            data['approved_by'] = {
                'employee_id': self.approved_by_employee.employee_id,
                'name': self.approved_by_employee.name
            }
            data['approval_date'] = self.approval_date.isoformat() if self.approval_date else None
            data['rejection_reason'] = self.rejection_reason

        return data

def init_db(app):
    """
    FAST: Only create tables on startup (no bcrypt hashing).
    Seed demo data on first API request via seed_demo_data().
    """
    with app.app_context():
        db.create_all()
        # That's it! Tables created, app is ready instantly ✅


def seed_demo_data(app):
    """
    Seed demo data on first request (only if needed).
    This is called lazily by @app.before_request, not on startup.
    """
    with app.app_context():
        try:
            # Only seed if company doesn't exist
            if Company.query.count() > 0:
                return  # Already seeded, skip
        except Exception:
            # If query fails, assume already seeded
            return
        
        print("📊 Seeding demo data on first request...")
        
        company = Company(
            company_id='COMP001',
            name='Demo Company',
            email='admin@demo.com',
            subscription_plan='free'
        )
        db.session.add(company)
        db.session.flush()

        # Create default owner
        owner = Employee(
            company_id=company.id,
            employee_id='OWNER001',
            name='Company Owner',
            email='owner@demo.com',
            department='Management',
            role='owner'
        )
        owner.set_password('Owner@123')
        db.session.add(owner)

        # Create default admin
        admin = Employee(
            company_id=company.id,
            employee_id='ADMIN001',
            name='Office Admin',
            email='admin@demo.com',
            department='Management',
            role='admin'
        )
        admin.set_password('Admin@123')
        db.session.add(admin)

        # Create sample employees
        sample_employees = [
            ('EMP001', 'Rahul Sharma', 'rahul@demo.com', 'Engineering'),
            ('EMP002', 'Priya Singh', 'priya@demo.com', 'Design'),
            ('EMP003', 'Amit Kumar', 'amit@demo.com', 'Marketing'),
        ]
        for emp_id, name, email, dept in sample_employees:
            emp = Employee(
                company_id=company.id,
                employee_id=emp_id,
                name=name,
                email=email,
                department=dept,
                role='employee'
            )
            emp.set_password('Emp@123')
            db.session.add(emp)

        db.session.commit()
        print("✅ Demo data seeded!")
        print("   Company: COMP001 / Demo Company")
        print("   Owner: OWNER001 / Owner@123")
        print("   Admin: ADMIN001 / Admin@123")
        print("   Employees: EMP001, EMP002, EMP003 / Emp@123")