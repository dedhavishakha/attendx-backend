# AttendX - Employee Attendance Management System

Modern, multi-tenant attendance tracking system with Chrome extension.

## Features
- Real-time check-in/check-out
- Leave management
- Work hours tracking
- Admin dashboard
- Multi-company support

## Tech Stack
- Backend: Flask + PostgreSQL
- Frontend: Chrome Extension
- Cloud: AWS Elastic Beanstalk

## Setup (Development)

### Prerequisites
- Python 3.11+
- PostgreSQL (optional, SQLite for dev)
- Chrome browser

### Installation

1. Clone repository
\\\ash
git clone https://github.com/dedhavishakha/attendx-backend.git
cd attendx-backend
\\\

2. Create virtual environment
\\\ash
python -m venv venv
source venv\Scripts\activate
\\\

3. Install dependencies
\\\ash
pip install -r requirements.txt
\\\

4. Run application
\\\ash
python app.py
\\\

App runs at: http://localhost:5000

## Deployment

See AWS_DEPLOYMENT_COMPLETE_GUIDE.md for production deployment.

## License

Proprietary - All rights reserved
