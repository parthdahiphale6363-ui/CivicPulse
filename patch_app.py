import re
import os

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Imports
imports_addition = """
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import logging
from logging.handlers import RotatingFileHandler
"""
code = code.replace("from email.mime.multipart import MIMEMultipart", "from email.mime.multipart import MIMEMultipart\n" + imports_addition)

# 2. Rate Limiting Setup
limiter_setup = """
# ---------------- RATE LIMITING ----------------
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per day", "200 per hour"],
    storage_uri="memory://"
)
"""
code = code.replace("app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))", "app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))\n" + limiter_setup)

# 3. Add Limiter Decorators to target routes
code = code.replace('@app.route("/report", methods=["POST"])', '@app.route("/report", methods=["POST"])\n@limiter.limit("5 per minute")')
code = code.replace('@app.route("/api/chat", methods=["POST"])', '@app.route("/api/chat", methods=["POST"])\n@limiter.limit("20 per minute")')
code = code.replace('@app.route("/api/enhance-announcement", methods=["POST"])', '@app.route("/api/enhance-announcement", methods=["POST"])\n@limiter.limit("10 per minute")')
code = code.replace('@app.route("/api/voice-report", methods=["POST"])', '@app.route("/api/voice-report", methods=["POST"])\n@limiter.limit("10 per minute")')

# 4. Error Handling
error_handling = """
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
"""
code = code.replace("app.register_blueprint(civic_iq_bp)", "app.register_blueprint(civic_iq_bp)\n" + error_handling)

# 5. CSRF Protection
csrf_setup = """
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
            html = re.sub(r'(<form[^>]*>)', rf'\\1\\n{csrf_input}', html, flags=re.IGNORECASE)
            response.set_data(html)
    return response

"""
code = code.replace("# ---------------- DATABASE CONNECTION ----------------", csrf_setup + "\n# ---------------- DATABASE CONNECTION ----------------")

# 6. Admin Access Control Fix
new_admin_required = """def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Admin access required.', 'danger')
            return redirect('/login')
            
        conn = get_db_connection()
        user = conn.execute("SELECT role FROM users WHERE id=?", (session['user_id'],)).fetchone()
        conn.close()
        
        if not user or user['role'] != 'admin':
            flash('Admin access required.', 'danger')
            return redirect('/login')
            
        return f(*args, **kwargs)
    return decorated_function"""
    
# Extract old admin_required and replace
code = re.sub(r'def admin_required\(f\):.*?return decorated_function', new_admin_required, code, flags=re.DOTALL)

# 7. Database Abstraction via SQLAlchemy Wrapper
db_abstraction = """
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
        
        class DBResult:
            def __init__(self, result):
                self.result = result
            def fetchone(self):
                try:
                    r = self.result.fetchone()
                    return r._mapping if r else None
                except Exception:
                    return None
            def fetchall(self):
                try:
                    return [r._mapping for r in self.result.fetchall()]
                except Exception:
                    return []
                    
        return DBResult(result)

    def commit(self):
        self.session.commit()

    def close(self):
        self.session.close()

def get_db_connection():
    return DBConnectionWrapper()
"""

old_db_c = """# ---------------- DATABASE CONNECTION ----------------
DB_PATH = os.path.join(DATA_DIR, "database.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn"""

code = code.replace(old_db_c, db_abstraction.strip())

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("App patched successfully!")
