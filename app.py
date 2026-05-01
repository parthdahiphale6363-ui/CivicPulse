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


from city_twin import city_twin_bp
from civic_iq import civic_iq_bp
app.register_blueprint(city_twin_bp)
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
MAIL_PORT = 587
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
            to=f"+91{target_phone}" if len(target_phone) == 10 else target_phone
        )
        return True, "Success"
    except Exception as e:
        return False, str(e)


def send_email_otp(target_email, otp_code):
    """Send a real OTP email via SMTP."""
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        return False, "Email service not configured in .env"
    
    try:
        msg = MIMEMultipart()
        msg['From'] = MAIL_USERNAME
        msg['To'] = target_email
        msg['Subject'] = f"Verification Code: {otp_code} — CivicPulse"
        
        body = f"""
        <h2>CivicPulse Verification</h2>
        <p>Your verification code is: <strong style="font-size: 24px; color: #6366f1;">{otp_code}</strong></p>
        <p>This code will expire in 10 minutes. Please enter it on the registration page to verify your account.</p>
        <br>
        <p>Team CivicPulse</p>
        """
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
        server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, "Success"
    except Exception as e:
        return False, str(e)


# ---------------- GROQ AI CONFIG ----------------
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def ask_groq(prompt, system_message="You are a helpful assistant for a local government problem reporting system. Be concise and helpful."):
    """Send a prompt to Groq AI and return the response."""
    if not GROQ_API_KEY:
        return "AI service not configured. Please set GROQ_API_KEY environment variable."
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1024
        }
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        if response.status_code != 200:
            return None
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"GROQ ERROR: {str(e)}")
        return None

def transcribe_audio(file_path):
    """Transcribe audio file using Groq's Whisper model."""
    if not GROQ_API_KEY:
        return None
    try:
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}"
        }
        with open(file_path, "rb") as f:
            files = {
                "file": (os.path.basename(file_path), f),
                "model": (None, "whisper-large-v3"),
                "response_format": (None, "json")
            }
            response = requests.post(url, headers=headers, files=files, timeout=30)
        
        if response.status_code != 200:
            print(f"TRANSCRIPTION ERROR: {response.status_code} - {response.text}")
            return None
        return response.json().get("text")
    except Exception as e:
        print(f"TRANSCRIPTION EXCEPTION: {str(e)}")
        return None

@app.route("/api/voice-report", methods=["POST"])
@limiter.limit("10 per minute")
def voice_report():
    """Handle voice complaint filing: transcribe and structure."""
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio_file = request.files['audio']
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{random.randint(1000,9999)}.webm")
    audio_file.save(temp_path)
    
    # 1. Transcribe
    transcript = transcribe_audio(temp_path)
    if os.path.exists(temp_path):
        os.remove(temp_path) # Cleanup
        
    if not transcript:
        return jsonify({"error": "Transcription failed. Please try again or type."})
        
    # 2. Structure using LLM
    prompt = f"""Transcript from citizen voice note: "{transcript}"
Analyze this and return ONLY a JSON object:
{{
  "category": "Pothole, Garbage, Water Leakage, Streetlight, Sewage, Road Damage, Traffic Signal, Noise Pollution, Illegal Dumping, or Other",
  "clean_description": "A formal, structured description based on the transcript",
  "priority": "High, Medium, or Low",
  "native_transcript": "{transcript}"
}}"""
    
    structured_raw = ask_groq(prompt, "You are a civic data structuring AI. Return only JSON.")
    if not structured_raw:
        return jsonify({"error": "AI structuring failed."})
        
    try:
        clean_json = structured_raw.strip()
        if "```json" in clean_json: clean_json = clean_json.split("```json")[1].split("```")[0]
        data = json.loads(clean_json)
        return jsonify(data)
    except:
        return jsonify({
            "category": "Other",
            "clean_description": transcript,
            "priority": "Medium",
            "native_transcript": transcript
        })

def ask_groq_vision(base64_image, prompt="Analyze this image."):
    """Send a multimodal prompt to Groq AI Vision model and return the response."""
    if not GROQ_API_KEY:
        return None
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama-3.2-11b-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.5,
            "max_tokens": 1024
        }
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        if response.status_code != 200:
            return None
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"GROQ VISION ERROR: {str(e)}")
        return None


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
            import re
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


# ---------------- CREATE TABLES ----------------
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

    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 0,
            message TEXT,
            response TEXT,
            created_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            author TEXT DEFAULT 'Admin',
            created_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id INTEGER,
            user_id INTEGER DEFAULT 0,
            rating INTEGER DEFAULT 5,
            comment TEXT DEFAULT '',
            created_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS complaint_subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id INTEGER,
            user_id INTEGER,
            created_at TEXT,
            FOREIGN KEY(complaint_id) REFERENCES complaints(id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            UNIQUE(complaint_id, user_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id INTEGER,
            user_id INTEGER,
            parent_id INTEGER DEFAULT NULL,
            content TEXT,
            created_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS issue_affected (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id INTEGER,
            user_id INTEGER,
            created_at TEXT,
            UNIQUE(complaint_id, user_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS issue_timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id INTEGER,
            status TEXT,
            notes TEXT,
            created_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS weekly_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            summary TEXT,
            created_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            badge_name TEXT,
            awarded_at TEXT,
            UNIQUE(user_id, badge_name)
        )
    """)

    # Migration: add columns if missing
    migrations = [
        ("complaints", "location", "TEXT DEFAULT ''"),
        ("complaints", "created_at", "TEXT"),
        ("complaints", "resolved_at", "TEXT"),
        ("complaints", "ai_analysis", "TEXT DEFAULT ''"),
        ("complaints", "ai_suggestion", "TEXT DEFAULT ''"),
        ("complaints", "upvotes", "INTEGER DEFAULT 0"),
        ("complaints", "image_url", "TEXT DEFAULT ''"),
        ("complaints", "video_url", "TEXT DEFAULT ''"),
        ("complaints", "status_step", "INTEGER DEFAULT 1"),
        ("complaints", "is_emergency", "INTEGER DEFAULT 0"),
        ("complaints", "user_id", "INTEGER DEFAULT 0"),
        ("complaints", "latitude", "REAL DEFAULT NULL"),
        ("complaints", "longitude", "REAL DEFAULT NULL"),
        ("complaints", "image_embedding", "BLOB DEFAULT NULL"),
        ("complaints", "department", "TEXT DEFAULT 'General'"),
        ("complaints", "estimated_resolution_time", "TEXT DEFAULT ''"),
        ("complaints", "resolution_confidence", "INTEGER DEFAULT 0"),
        ("complaints", "ward", "TEXT DEFAULT 'Ward 1'"),
        ("complaints", "is_anonymous", "INTEGER DEFAULT 0"),
        ("complaints", "affected_count", "INTEGER DEFAULT 0"),
        ("users", "role", "TEXT DEFAULT 'user'"),
        ("users", "created_at", "TEXT"),
        ("users", "trust_score", "INTEGER DEFAULT 100"),
        ("users", "streak_days", "INTEGER DEFAULT 0"),
        ("users", "last_active_date", "TEXT DEFAULT ''"),
    ]
    for table, column, col_type in migrations:
        try:
            conn.execute(f"SELECT {column} FROM {table} LIMIT 1")
        except:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

    conn.commit()
    conn.close()
with app.app_context():
    create_table()

# Inject global variables
@app.context_processor
def inject_user_data():
    if 'user_id' in session:
        conn = get_db_connection()
        user = conn.execute("SELECT fullname, trust_score, streak_days FROM users WHERE id=?", (session['user_id'],)).fetchone()
        conn.close()
        if user:
            return {'g_fullname': user['fullname'], 'g_trust_score': user['trust_score'], 'g_streak_days': user['streak_days'] or 0}
    return {}


# ---------------- AUTH DECORATOR ----------------
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
            
        # Allow hardcoded admin bypass
        if session.get('user_id') == 0 and session.get('role') == 'admin':
            return f(*args, **kwargs)
            
        conn = get_db_connection()
        user = conn.execute("SELECT role FROM users WHERE id=?", (session['user_id'],)).fetchone()
        conn.close()
        
        if not user or user['role'] != 'admin':
            flash('Admin access required.', 'danger')
            return redirect('/login')
            
        return f(*args, **kwargs)
    return decorated_function


# ---------------- PRIORITY LOGIC ----------------
def get_priority(category):
    priority_map = {
        "Pothole": "High",
        "Garbage": "Medium",
        "Water Leakage": "High",
        "Streetlight": "Medium",
        "Sewage": "High",
        "Noise Pollution": "Low",
        "Illegal Dumping": "Medium",
        "Road Damage": "High",
        "Traffic Signal": "High",
        "Other": "Low"
    }
    return priority_map.get(category, "Low")


# ---------------- CONTEXT PROCESSOR ----------------
@app.context_processor
def inject_user():
    is_logged = 'user_id' in session
    return {
        'logged_in': is_logged,
        'username': session.get('username', ''),
        'user_role': session.get('role', 'user'),
        'current_year': datetime.now().year
    }


# ================================================================
#                         ROUTES
# ================================================================

# ---------------- HOME ----------------
@app.route("/")
def home():
    conn = get_db_connection()
    total = conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    resolved = conn.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'").fetchone()[0]
    recent = conn.execute("SELECT * FROM complaints ORDER BY id DESC LIMIT 5").fetchall()

    # Announcements
    try:
        announcements = conn.execute("SELECT * FROM announcements ORDER BY id DESC LIMIT 3").fetchall()
    except:
        announcements = []

    conn.close()
    return render_template("index.html", total=total, resolved=resolved, pending=pending, recent=recent, announcements=announcements)

# ---------------- LIVE CITY PULSE ----------------
@app.route('/api/civic-news')
def get_civic_news():
    """Returns curated municipal and urban development news."""
    return jsonify([
        {"title": "Smart Cities Mission Reaches 2025 Milestone", "summary": "Over 95% of 8,000 sanctioned projects finalized. Integrated Command Centers now operational in 100 cities.", "source": "PIB India", "tag": "Policy"},
        {"title": "AMRUT 2.0: Circular Economy for Water Scaling", "summary": "New 'City Water Balance Plans' introduced to recycle treated sewage across tier-2 cities.", "source": "MoHUA", "tag": "Environment"},
        {"title": "Global Logistics Hub Breakthrough", "summary": "PM Gati Shakti National Master Plan integrates 10+ data layers for urban transport optimization.", "source": "Invest India", "tag": "Infrastructure"},
        {"title": "Industrial Smart Cities Approved", "summary": "Government greenlights 12 major hubs to boost manufacturing and regional jobs.", "source": "The Hindu", "tag": "Economy"}
    ])

@app.route("/live-pulse")
def live_pulse():
    conn = get_db_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    total_today = conn.execute("SELECT COUNT(*) FROM complaints WHERE created_at LIKE ?", (f"{today}%",)).fetchone()[0]
    total_resolved = conn.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'").fetchone()[0]
    total_pending = conn.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'").fetchone()[0]
    
    # Granular Dept Stats
    dept_stats = conn.execute("SELECT category, COUNT(*) as count FROM complaints GROUP BY category LIMIT 4").fetchall()
    
    # Radar issues
    radar_issues = conn.execute("SELECT id, category, priority, latitude, longitude FROM complaints WHERE status!='Resolved' AND latitude IS NOT NULL LIMIT 8").fetchall()
    radar_data = [dict(r) for r in radar_issues]
    conn.close()
    
    live_summary = ask_groq(f"Summary for today: {total_today} new reports. {total_resolved} resolved. Output 1 punchy civic headline.", "Live Pulse News Anchor.")
    return render_template("live_pulse.html", total_today=total_today, resolved=total_resolved, pending=total_pending, live_summary=live_summary, radar_data=radar_data, dept_stats=dept_stats)

# ---------------- REPORT ----------------

@app.route("/report")
@login_required
def report_page():
    return render_template("report.html")


@app.route("/report", methods=["POST"])
@limiter.limit("5 per minute")
@login_required
def submit_report():
    category = request.form["category"]
    description = request.form["description"]
    location = request.form.get("location", "")
    
    lat_str = request.form.get("latitude")
    lon_str = request.form.get("longitude")
    latitude = float(lat_str) if lat_str else None
    longitude = float(lon_str) if lon_str else None

    is_emergency = 1 if request.form.get("is_emergency") else 0
    is_anonymous = 1 if request.form.get("is_anonymous") else 0
    priority = "Urgent" if is_emergency else get_priority(category)
    status = "Pending"
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Handle Media Uploads
    image_url = ""
    video_url = ""
    new_embedding_bytes = None
    vision_extra_context = ""
    file = None
    file_bytes = None
    
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            file_bytes = file.read()
            
            # --- AI VISION VALIDATION ---
            import base64
            import json
            base64_img = base64.b64encode(file_bytes).decode('utf-8')
            vision_prompt = """Analyze this image in the context of a civic complaints platform.
Format your response as pure JSON like this:
{
  "is_valid": true,
  "reason": "If false, why? e.g. This is a person's selfie, unrelated meme.",
  "issue_type": "Pothole / Garbage / Leak / Unknown",
  "severity_clues": "Visible depth is approx 3 inches, spans across lane / none"
}
Return ONLY JSON."""
            
            vision_ans = ask_groq_vision(base64_img, vision_prompt)
            vision_extra_context = ""
            
            if vision_ans:
                try:
                    cleaned_ans = vision_ans.replace('```json', '').replace('```', '').strip()
                    vision_data = json.loads(cleaned_ans)
                    
                    if not vision_data.get("is_valid", True):
                        flash(f"AI Image Validation Failed: {vision_data.get('reason', 'Irrelevant image detected.')}", "danger")
                        return redirect("/report")
                        
                    vision_extra_context = f"AI Vision detected this is a {vision_data.get('issue_type', 'issue')}. Clues: {vision_data.get('severity_clues', 'None')}."
                except Exception as e:
                    print(f"Vision JSON parse error: {e}")
            # ---------------------------

    # Generate embedding before saving
    new_embedding_bytes = get_image_embedding(file_bytes) if file_bytes else None
    
    filename = f"img_{int(datetime.now().timestamp())}_{file.filename}" if file else ""
    if file_bytes:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(filepath, 'wb') as f:
            f.write(file_bytes)
        image_url = f"/static/uploads/{filename}"

    if 'video' in request.files:
        file = request.files['video']
        if file and allowed_file(file.filename):
            v_filename = f"vid_{int(datetime.now().timestamp())}_{file.filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], v_filename))
            video_url = f"/static/uploads/{v_filename}"

    # AI Analysis of the complaint (including media context)
    ai_prompt = f"""Analyze this local problem complaint. Multimedia proof was provided: {"Photo attached (" + vision_extra_context + ")" if image_url else "No photo"}, {"Video attached (15s)" if video_url else "No video"}.
Category: {category}
Description: {description}
Location: {location}

Provide:
1. Severity assessment (1-2 sentences)
2. Priority recommendation (High/Medium/Low)
3. Action plan for the department
Keep it under 150 words."""

    ai_analysis = ask_groq(ai_prompt, "You are an expert municipal problem analyst. Media visibility adds urgency.")
    ai_suggestion = ask_groq(f"Resolution steps for: {category} - {description}", "Give 2-3 actionable steps.")

    conn = get_db_connection()
    
    # --- SMART MERGE LOGIC ---
    matched_complaint_id = None
    if latitude and longitude and new_embedding_bytes:
        new_coords = (latitude, longitude)
        recent_complaints = conn.execute("SELECT id, latitude, longitude, image_embedding FROM complaints WHERE status != 'Resolved'").fetchall()
        
        for c in recent_complaints:
            if c['latitude'] and c['longitude'] and c['image_embedding']:
                existing_coords = (c['latitude'], c['longitude'])
                distance_meters = geodesic(new_coords, existing_coords).meters
                
                if distance_meters <= 50:
                    similarity = calculate_similarity(new_embedding_bytes, c['image_embedding'])
                    if similarity > 0.85:
                        matched_complaint_id = c['id']
                        break
                        
    if matched_complaint_id:
        try:
            conn.execute("INSERT INTO complaint_subscribers (complaint_id, user_id, created_at) VALUES (?, ?, ?)",
                         (matched_complaint_id, session.get('user_id', 0), created_at))
            conn.commit()
        except sqlite3.IntegrityError:
            pass # User already subscribed to this issue
            
        conn.close()
        flash('Notice: This issue is already being tracked! You have been subscribed to updates.', 'info')
        return redirect(f"/complaint/{matched_complaint_id}")
    # -------------------------

    ward = "Ward " + str(random.randint(1, 5)) # Dynamic Mock Ward assignment
    conn.execute(
        """INSERT INTO complaints (category, description, priority, status, location, created_at, ai_analysis, ai_suggestion, image_url, video_url, is_emergency, user_id, latitude, longitude, image_embedding, ward, is_anonymous) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (category, description, priority, status, location, created_at, ai_analysis, ai_suggestion, image_url, video_url, is_emergency, session.get('user_id', 0), latitude, longitude, new_embedding_bytes, ward, is_anonymous)
    )
    complaint_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    # Initialize timeline
    conn.execute(
        "INSERT INTO issue_timeline (complaint_id, status, notes, created_at) VALUES (?, ?, ?, ?)",
        (complaint_id, "Reported", "Issue was successfully reported by citizen.", created_at)
    )
    
    # Update Fix Streak
    if 'user_id' in session:
        uid = session['user_id']
        u = conn.execute("SELECT streak_days, last_active_date FROM users WHERE id=?", (uid,)).fetchone()
        if u:
            today = datetime.now().strftime("%Y-%m-%d")
            last_dt = u['last_active_date']
            curr_streak = u['streak_days'] or 0
            if last_dt:
                from datetime import datetime as dt
                try:
                    delta = (dt.strptime(today, "%Y-%m-%d") - dt.strptime(last_dt, "%Y-%m-%d")).days
                    if delta == 1: curr_streak += 1
                    elif delta > 1: curr_streak = 1
                except: curr_streak = 1
            else:
                curr_streak = 1
            if curr_streak >= 3:
                conn.execute("UPDATE users SET trust_score = trust_score + 5 WHERE id=?", (uid,))
                flash("🔥 Fix Streak active! (+5 Bonus Trust Points!)", "success")
            conn.execute("UPDATE users SET streak_days=?, last_active_date=? WHERE id=?", (curr_streak, today, uid))

    conn.commit()
    conn.close()

    flash('Complaint submitted with multimedia evidence! AI is analyzing the proof.', 'success')
    return redirect("/complaints")


@app.route("/api/analyze-draft", methods=["POST"])
def analyze_draft():
    """Smart Complaint Analyzer: Autodetect category, severity, format description, missing details."""
    data = request.get_json()
    description = data.get("description", "").strip()
    
    if not description:
        return jsonify({"error": "Please write a description first."})
        
    prompt = f"""Analyze this civic complaint draft: "{description}"
Respond with a pure JSON object containing:
{{
  "category": "Best matching category (e.g., Pothole, Garbage, Water Leakage, Streetlight, Sewage)",
  "severity_score": 5, // 1-10 integer
  "official_description": "Clean, professional public report description based on the input",
  "missing_details": "Suggestions of info to add like 'Exact street number', or 'None'"
}}
Important: Return ONLY valid JSON, no markdown formatting."""

    raw = ask_groq(prompt, "You are a specialized civic data parser. Return only JSON.")
    if not raw:
        return jsonify({"error": "AI service unavailable."})
    try:
        import json
        clean_json = raw.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json.replace("```json", "", 1)
        if clean_json.endswith("```"):
            clean_json = clean_json[::-1].replace("```"[::-1], "", 1)[::-1]
        result = json.loads(clean_json.strip())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "AI analysis failed."})

@app.route("/api/enhance-description", methods=["POST"])
def enhance_description():
    """Legacy enhancer for backward compatibility."""
    data = request.get_json()
    raw_description = data.get("description", "").strip()
    if not raw_description:
        return jsonify({"enhanced": "", "error": "Please write a description first."})
    return jsonify({"enhanced": raw_description})

@app.route("/api/enhance-location", methods=["POST"])
def enhance_location():
    """Hyper-Accurate Location Engine: Refines address and identifies landmarks."""
    data = request.get_json()
    raw_location = data.get("location", "").strip()
    
    if not raw_location:
        return jsonify({"error": "Please enter a location first."})

    prompt = f"""A citizen reported an issue at: "{raw_location}"
Refine this into a highly accurate location reading. Respond with pure JSON:
{{
  "refined_address": "Cleaned up standard string",
  "nearby_landmarks": ["List of likely landmarks or intersections nearby"],
  "confidence_score": 90 // 1-100 integer
}}
Do NOT include any markdown."""

    raw = ask_groq(prompt, "You are a geospatial analysis AI. Return only JSON.")
    if not raw:
        return jsonify({"error": "AI service unavailable."})
    try:
        import json
        clean_json = raw.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json.replace("```json", "", 1)
        if clean_json.endswith("```"):
            clean_json = clean_json[::-1].replace("```"[::-1], "", 1)[::-1]
        data = json.loads(clean_json.strip())
        # Provide fallback "enhanced" string for old templates that might rely on it
        data["enhanced"] = data.get("refined_address", "")
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": "AI location parsing failed."})

@app.route("/api/explain-simply", methods=["POST"])
def explain_simply():
    """Converts complex official jargon to simple explanations."""
    data = request.get_json()
    jargon = data.get("jargon", "").strip()
    if not jargon: return jsonify({"error": "No text provided"})
    
    prompt = f"Convert this official municipal update into very simple, easy-to-understand language:\n'{jargon}'\nKeep it to one sentence."
    simple_text = ask_groq(prompt, "You are a plain language translator for citizens.")
    return jsonify({"simple": simple_text})

@app.route("/api/predict-resolution/<int:id>")
def predict_resolution(id):
    """AI Resolution Predictor: Predicts time and department for an existing complaint."""
    conn = get_db_connection()
    complaint = conn.execute("SELECT * FROM complaints WHERE id=?", (id,)).fetchone()
    conn.close()

    if not complaint:
        return jsonify({"error": "Complaint not found."})

    if complaint['estimated_resolution_time'] and complaint['resolution_confidence']:
        return jsonify({
            "estimated_time": complaint['estimated_resolution_time'],
            "department": complaint['department'],
            "confidence": complaint['resolution_confidence']
        })

    prompt = f"""Predict the resolution for this issue:
Category: {complaint['category']}
Priority: {complaint['priority']}
Description: {complaint['description']}

Provide pure JSON object:
{{
  "estimated_time": "e.g. 48 Hours, 1 Week",
  "department": "e.g. Public Works, Sanitation, Traffic Division",
  "confidence": 85 // 1-100 integer representing prediction confidence
}}"""

    raw = ask_groq(prompt, "You are an operational prediction engine. Return only JSON.")
    if not raw:
        return jsonify({"error": "AI service unavailable."})
    import json
    try:
        clean_json = raw.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json.replace("```json", "", 1)
        if clean_json.endswith("```"):
            clean_json = clean_json[::-1].replace("```"[::-1], "", 1)[::-1]
        pred = json.loads(clean_json.strip())

        # Update DB for caching
        conn = get_db_connection()
        conn.execute(
            "UPDATE complaints SET estimated_resolution_time=?, department=?, resolution_confidence=? WHERE id=?",
            (pred.get("estimated_time", ""), pred.get("department", "General"), pred.get("confidence", 0), id)
        )
        conn.commit()
        conn.close()
        return jsonify(pred)
    except:
        return jsonify({"error": "Failed to predict resolution."})

@app.route("/api/impact-score/<int:id>")
def impact_score(id):
    """AI Impact Score: Generates 0-100 severity impact context."""
    conn = get_db_connection()
    c = conn.execute("SELECT * FROM complaints WHERE id=?", (id,)).fetchone()
    if not c:
        conn.close()
        return jsonify({"error": "Not found"})
    
    similar_count = conn.execute("SELECT COUNT(*) FROM complaints WHERE category=?", (c['category'],)).fetchone()[0]
    conn.close()

    prompt = f"""Analyze the civic impact of this issue:
Category: {c['category']}
Priority/Severity: {c['priority']}
Details/AI Review: {c['ai_analysis']}
Location Context: {c['location']}
Upvotes (community demand): {c['upvotes']}
Historical category volume: {similar_count} total

Output pure JSON exactly like this:
{{
  "score": 85, // 0-100 integer
  "badge": "Low", // Strictly one of: Low, Moderate, Critical
  "reason": "1 short line summarizing why it is critical, moderate, or low."
}}
Do NOT use markdown. Only JSON."""

    raw = ask_groq(prompt, "You are a specialized civic data analyst rating community impact. Return only JSON.")
    if not raw:
        return jsonify({"error": "AI unavailable"})
    
    try:
        import json
        clean = raw.strip()
        if clean.startswith("```json"): clean = clean.replace("```json", "", 1)
        if clean.endswith("```"): clean = clean[::-1].replace("```"[::-1], "", 1)[::-1]
        result = json.loads(clean.strip())
        
        # Fallback badge assignment if groq goes weird
        score = int(result.get('score', 50))
        if score <= 33: badge = "Low"
        elif score <= 66: badge = "Moderate"
        else: badge = "Critical"
        result['badge'] = badge
        
        return jsonify(result)
    except:
        return jsonify({"error": "Failed to parse impact score"})

@app.route("/api/nearby-duplicates", methods=["POST"])
def nearby_duplicates():
    """Find and return existing similar complaints nearby."""
    data = request.get_json()
    lat = data.get("latitude")
    lng = data.get("longitude")
    if lat is None or lng is None:
        return jsonify([])
        
    conn = get_db_connection()
    recent = conn.execute("SELECT id, category, description, location, latitude, longitude, status FROM complaints WHERE status != 'Resolved'").fetchall()
    conn.close()
    
    similar = []
    new_coords = (lat, lng)
    for c in recent:
        if c['latitude'] and c['longitude']:
            dist = geodesic(new_coords, (c['latitude'], c['longitude'])).meters
            if dist <= 200: # within 200 meters Show them to user
                similar.append({
                    "id": c['id'],
                    "category": c['category'],
                    "location": c['location'],
                    "distance_m": int(dist),
                    "status": c['status']
                })
    similar = sorted(similar, key=lambda x: x['distance_m'])[:3]
    return jsonify(similar)


# ---------------- COMPLAINTS ----------------

@app.route("/complaints")
def complaints():
    conn = get_db_connection()
    status_filter = request.args.get('status', 'all')
    category_filter = request.args.get('category', 'all')
    search_query = request.args.get('search', '').strip()

    query = "SELECT * FROM complaints"
    conditions = []
    params = []

    if status_filter != 'all':
        conditions.append("status = ?")
        params.append(status_filter)
    if category_filter != 'all':
        conditions.append("category = ?")
        params.append(category_filter)
    if search_query:
        conditions.append("(description LIKE ? OR location LIKE ? OR category LIKE ?)")
        params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY id DESC"
    data = conn.execute(query, params).fetchall()
    conn.close()

    return render_template("complaints.html", complaints=data,
                           status_filter=status_filter,
                           category_filter=category_filter,
                           search_query=search_query)


# Resolve Complaint
@app.route("/resolve/<int:id>")
@admin_required
def resolve(id):
    resolved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    conn.execute("UPDATE complaints SET status='Resolved', resolved_at=? WHERE id=?", (resolved_at, id))
    conn.commit()
    conn.close()
    flash('Complaint marked as resolved!', 'success')
    return redirect("/complaints")


# Upvote complaint (Modifies trust score too)
@app.route("/upvote/<int:id>")
def upvote(id):
    conn = get_db_connection()
    conn.execute("UPDATE complaints SET upvotes = upvotes + 1 WHERE id=?", (id,))
    
    # Increase trust score for author
    complaint = conn.execute("SELECT user_id FROM complaints WHERE id=?", (id,)).fetchone()
    if complaint and complaint['user_id']:
        conn.execute("UPDATE users SET trust_score = trust_score + 2 WHERE id=?", (complaint['user_id'],))
        
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# Delete complaint
@app.route("/delete/<int:id>")
@admin_required
def delete_complaint(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM complaints WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash('Complaint deleted.', 'info')
    return redirect("/complaints")


# View single complaint
@app.route("/complaint/<int:id>")
def view_complaint(id):
    conn = get_db_connection()
    complaint = conn.execute("SELECT c.*, u.fullname, u.username, u.trust_score FROM complaints c LEFT JOIN users u ON c.user_id = u.id WHERE c.id=?", (id,)).fetchone()

    # Get feedback for this complaint
    try:
        feedbacks = conn.execute("SELECT * FROM feedback WHERE complaint_id=? ORDER BY id DESC", (id,)).fetchall()
    except:
        feedbacks = []

    # Get comments
    try:
        comments = conn.execute("""
            SELECT c.*, u.fullname, u.username, u.trust_score 
            FROM comments c 
            JOIN users u ON c.user_id = u.id 
            WHERE c.complaint_id=? ORDER BY c.created_at ASC
        """, (id,)).fetchall()
    except:
        comments = []

    # Get timeline
    try:
        timeline = conn.execute("SELECT * FROM issue_timeline WHERE complaint_id=? ORDER BY created_at ASC", (id,)).fetchall()
    except:
        timeline = []

    conn.close()
    if not complaint:
        flash('Complaint not found.', 'danger')
        return redirect("/complaints")
    return render_template("complaint_detail.html", complaint=complaint, feedbacks=feedbacks, comments=comments, timeline=timeline)

# ======== NEW COMMUNITY BOARD ROUTES ========
@app.route("/api/complaint/<int:id>/comment", methods=["POST"])
@login_required
def add_comment(id):
    content = request.form.get("content", "").strip()
    if not content:
        flash("Comment cannot be empty.", "warning")
        return redirect(f"/complaint/{id}")
    
    # Store comment
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    conn.execute("INSERT INTO comments (complaint_id, user_id, content, created_at) VALUES (?, ?, ?, ?)",
                 (id, session['user_id'], content, created_at))
    conn.commit()
    conn.close()
    flash("Comment added successfully!", "success")
    return redirect(f"/complaint/{id}")

@app.route("/api/complaint/<int:id>/affected", methods=["POST"])
@login_required
def affected_too(id):
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO issue_affected (complaint_id, user_id, created_at) VALUES (?, ?, ?)",
                     (id, session['user_id'], created_at))
        conn.execute("UPDATE complaints SET affected_count = affected_count + 1 WHERE id=?", (id,))
        conn.commit()
        success = True
        msg = "You've marked this issue as affecting you."
    except sqlite3.IntegrityError:
        success = False
        msg = "You already marked this issue."
    conn.close()
    
    return jsonify({"success": success, "message": msg})

@app.route("/admin/timeline/<int:id>", methods=["POST"])
@admin_required
def update_timeline(id):
    status = request.form.get("status", "In Progress")
    notes = request.form.get("notes", "Status updated by admin.").strip()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_db_connection()
    # Insert new timeline stage
    conn.execute("INSERT INTO issue_timeline (complaint_id, status, notes, created_at) VALUES (?, ?, ?, ?)",
                 (id, status, notes, created_at))
    # Update main issue status
    conn.execute("UPDATE complaints SET status=? WHERE id=?", (status, id))
    conn.commit()
    conn.close()
    
    flash("Timeline updated!", "success")
    return redirect(f"/complaint/{id}")

@app.route("/api/complaint/<int:id>/subscribe", methods=["POST"])
@login_required
def subscribe_notify(id):
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO complaint_subscribers (complaint_id, user_id, created_at) VALUES (?, ?, ?)",
                     (id, session['user_id'], created_at))
        conn.commit()
        success = True
        msg = "You are now subscribed. We'll notify you on status changes."
    except sqlite3.IntegrityError:
        success = False
        msg = "You are already subscribed to this issue."
    conn.close()
    return jsonify({"success": success, "message": msg})


# ======== REAL AUTH: OTP API ========

@app.route("/api/send-otp", methods=["POST"])
def send_otp():
    """Generate and send a REAL 6-digit OTP to the user's email."""
    data = request.get_json()
    target = data.get("email", "").strip()
    
    if not target or "@gmail.com" not in target:
        return jsonify({"success": False, "message": "Valid Gmail address required."})
    
    # Generate 6-digit OTP
    otp = ''.join(random.choices(string.digits, k=6))
    
    # Store in session (temp)
    session['signup_otp'] = otp
    session['otp_email'] = target
    
    success, error_msg = send_email_otp(target, otp)
    
    if success:
        return jsonify({"success": True, "message": "OTP sent successfully!"})
    else:
        # Fallback for development if keys are missing
        print(f"DEBUG: OTP for {target} is {otp}. Error: {error_msg}")
        return jsonify({"success": False, "message": f"Service error. Check .env if you used real keys. (Dev OTP: {otp})"})


@app.route("/api/send-sms", methods=["POST"])
def send_sms_api():
    """Generate and send a REAL SMS OTP via Twilio."""
    data = request.get_json()
    target = data.get("mobile", "").strip()
    
    if not target or len(target) < 10:
        return jsonify({"success": False, "message": "Valid mobile number required."})
    
    otp = ''.join(random.choices(string.digits, k=6))
    session['mobile_otp'] = otp
    
    success, error_msg = send_sms_otp(target, otp)
    
    if success:
        return jsonify({"success": True, "message": "SMS sent successfully!"})
    else:
        print(f"DEBUG SMS: OTP for {target} is {otp}. Error: {error_msg}")
        return jsonify({"success": False, "message": f"SMS Service Error: {error_msg}. (Dev OTP: {otp})"})


@app.route("/api/verify-otp", methods=["POST"])
def verify_otp_api():
    """Verify the OTP entered by the user."""
    data = request.get_json()
    user_otp = data.get("otp", "").strip()
    v_type = data.get("type", "email")
    
    if v_type == 'mobile':
        if 'mobile_otp' in session and session['mobile_otp'] == user_otp:
            session['mobile_verified'] = True
            return jsonify({"success": True})
    else:
        if 'signup_otp' in session and session['signup_otp'] == user_otp:
            session['email_verified'] = True
            return jsonify({"success": True})
            
    return jsonify({"success": False, "message": "Invalid verification code."})


# ======== ADMIN: OFFICIAL RESPONSE ========
@app.route("/admin/respond/<int:id>", methods=["POST"])
@admin_required
def admin_respond(id):
    response_text = request.form.get("official_response", "").strip()
    if not response_text:
        flash("Response cannot be empty.", "warning")
        return redirect(f"/complaint/{id}")
    
    conn = get_db_connection()
    conn.execute("UPDATE complaints SET official_response=? WHERE id=?", (response_text, id))
    conn.commit()
    conn.close()
    
    flash("Official response updated!", "success")
    return redirect(f"/complaint/{id}")


@app.route("/api/draft-response", methods=["POST"])
@admin_required
def draft_response():
    """Generates a formal municipal response based on admin shorthand notes."""
    data = request.get_json()
    notes = data.get("notes", "").strip()
    complaint_id = data.get("complaint_id")

    if not notes or not complaint_id:
        return jsonify({"draft": "", "error": "Notes and complaint ID are required."})
        
    conn = get_db_connection()
    complaint = conn.execute("SELECT * FROM complaints WHERE id=?", (complaint_id,)).fetchone()
    conn.close()
    
    if not complaint:
        return jsonify({"draft": "", "error": "Complaint not found."})

    prompt = f"""You are drafting an official public response from a Municipal Authority regarding a citizen's complaint.
Complaint Category: {complaint['category']}
Complaint Description: {complaint['description']}
Location: {complaint['location']}

The administrator has provided these informal notes on the resolution or status: "{notes}"

Draft a professional, empathetic, and formal official response to the citizen (maximum 3-4 sentences). The response should clearly state what action was taken based on the notes. Do NOT include placeholders like [Your Name] or [Department Name]. Just the response body."""

    draft = ask_groq(prompt, "You are a professional municipal communications officer.")
    if not draft:
        return jsonify({"draft": "", "error": "AI service temporarily unavailable."}), 503
        
    return jsonify({"draft": draft})


# ======== AI CIVIC ACTION CAMPAIGN BUILDER (FOR USERS) ========
@app.route("/api/generate-campaign/<int:id>")
def generate_campaign(id):
    """Generates a social media and community action kit for citizens to amplify an issue."""
    conn = get_db_connection()
    complaint = conn.execute("SELECT * FROM complaints WHERE id=?", (id,)).fetchone()
    conn.close()

    if not complaint:
        return jsonify({"error": "Complaint not found."})

    link = f"http://127.0.0.1:5000/complaint/{id}"
    
    prompt = f"""You are a community organizing AI assistant helping a citizen amplify a civic issue.
The issue details are as follows:
Category: {complaint['category']}
Description: {complaint['description']}
Location: {complaint['location']}
Priority: {complaint['priority']}

Generate a "Civic Action Kit" in JSON format (pure JSON, no markdown blocks, no triple backticks). Use this exact structure:
{{
  "whatsapp": "A compelling message to forward to neighborhood WhatsApp groups to ask them to upvote the issue. Include the link {link}.",
  "twitter": "A short, impactful tweet (<280 chars) to tag local authorities about the delay, including relevant hashtags and the link {link}.",
  "email": "A professional 3-sentence email template to send to the local Ward Councilor requesting immediate intervention."
}}
Keep all text highly professional, action-oriented, and realistic."""

    raw_response = ask_groq(prompt, "You are a community organizer. Always return ONLY valid JSON.")
    if not raw_response:
        return jsonify({"error": "AI service down."}), 503
        
    try:
        # Try to parse the JSON returned by Groq, handling potential markdown wrappings
        import json
        clean_json = raw_response.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json.replace("```json", "", 1)
        if clean_json.endswith("```"):
            clean_json = clean_json[::-1].replace("```"[::-1], "", 1)[::-1]
            
        kit_data = json.loads(clean_json.strip())
        return jsonify(kit_data)
    except Exception as e:
        print(f"Error parsing JSON from Groq: {e}\nRaw Response: {raw_response}")
        return jsonify({"error": "Failed to generate campaign. Please try again."})


# ======== EXPORT COMPLAINTS AS CSV ========
@app.route("/export/csv")
@admin_required
def export_csv():
    conn = get_db_connection()
    complaints = conn.execute("SELECT * FROM complaints ORDER BY id DESC").fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Category', 'Description', 'Priority', 'Status', 'Location', 'Created At', 'Resolved At', 'Upvotes'])

    for c in complaints:
        writer.writerow([
            c['id'], c['category'], c['description'], c['priority'],
            c['status'], c['location'] or '', c['created_at'] or '',
            c['resolved_at'] or '', c['upvotes'] or 0
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment;filename=complaints_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


# ======== FEEDBACK ON COMPLAINTS ========
@app.route("/feedback/<int:complaint_id>", methods=["POST"])
@login_required
def submit_feedback(complaint_id):
    rating = int(request.form.get("rating", 5))
    comment = request.form.get("comment", "").strip()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO feedback (complaint_id, user_id, rating, comment, created_at) VALUES (?, ?, ?, ?, ?)",
        (complaint_id, session.get('user_id', 0), rating, comment, created_at)
    )
    conn.commit()
    conn.close()

    flash('Thank you for your feedback!', 'success')
    return redirect(f"/complaint/{complaint_id}")


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
@admin_required
def dashboard():
    conn = get_db_connection()

    total = conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    high = conn.execute("SELECT COUNT(*) FROM complaints WHERE priority='High'").fetchone()[0]
    medium = conn.execute("SELECT COUNT(*) FROM complaints WHERE priority='Medium'").fetchone()[0]
    low = conn.execute("SELECT COUNT(*) FROM complaints WHERE priority='Low'").fetchone()[0]
    resolved = conn.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'").fetchone()[0]
    users_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    categories = conn.execute("""
        SELECT category, COUNT(*) as count FROM complaints GROUP BY category ORDER BY count DESC
    """).fetchall()

    recent = conn.execute("SELECT * FROM complaints ORDER BY id DESC LIMIT 10").fetchall()

    # Announcements
    try:
        announcements = conn.execute("SELECT * FROM announcements ORDER BY id DESC").fetchall()
    except:
        announcements = []

    conn.close()

    return render_template(
        "dashboard.html",
        total=total, high=high, medium=medium, low=low,
        resolved=resolved, pending=pending, users_count=users_count,
        categories=categories, recent=recent, announcements=announcements
    )


# Dashboard AI Summary (Public)
@app.route("/api/dashboard-summary")
def dashboard_summary():
    conn = get_db_connection()
    total = conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    high = conn.execute("SELECT COUNT(*) FROM complaints WHERE priority='High'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'").fetchone()[0]
    resolved = conn.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'").fetchone()[0]

    categories = conn.execute("""
        SELECT category, COUNT(*) as count FROM complaints GROUP BY category ORDER BY count DESC
    """).fetchall()
    cat_text = ", ".join([f"{c['category']}: {c['count']}" for c in categories])

    conn.close()

    prompt = f"""Analyze these municipal complaint statistics and provide insights:
- Total complaints: {total}
- High priority: {high}
- Pending: {pending}
- Resolved: {resolved}
- Category breakdown: {cat_text}

Provide:
1. A brief overall assessment (2-3 sentences)
2. Key areas of concern
3. Recommendations for improvement
Keep it under 200 words. Use bullet points."""

    summary = ask_groq(prompt, "You are a municipal data analyst. Provide actionable insights.")
    return jsonify({"summary": summary})

@app.route('/admin/dept-insight/<category>')
def dept_insight(category):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    conn = get_db_connection()
    complaints = conn.execute("SELECT description, priority, status FROM complaints WHERE category=? AND status='Pending' LIMIT 10", (category,)).fetchall()
    conn.close()
    
    if not complaints:
        return jsonify({"insight": "No pending complaints found for this department."})
    
    # Pre-process descriptions for prompt
    data_summary = "\n".join([f"- Priority: {c['priority']}, Desc: {c['description']}" for c in complaints])
    
    prompt = f"""
    You are a Senior Municipal Planning Expert. Analyzing the latest PENDING complaints for the '{category}' department:
    {data_summary}
    
    Provide a professional, actionable 3-point summary for the government staff:
    1. Major Trending Issue: What is the biggest concern?
    2. Recommended Staff Action: What step should be taken first?
    3. Community Impact: How does this affect citizens?
    
    Keep it professional, concise, and structured.
    """
    
    insight = ask_groq(prompt, system_message="Official Government Strategic Advisor. Focus on efficiency and citizen satisfaction.")
    return jsonify({"insight": insight})

@app.route('/admin/generate-weekly-report')
def generate_weekly_report():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    conn = get_db_connection()
    # Get stats per ward
    ward_stats = conn.execute("""
        SELECT ward, COUNT(*) as total, 
        SUM(CASE WHEN status='Resolved' THEN 1 ELSE 0 END) as resolved,
        SUM(CASE WHEN status='Pending' THEN 1 ELSE 0 END) as pending
        FROM complaints GROUP BY ward
    """).fetchall()
    
    top_categories = conn.execute("""
        SELECT category, COUNT(*) as count FROM complaints GROUP BY category ORDER BY count DESC LIMIT 3
    """).fetchall()
    conn.close()
    
    stats_summary = "\n".join([f"Ward: {w['ward']}, Total: {w['total']}, Fixed: {w['resolved']}, Pending: {w['pending']}" for w in ward_stats])
    cats_summary = ", ".join([f"{c['category']} ({c['count']})" for c in top_categories])
    
    prompt = f"""
    You are a Municipal Commissioner's Executive Assistant. Generate a FORMAL weekly performance report based on this data:
    
    WEEKLY DATA:
    {stats_summary}
    
    TOP ISSUES:
    {cats_summary}
    
    Provide the report in these sections:
    1. Executive Overview (Professional summary)
    2. Ward Performance Table (Mock up a textual table)
    3. Primary Bottlenecks (Analyze why issues are pending)
    4. Strategic Recommendations for Next Week
    
    Keep the tone extremely professional and suitable for a City Council meeting.
    """
    
    report = ask_groq(prompt, system_message="Formal Municipal Reporting AI. Use institutional and administrative tone.")
    return jsonify({"report": report})

@app.route('/admin/dashboard')
def admin_dashboard():
    conn = get_db_connection()
    complaints = conn.execute("SELECT id, category, latitude, longitude, priority, status FROM complaints WHERE latitude IS NOT NULL").fetchall()
    conn.close()
    data = []
    for c in complaints:
        data.append({
            "id": c["id"],
            "category": c["category"],
            "lat": c["latitude"],
            "lng": c["longitude"],
            "priority": c["priority"],
            "status": c["status"]
        })
    return jsonify(data)

@app.route("/api/map-data")
def map_data():
    conn = get_db_connection()
    complaints = conn.execute("SELECT id, category, latitude, longitude, priority, status FROM complaints WHERE latitude IS NOT NULL").fetchall()
    conn.close()
    data = []
    for c in complaints:
        data.append({
            "id": c["id"],
            "category": c["category"],
            "lat": c["latitude"],
            "lng": c["longitude"],
            "priority": c["priority"],
            "status": c["status"]
        })
    return jsonify(data)


# ======== ANNOUNCEMENTS (Admin) ========
@app.route("/api/enhance-announcement", methods=["POST"])
@limiter.limit("10 per minute")
@admin_required
def api_enhance_announcement():
    data = request.get_json()
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    
    if not title and not content:
        return jsonify({"error": "Please provide title or content to enhance."})
        
    prompt = f"""Enhance this municipal announcement to be more professional, clear, and engaging for citizens:
Title: {title}
Content: {content}

Return pure JSON object:
{{
  "title": "Enhanced professional title",
  "content": "Enhanced professional and clear content"
}}"""

    raw = ask_groq(prompt, "You are a municipal communications expert. Return only JSON.")
    if not raw:
        return jsonify({"error": "AI service unavailable."})
    try:
        import json
        clean_json = raw.strip()
        if clean_json.startswith("```json"): clean_json = clean_json.replace("```json", "", 1)
        if clean_json.endswith("```"): clean_json = clean_json[::-1].replace("```"[::-1], "", 1)[::-1]
        result = json.loads(clean_json.strip())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "AI enhancement failed."})

@app.route("/announcement", methods=["POST"])
@admin_required
def create_announcement():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    if not title or not content:
        flash("Title and content are required.", "danger")
        return redirect("/dashboard")

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO announcements (title, content, author, created_at) VALUES (?, ?, ?, ?)",
        (title, content, session.get('username', 'Admin'), created_at)
    )
    conn.commit()
    conn.close()
    flash("Announcement published!", "success")
    return redirect("/dashboard")


@app.route("/announcement/delete/<int:id>")
@admin_required
def delete_announcement(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM announcements WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Announcement deleted.", "info")
    return redirect("/dashboard")


# ======== COMMUNITY PAGE ========
@app.route("/community")
def community():
    conn = get_db_connection()
    try:
        announcements = conn.execute("SELECT * FROM announcements ORDER BY id DESC").fetchall()
    except:
        announcements = []

    # Get Weekly Summary
    try:
        latest_summary = conn.execute("SELECT * FROM weekly_summaries ORDER BY id DESC LIMIT 1").fetchone()
    except:
        latest_summary = None

    # Top upvoted complaints
    top_complaints = conn.execute(
        "SELECT c.*, (SELECT COUNT(*) FROM comments WHERE complaint_id = c.id) as comment_count FROM complaints c ORDER BY c.upvotes DESC LIMIT 10"
    ).fetchall()

    # Resolved Issue Celebration Feed
    resolved_feed = conn.execute("""
        SELECT c.*, u.fullname,
               (julianday(c.resolved_at) - julianday(c.created_at)) as resolution_days
        FROM complaints c
        LEFT JOIN users u ON c.user_id = u.id
        WHERE c.status='Resolved'
        ORDER BY c.resolved_at DESC LIMIT 5
    """).fetchall()

    # Department Response Leaderboard
    dept_leaderboard = conn.execute("""
        SELECT department, COUNT(*) as resolved_count, 
               AVG(julianday(resolved_at) - julianday(created_at)) as avg_days
        FROM complaints 
        WHERE status='Resolved' AND department != 'General'
        GROUP BY department
        ORDER BY avg_days ASC
        LIMIT 5
    """).fetchall()

    conn.close()
    return render_template("community.html", 
                           announcements=announcements, 
                           top_complaints=top_complaints,
                           latest_summary=latest_summary,
                           resolved_feed=resolved_feed,
                           dept_leaderboard=dept_leaderboard)

@app.route("/admin/generate-weekly-summary", methods=["POST"])
@admin_required
def generate_weekly_summary():
    conn = get_db_connection()
    # fetch top complaints from last 7 days
    recent = conn.execute("SELECT category, description, upvotes FROM complaints ORDER BY upvotes DESC LIMIT 5").fetchall()
    conn.close()
    
    if not recent:
        flash("No recent complaints to summarize.", "info")
        return redirect("/dashboard")

    issues_text = "\\n".join([f"- {c['category']} ({c['upvotes']} upvotes): {c['description']}" for c in recent])
    
    prompt = f"""You are CivicAI summarizing the community's week.
Here are the top trending citizen issues:
{issues_text}

Draft ONE concise, professional, and encouraging paragraph summarizing the key concerns for this week. No markdown formatting, just pure text."""

    summary = ask_groq(prompt, "You are a public relations AI for a city.")
    if summary:
        conn = get_db_connection()
        conn.execute("INSERT INTO weekly_summaries (summary, created_at) VALUES (?, ?)", 
                     (summary, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        flash("Weekly summary generated!", "success")
    else:
        flash("Failed to generate summary via AI.", "danger")
    
    return redirect("/dashboard")


# ---------------- AI CHAT ----------------

@app.route("/ai-chat")
def ai_chat_page():
    return render_template("ai_chat.html")


@app.route("/api/chat", methods=["POST"])
@limiter.limit("20 per minute")
def ai_chat():
    data = request.get_json()
    user_message = data.get("message", "")

    if not user_message.strip():
        return jsonify({"response": "Please type a message."})

    system_msg = """You are CivicAI, an intelligent assistant for the Smart Local Problem Reporting System. 

CRITICAL INSTRUCTIONS:
1. If a user describes an issue they want to report, immediately suggest the BEST category from this list: Pothole, Garbage, Water Leakage, Streetlight, Sewage, Road Damage, Traffic Signal, Noise Pollution, Illegal Dumping. 
2. Also tell them their expected priority level (High/Medium/Low).
3. Provide them a direct link to report it like this: [Click here to Report](/report)
4. Answer general questions about municipal services, procedures, and community improvement.

Be friendly, helpful, and concise. Use emojis occasionally.
If someone asks something unrelated, politely redirect them.
Keep responses under 150 words."""

    response = ask_groq(user_message, system_msg)

    # Save chat history
    try:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO chat_history (user_id, message, response, created_at) VALUES (?, ?, ?, ?)",
            (session.get('user_id', 0), user_message, response, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()
    except:
        pass

    return jsonify({"response": response})


# AI Analyze a specific complaint
@app.route("/api/analyze/<int:id>")
def ai_analyze(id):
    conn = get_db_connection()
    complaint = conn.execute("SELECT * FROM complaints WHERE id=?", (id,)).fetchone()
    conn.close()

    if not complaint:
        return jsonify({"analysis": "Complaint not found."})

    prompt = f"""Provide a detailed analysis of this municipal complaint:
Category: {complaint['category']}
Description: {complaint['description']}
Current Priority: {complaint['priority']}
Status: {complaint['status']}
Location: {complaint['location'] or 'Not specified'}

Provide:
1. Risk assessment
2. Impact on citizens
3. Recommended priority adjustment (if any)
4. Step-by-step resolution plan
5. Preventive measures

Keep it under 250 words."""

    analysis = ask_groq(prompt, "You are an expert municipal problem analyst.")
    return jsonify({"analysis": analysis})


# ---------------- USER REGISTER ----------------

@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/register", methods=["POST"])
def register():
    fullname = request.form["fullname"]
    mobile = request.form["mobile"]
    email = request.form["email"]
    username = request.form["username"]
    password = request.form["password"]
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Validate Gmail Format
    if not email.endswith("@gmail.com"):
        flash("Only @gmail.com addresses are accepted for verification.", "danger")
        return redirect("/register")
    
    if not re.match(r"^[a-zA-Z0-9._%+-]+@gmail\.com$", email):
        flash("Invalid Gmail address format.", "danger")
        return redirect("/register")

    # 2. Validate Phone Format (10 digits starting with 6-9)
    if not re.match(r"^[6-9]\d{9}$", mobile):
        flash("Invalid Mobile Number. Please enter a valid 10-digit number.", "danger")
        return redirect("/register")

    # 3. Hash the password for security
    hashed_password = generate_password_hash(password)

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO users (fullname, mobile, email, username, password, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (fullname, mobile, email, username, hashed_password, 'user', created_at)
        )
        conn.commit()
        flash('Registration successful! Please login.', 'success')
    except sqlite3.IntegrityError:
        flash('Username already exists. Please choose a different one.', 'danger')
        conn.close()
        return redirect("/register")

    conn.close()
    return redirect("/login")


# ---------------- USER LOGIN ----------------

@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]

    # Admin login
    if username == "admin" and password == "admin123":
        session['user_id'] = 0
        session['username'] = 'Admin'
        session['role'] = 'admin'
        flash('Welcome back, Admin!', 'success')
        return redirect("/dashboard")

    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username=?",
        (username,)
    ).fetchone()
    conn.close()

    if user and check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['username'] = user['fullname']
        session['role'] = user['role'] or 'user'
        flash(f'Welcome back, {user["fullname"]}!', 'success')
        return redirect("/")
    else:
        flash('Invalid username or password.', 'danger')
        return redirect("/login")


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect("/")


# ---------------- PROFILE ----------------

@app.route("/profile")
@login_required
def profile():
    conn = get_db_connection()
    user_complaints = conn.execute(
        "SELECT * FROM complaints WHERE user_id=? ORDER BY id DESC", (session['user_id'],)
    ).fetchall()

    total_filed = len(user_complaints)
    total_resolved = sum(1 for c in user_complaints if c['status'] == 'Resolved')
    total_pending = total_filed - total_resolved

    conn.close()
    return render_template("profile.html", user_complaints=user_complaints,
                         total_filed=total_filed, total_resolved=total_resolved, total_pending=total_pending)


# ---------------- API ENDPOINTS ----------------

@app.route("/api/stats")
def api_stats():
    conn = get_db_connection()
    total = conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    resolved = conn.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'").fetchone()[0]
    high = conn.execute("SELECT COUNT(*) FROM complaints WHERE priority='High'").fetchone()[0]
    medium = conn.execute("SELECT COUNT(*) FROM complaints WHERE priority='Medium'").fetchone()[0]
    low = conn.execute("SELECT COUNT(*) FROM complaints WHERE priority='Low'").fetchone()[0]

    categories = conn.execute("""
        SELECT category, COUNT(*) as count FROM complaints GROUP BY category
    """).fetchall()

    conn.close()

    return jsonify({
        "total": total, "resolved": resolved, "pending": pending,
        "high": high, "medium": medium, "low": low,
        "categories": [{"name": c["category"], "count": c["count"]} for c in categories]
    })


# ======== ADMIN: MANAGE USERS ========
@app.route("/admin/users")
@admin_required
def admin_users():
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin_users.html", users=users)


@app.route("/admin/user/delete/<int:id>")
@admin_required
def admin_delete_user(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("User deleted.", "info")
    return redirect("/admin/users")


@app.route('/favicon.ico')
def favicon():
    return '', 204

# --- NEW AMAZING AI FEATURES ---
@app.route('/api/ripple-effect/<int:id>')
def api_ripple_effect(id):
    complaint = query_db('SELECT * FROM complaints WHERE id = ?', [id], one=True)
    if not complaint:
        return jsonify({'error': 'Complaint not found'})
    
    prompt = f"""
    Analyze this civic issue: {complaint['category']} - {complaint['description']}.
    What are the cascading 'ripple effects' if this is ignored for a week? 
    Give exactly 3 short points. Start Point 1 with 'Immediate:', Point 2 with 'Secondary:', Point 3 with 'Long-Term:'. Keep it brief and severely impactful.
    """
    
    try:
        response = call_groq_llama(prompt)
        lines = [line.strip() for line in response.split('\n') if line.strip() and (line.startswith('Immediate') or line.startswith('Secondary') or line.startswith('Long-Term') or line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or line.startswith('-'))]
        if not lines:
            lines = [response]
        return jsonify({'success': True, 'effects': lines})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/resource-matrix/<int:id>')
def api_resource_matrix(id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    complaint = query_db('SELECT * FROM complaints WHERE id = ?', [id], one=True)
    if not complaint:
        return jsonify({'error': 'Complaint not found'})
        
    prompt = f"""
    Act as a Municipal Operations AI.
    Analyze this repair job: {complaint['category']} - {complaint['description']}.
    Provide a highly realistic 'Resource & Budget Matrix' in exactly these 3 lines:
    1. Crew Required: [workers]
    2. Equipment: [tools]
    3. Estimated Cost: [$X, short reason]
    """
    
    try:
        response = call_groq_llama(prompt)
        return jsonify({'success': True, 'matrix': response})
    except Exception as e:
        return jsonify({'error': str(e)})

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)