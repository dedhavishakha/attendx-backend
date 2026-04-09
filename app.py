# """
# app.py - Multi-Tenant Flask Application
# """

# from flask import Flask
# from flask_cors import CORS
# from database import db, init_db
# import os

# app = Flask(__name__)

# # ===== CONFIGURATION =====
# app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
#     'DATABASE_URL',
#     'sqlite:///attendance.db'
# )
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# # ===== CORS SETUP =====
# CORS(app, origins=['chrome-extension://*', 'http://localhost:*', 'http://127.0.0.1:*'])

# # ===== DATABASE INITIALIZATION =====
# db.init_app(app)

# # ===== IMPORT & REGISTER BLUEPRINTS =====
# from routes.auth import auth_bp
# from routes.attendance import attendance_bp
# from routes.attendance_export import attendance_export_bp
# from routes.admin import admin_bp
# from routes.company import company_bp
# from routes.leave import leave_bp

# app.register_blueprint(auth_bp, url_prefix='/api/auth')
# app.register_blueprint(attendance_bp, url_prefix='/api/attendance')
# app.register_blueprint(attendance_export_bp, url_prefix='/api/attendance')
# app.register_blueprint(admin_bp, url_prefix='/api/admin')
# app.register_blueprint(company_bp, url_prefix='/api/company')
# app.register_blueprint(leave_bp, url_prefix='/api/leave')


# # ===== HEALTH CHECK =====
# @app.route('/api/health', methods=['GET'])
# def health():
#     from datetime import datetime
#     return {
#         'status': 'ok',
#         'version': '2.0',
#         'timestamp': datetime.utcnow().isoformat(),
#         'mode': 'multi-tenant-saas'
#     }, 200

# # ===== ERROR HANDLERS =====
# @app.errorhandler(400)
# def bad_request(e):
#     return {'success': False, 'message': 'Bad request', 'status': 400}, 400

# @app.errorhandler(401)
# def unauthorized(e):
#     return {'success': False, 'message': 'Unauthorized', 'status': 401}, 401

# @app.errorhandler(403)
# def forbidden(e):
#     return {'success': False, 'message': 'Forbidden', 'status': 403}, 403

# @app.errorhandler(404)
# def not_found(e):
#     return {'success': False, 'message': 'Not found', 'status': 404}, 404

# @app.errorhandler(500)
# def internal_error(e):
#     return {'success': False, 'message': 'Internal server error', 'status': 500}, 500

# # ===== MAIN =====
# if __name__ == '__main__':
#     # NOTE: init_db() is commented out for AWS deployment
#     # Database tables will be created on first API call via db.create_all()
#     # Uncomment below if running locally and need to reset DB
#     with app.app_context():
#         init_db(app)
    
#     app.run(
#         host='0.0.0.0',
#         port=int(os.environ.get('PORT', 5000)),
#         debug=os.environ.get('DEBUG', 'False') == 'True'
#     )



"""
app.py - Multi-Tenant Flask Application
"""

from flask import Flask
from flask_cors import CORS
from database import db, init_db
import os

app = Flask(__name__)

# ===== CONFIGURATION =====
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:///attendance.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ===== CORS SETUP =====
CORS(app, origins=['chrome-extension://*', 'http://localhost:*', 'http://127.0.0.1:*'])

# ===== DATABASE INITIALIZATION =====
db.init_app(app)

# Initialize database on app startup (runs when gunicorn imports app)
with app.app_context():
    init_db(app)

# ===== IMPORT & REGISTER BLUEPRINTS =====
from routes.auth import auth_bp
from routes.attendance import attendance_bp
from routes.attendance_export import attendance_export_bp
from routes.admin import admin_bp
from routes.company import company_bp
from routes.leave import leave_bp

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(attendance_bp, url_prefix='/api/attendance')
app.register_blueprint(attendance_export_bp, url_prefix='/api/attendance')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(company_bp, url_prefix='/api/company')
app.register_blueprint(leave_bp, url_prefix='/api/leave')


# ===== HEALTH CHECK =====
@app.route('/api/health', methods=['GET'])
def health():
    from datetime import datetime
    return {
        'status': 'ok',
        'version': '2.0',
        'timestamp': datetime.utcnow().isoformat(),
        'mode': 'multi-tenant-saas'
    }, 200

# ===== ERROR HANDLERS =====
@app.errorhandler(400)
def bad_request(e):
    return {'success': False, 'message': 'Bad request', 'status': 400}, 400

@app.errorhandler(401)
def unauthorized(e):
    return {'success': False, 'message': 'Unauthorized', 'status': 401}, 401

@app.errorhandler(403)
def forbidden(e):
    return {'success': False, 'message': 'Forbidden', 'status': 403}, 403

@app.errorhandler(404)
def not_found(e):
    return {'success': False, 'message': 'Not found', 'status': 404}, 404

@app.errorhandler(500)
def internal_error(e):
    return {'success': False, 'message': 'Internal server error', 'status': 500}, 500

# ===== MAIN =====
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('DEBUG', 'False') == 'True'
    )