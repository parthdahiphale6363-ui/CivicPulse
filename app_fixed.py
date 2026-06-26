from flask import Flask, render_template, request, redirect, session, jsonify, flash, url_for, Response
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import requests
import json
import csv
import io
from datetime import datetime
from functools import wraps
import re
import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import logging
from logging.handlers import RotatingFileHandler

from geopy.distance import geodesic
from cv_utils import get_image_embedding, calculate_similarity

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# ---------------- RATE LIMITING ----------------
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per day", "200 per hour"],
    storage_uri="memory://"
)

from civic_iq import civic_iq_bp
app.register_blueprint(civic_iq_bp)

# ---------------- GLOBAL ERROR HANDLING ----------------
handler = RotatingFileHandler('app_errors.log', maxBytes=100000, backupCount=3)
handler.setLevel(logging.ERROR)
app.logger.addHandler(handler)

@app.errorhandler(404)
def not_found_error(error):
    app.logger.error(f'Page not found: {request.url}')
    return "Not Found", 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'Server Error: {error}')
    return "Internal Server Error", 500

@app.errorhandler(Exception)
def unhandled_exception(e):
    app.logger.error(f'Unhandled Exception: {e}')
    return "Internal Server Error", 500

# Persistent Storage Logic (for Fly.io / Volumes)
DATA_DIR = "/data" if os.path.exists("/data") else os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(DATA_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------- EMAIL CONFIG ----------------
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 465
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "") # Gmail App Password

# ---------------- TWILIO CONFIG ----------------
TWILIO_SID = os.environ.get("TWILIO_SID", "")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN", "")
TWILIO_NUMBER = os.environ.get("TWILIO_NUMBER", "")


def send_sms_otp(target_phone, otp_code):
    """Send a real SMS OTP via Twilio."""
    if not TWILIO_SID or not TWILIO_TOKEN or not TWILIO_NUMBER:
        return False, "Twilio not configured in .env"

    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        message = client.messages.create(
            body=f"Your CivicPulse verification code is: {otp_code}",
            from_=TWILIO_NUMBER,
            to=f"+91{target_phone}" if len(target_phone) == 10 else target_phone,
        )
        return True, "Success"
    except Exception as e:
        return False, str(e)


def send_email_otp(target_email, otp_code):
    """Send a REAL OTP email using Resend (HTTPS API)."""
    resend_api_key = os.environ.get("RESEND_API_KEY", "").strip()
    if not resend_api_key:
        return False, "Resend not configured: RESEND_API_KEY is missing"

    # Resend requires a verified sender (domain/email)
    sender = os.environ.get("RESEND_FROM_EMAIL", "").strip() or MAIL_USERNAME.strip()
    if not sender:
        return False, "Resend sender not configured: set RESEND_FROM_EMAIL (or MAIL_USERNAME)"

    subject = f"Verification Code: {otp_code} — CivicPulse"
    html_body = f"""
    <h2>CivicPulse Verification</h2>
    <p>Your verification code is: <strong style=\"font-size: 24px; color: #6366f1;\">{otp_code}</strong></p>
    <p>This code will expire in 10 minutes. Please enter it on the registration page to verify your account.</p>
    <br>
    <p>Team CivicPulse</p>
    """.strip()

    payload = {
        "from": sender,
        "to": [target_email],
        "subject": subject,
        "html": html_body,
    }

    headers = {
        "Authorization": f"Bearer {resend_api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers=headers,
            json=payload,
            timeout=20,
        )

        if response.status_code >= 400:
            app.logger.error(
                f"OTP email send failed for {target_email}: HTTP {response.status_code} - {response.text}"
            )
            return False, f"Resend API error: HTTP {response.status_code}"

        return True, "Success"
    except Exception as e:
        app.logger.error(
            f"OTP email send failed for {target_email}: {type(e).__name__}: {e}"
        )
        return False, f"Resend request failed: {type(e).__name__}"


# ---------------- CSRF PROTECTION ----------------
app.config['WTF_CSRF_SECRET_KEY'] = app.secret_key
app.config['WTF_CSRF_CHECK_DEFAULT'] = False
csrf = CSRFProtect(app)

@app.before_request
def manual_csrf_check():
    if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        if request.path.startswith('/api/') or request.path.startswith('/live-pulse'):
            return
        from flask_wtf.csrf import validate_csrf
        try:
            validate_csrf(request.form.get('csrf_token'))
        except Exception:
            return "CSRF verification failed", 400

@app.after_request
def inject_csrf_token(response):
    if response.content_type and 'text/html' in response.content_type:
        html = response.get_data(as_text=True)
        if '<form' in html.lower():
            csrf_input = f'<input type="hidden" name="csrf_token" value="{generate_csrf()}"/>'
            html = re.sub(r'(<form[^>]*>)', rf'\1\n{csrf_input}', html, flags=re.IGNORECASE)
            response.set_data(html)
    return response


# ---------------- DATABASE CONNECTION ----------------
DB_PATH = os.path.join(DATA_DIR, "database.db")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{DB_PATH}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class DBConnectionWrapper:
    def __init__(self):
        self.session = db.session()

    def execute(self, sql, params=()):
        param_idx = 0

        def replace_qm(match):
            nonlocal param_idx
            replacement = f":p{param_idx}"
            param_idx += 1
            return replacement

        converted_sql = re.sub(r'\?', replace_qm, sql)

        if isinstance(params, (tuple, list)):
            dict_params = {f"p{i}": val for i, val in enumerate(params)}
        elif isinstance(params, dict):
            dict_params = params
        else:
            dict_params = {}

        result = self.session.execute(text(converted_sql), dict_params)

        class CustomRow:
            def __init__(self, row):
                self._row = row
                self._mapping = row._mapping

            def __getitem__(self, key):
                if isinstance(key, int):
                    return self._row[key]
                return self._mapping[key]

            def keys(self):
                return self._mapping.keys()

            def __iter__(self):
                return iter(self._mapping.keys())

        class DBResult:
            def __init__(self, result):
                self.result = result

            def fetchone(self):
                try:
                    r = self.result.fetchone()
                    return CustomRow(r) if r else None
                except Exception:
                    return None

            def fetchall(self):
                try:
                    return [CustomRow(r) for r in self.result.fetchall()]
                except Exception:
                    return []

        return DBResult(result)

    def commit(self):
        self.session.commit()

    def close(self):
        self.session.close()


def get_db_connection():
    return DBConnectionWrapper()


def create_table():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS workers (
            name TEXT PRIMARY KEY,
            lat REAL,
            lng REAL,
            assignment TEXT,
            last_seen TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            description TEXT,
            priority TEXT,
            status TEXT DEFAULT 'Pending',
            location TEXT DEFAULT '',
            created_at TEXT,
            resolved_at TEXT,
            ai_analysis TEXT DEFAULT '',
            ai_suggestion TEXT DEFAULT '',
            official_response TEXT DEFAULT '',
            upvotes INTEGER DEFAULT 0,
            image_url TEXT DEFAULT '',
            video_url TEXT DEFAULT '',
            status_step INTEGER DEFAULT 1,
            is_emergency INTEGER DEFAULT 0,
            user_id INTEGER DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT,
            mobile TEXT,
            email TEXT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT DEFAULT 'user',
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


with app.app_context():
    create_table()


@app.context_processor
def inject_user_data():
    if 'user_id' in session:
        conn = get_db_connection()
        user = conn.execute(
            "SELECT fullname, trust_score, streak_days FROM users WHERE id=?",
            (session['user_id'],),
        ).fetchone()
        conn.close()
        if user:
            return {
                'g_fullname': user['fullname'],
                'g_trust_score': user['trust_score'],
                'g_streak_days': user['streak_days'] or 0,
            }
    return {}


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect('/login')
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Admin access required.', 'danger')
            return redirect('/login')

        if session.get('user_id') == 0 and session.get('role') == 'admin':
            return f(*args, **kwargs)

        conn = get_db_connection()
        user = conn.execute(
            "SELECT role FROM users WHERE id=?",
            (session['user_id'],),
        ).fetchone()
        conn.close()

        if not user or user['role'] != 'admin':
            flash('Admin access required.', 'danger')
            return redirect('/login')

        return f(*args, **kwargs)

    return decorated_function


# --- IMPORTANT ---
# NOTE: app_fixed.py only patches send_email_otp indentation issue.
# The rest of your app routes are intentionally omitted here.
# Use this file only to verify send_email_otp compiles.

if __name__ == "__main__":
    app.run(debug=True)

