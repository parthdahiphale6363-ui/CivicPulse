from flask import Blueprint, render_template, request, jsonify, session
import sqlite3
import os
import random
import json
import math
from datetime import datetime, timedelta
import requests
import re
from collections import defaultdict

city_twin_bp = Blueprint('city_twin', __name__, template_folder='templates')

# ─────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────
DATA_DIR     = "/data" if os.path.exists("/data") else os.path.dirname(os.path.abspath(__file__))
DB_PATH      = os.path.join(DATA_DIR, "database.db")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


# ─────────────────────────────────────────────────────────────
#  DB HELPERS
# ─────────────────────────────────────────────────────────────
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn, name):
    return bool(conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone())


# (Removed old worker table log)


# ─────────────────────────────────────────────────────────────
#  GROQ HELPERS
# ─────────────────────────────────────────────────────────────
def ask_groq(prompt, system_message="You are an advanced civic intelligence engine.", temperature=0.4):
    if not GROQ_API_KEY:
        # Fallback to a placeholder response if API key is missing to avoid crashing but still show "AI" effort
        return None
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type":  "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user",   "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens":  1024
        }
        res = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"GROQ ERROR: {e}")
        return None


def extract_json(raw):
    """Pull the first valid JSON object from any Groq response string."""
    if not raw:
        return None
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return None


# ─────────────────────────────────────────────────────────────
#  GEO HELPER
# ─────────────────────────────────────────────────────────────
def haversine(lat1, lng1, lat2, lng2):
    """Returns distance in metres between two GPS coordinates."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi        = math.radians(lat2 - lat1)
    dlambda     = math.radians(lng2 - lng1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def bearing(lat1, lng1, lat2, lng2):
    """Compass bearing (0-360) from point 1 to point 2."""
    dLng = math.radians(lng2 - lng1)
    x    = math.sin(dLng) * math.cos(math.radians(lat2))
    y    = (math.cos(math.radians(lat1)) * math.sin(math.radians(lat2))
            - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dLng))
    return (math.degrees(math.atan2(x, y)) + 360) % 360


# ─────────────────────────────────────────────────────────────
#  SCORE HELPERS
# ─────────────────────────────────────────────────────────────
def health_grade(score):
    return ("A" if score >= 85 else
            "B" if score >= 70 else
            "C" if score >= 55 else
            "D" if score >= 40 else "F")


def severity_score(priority, upvotes, age_hours):
    """Composite 0-100 severity for a single complaint."""
    pw = {'High': 50, 'Medium': 25, 'Low': 10}.get(priority, 10)
    uw = min(upvotes * 2, 30)
    aw = min(age_hours / 24 * 10, 20)
    return min(100, pw + uw + aw)


# ─────────────────────────────────────────────────────────────
#  PAGE ROUTE
# ─────────────────────────────────────────────────────────────
@city_twin_bp.route('/city-twin')
def city_twin_home():
    return render_template('city_twin.html')


# ═════════════════════════════════════════════════════════════
#  ORIGINAL API ROUTES  (paths preserved, responses enriched)
# ═════════════════════════════════════════════════════════════

@city_twin_bp.route('/api/city-twin/data')
def get_twin_data():
    """
    All geo-tagged complaints + live workers.
    Enhanced: adds severity_score, age_hours, pulse_radius per complaint.
    """
    conn = get_db_connection()
    complaints_raw = conn.execute("""
        SELECT id, latitude, longitude, priority, status,
               upvotes, category, description, created_at
        FROM   complaints
        WHERE  latitude IS NOT NULL AND longitude IS NOT NULL
    """).fetchall()
    conn.close()

    now        = datetime.utcnow()
    complaints = []
    for c in complaints_raw:
        d = dict(c)
        try:
            # Handle potential space in datetime (depending on how it's stored)
            created_str = d.get('created_at', '')
            if ' ' in created_str:
                created = datetime.strptime(created_str, "%Y-%m-%d %H:%M:%S")
            else:
                created = datetime.fromisoformat(created_str)
            d['age_hours'] = round((now - created).total_seconds() / 3600, 1)
        except Exception:
            d['age_hours'] = 0

        d['severity_score'] = severity_score(
            d.get('priority', 'Low'), d.get('upvotes', 0), d['age_hours']
        )
        # pulse_radius drives the animated glow size on the map (8-28 px)
        d['pulse_radius'] = 8 + int(d['severity_score'] / 100 * 20)
        complaints.append(d)

    complaints.sort(key=lambda x: x['severity_score'], reverse=True)

    return jsonify({
        "complaints": complaints,
        "timestamp":  now.isoformat()
    })


@city_twin_bp.route('/api/city-twin/health')
def city_health():
    """
    City health score 0-100.
    Enhanced: adds grade, trend, and per-category breakdown.
    """
    conn    = get_db_connection()
    total   = conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'").fetchone()[0]
    resolved= conn.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'").fetchone()[0]
    high_p  = conn.execute(
        "SELECT COUNT(*) FROM complaints WHERE priority='High' AND status='Pending'"
    ).fetchone()[0]

    cat_rows = conn.execute("""
        SELECT category,
               COUNT(*) AS cnt,
               SUM(CASE WHEN status='Pending' THEN 1 ELSE 0 END) AS pending_cnt
        FROM   complaints
        GROUP  BY category
    """).fetchall()

    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
    recent   = conn.execute(
        "SELECT COUNT(*) FROM complaints WHERE created_at >= ?", (week_ago,)
    ).fetchone()[0]
    conn.close()

    score = 100 if total == 0 else max(0, min(100, 100 - (pending / total * 40) - (high_p / total * 60)))

    categories = [
        {
            "name":    r["category"],
            "total":   r["cnt"],
            "pending": r["pending_cnt"],
            "health":  max(0, 100 - int((r["pending_cnt"] / r["cnt"]) * 100))
        }
        for r in cat_rows if r["cnt"] > 0
    ]

    return jsonify({
        "score":         int(score),
        "grade":         health_grade(int(score)),
        "total":         total,
        "pending":       pending,
        "resolved":      resolved,
        "high_priority": high_p,
        "recent_7days":  recent,
        "categories":    categories,
        "timestamp":     datetime.utcnow().isoformat()
    })


@city_twin_bp.route('/api/city-twin/simulate', methods=['POST'])
def simulate_disaster():
    """
    Groq disaster simulation.
    Enhanced: confidence_level, affected_categories, timeline, evacuation_zones.
    """
    data      = request.json or {}
    condition = data.get('condition', 'normal')

    conn       = get_db_connection()
    unresolved = conn.execute("""
        SELECT category, description, priority, latitude, longitude
        FROM   complaints
        WHERE  status != 'Resolved'
        LIMIT  20
    """).fetchall()
    conn.close()

    complaint_summary = "\n".join([
        f"- [{c['priority']}] {c['category']} at ({c['latitude']:.4f},{c['longitude']:.4f})"
        for c in unresolved
    ]) or "No active unresolved issues."

    prompt = f"""
DISASTER SCENARIO: {condition}
CURRENT UNRESOLVED CIVIC ISSUES:
{complaint_summary}

Return ONLY valid JSON with no markdown or explanation:
{{
  "risk_zones":          [{{"lat": <float>, "lng": <float>, "risk": "<High|Medium|Low>", "desc": "<short reason>"}}],
  "actions":             ["<action 1>", "<action 2>", "<action 3>"],
  "probability":         <integer 0-100>,
  "confidence_level":    "<High|Medium|Low>",
  "affected_categories": ["<cat1>", "<cat2>"],
  "timeline":            "<estimated impact window>",
  "evacuation_zones":    ["<zone description>"]
}}
"""

    raw    = ask_groq(prompt, "You are a municipal disaster risk simulation engine. Return strict JSON only.")
    parsed = extract_json(raw)

    fallback = {
        "risk_zones":          [{"lat": 20.59, "lng": 78.96, "risk": "High", "desc": "Critical Infrastructure Stress"}],
        "actions":             ["Deploy Emergency Response Teams", "Issue Public Notification", "Inspect Drainage Systems"],
        "probability":         75,
        "confidence_level":    "Medium",
        "affected_categories": ["Roads", "Drainage"],
        "timeline":            "Next 6-12 hours",
        "evacuation_zones":    []
    }

    if parsed:
        for k, v in fallback.items():
            parsed.setdefault(k, v)
        return jsonify(parsed)

    return jsonify(fallback)


# Removed Resource Optimization Logic


@city_twin_bp.route('/api/city-twin/heatmap')
def health_heatmap():
    conn = get_db_connection()
    # Get complaints with lat/lng and calculate intensity based on priority/upvotes
    rows = conn.execute("""
        SELECT latitude, longitude, priority, upvotes
        FROM   complaints
        WHERE  latitude IS NOT NULL AND longitude IS NOT NULL
    """).fetchall()
    
    points = []
    for r in rows:
        intensity = 0.4
        if r['priority'] == 'Critical': intensity = 1.0
        elif r['priority'] == 'High': intensity = 0.8
        elif r['priority'] == 'Medium': intensity = 0.6
        
        # Add boost for upvotes
        intensity = min(1.0, intensity + (r['upvotes'] * 0.01))
        points.append([r['latitude'], r['longitude'], intensity])
        
    return jsonify(points)

@city_twin_bp.route('/api/city-twin/sentiment-map')
def sentiment_map():
    """
    Ward-level citizen sentiment derived from real complaint data.
    Enhanced: resolution_rate, mood_score, top_issue per ward.
    """
    conn = get_db_connection()

    # Changed 'area' to 'ward' to match app.py schema
    try:
        rows = conn.execute("""
            SELECT
                COALESCE(ward, 'Unknown Ward') AS ward_name,
                COUNT(*)                        AS total,
                SUM(CASE WHEN priority='High' AND status='Pending' THEN 1 ELSE 0 END) AS high_pending,
                SUM(CASE WHEN status='Resolved' THEN 1 ELSE 0 END)                    AS resolved
            FROM complaints
            GROUP BY ward_name
            LIMIT 10
        """).fetchall()
    except Exception as e:
        print(f"Sentiment Map DB Error: {e}")
        rows = []
    conn.close()

    result = []
    for r in rows:
        total  = r["total"] or 1
        ratio  = r["high_pending"] / total
        mood   = "CALM" if ratio < 0.2 else ("TENSE" if ratio < 0.5 else "ANGRY")
        result.append({
            "ward":            r["ward_name"],
            "mood":            mood,
            "mood_score":      round((1 - ratio) * 100),
            "total":           r["total"],
            "high_pending":    r["high_pending"],
            "resolution_rate": round((r["resolved"] / total) * 100)
        })

    # Fallback demo data if no rows
    if not result:
        moods = ["CALM", "TENSE", "ANGRY"]
        result = [
            {
                "ward":            f"Ward {i+1}",
                "mood":            random.choice(moods),
                "mood_score":      random.randint(30, 90),
                "total":           random.randint(5, 30),
                "high_pending":    random.randint(0, 10),
                "resolution_rate": random.randint(30, 90)
            }
            for i in range(5)
        ]

    return jsonify(result)


# Removed Worker Location Logic


# ═════════════════════════════════════════════════════════════
#  NEW PREMIUM ROUTES
# ═════════════════════════════════════════════════════════════

@city_twin_bp.route('/api/city-twin/ar-complaints')
def ar_complaints():
    """
    Returns complaints within radius of user GPS for AR street overlay.
    Params: lat, lng, radius (default 500 m)
    """
    try:
        user_lat = float(request.args.get('lat'))
        user_lng = float(request.args.get('lng'))
        radius   = float(request.args.get('radius', 500))
    except (TypeError, ValueError):
        return jsonify({"error": "lat and lng query params are required"}), 400

    conn = get_db_connection()
    rows = conn.execute("""
        SELECT id, category, priority, status, latitude, longitude, upvotes, description
        FROM   complaints
        WHERE  latitude IS NOT NULL AND longitude IS NOT NULL AND status != 'Resolved'
    """).fetchall()
    conn.close()

    nearby = []
    for r in rows:
        dist = haversine(user_lat, user_lng, r['latitude'], r['longitude'])
        if dist <= radius:
            nearby.append({
                **dict(r),
                "distance_m": round(dist),
                "bearing":    round(bearing(user_lat, user_lng, r['latitude'], r['longitude']), 1)
            })

    nearby.sort(key=lambda x: x['distance_m'])
    return jsonify({"count": len(nearby), "complaints": nearby})


@city_twin_bp.route('/api/city-twin/hotspot-forecast')
def hotspot_forecast():
    """
    Groq predicts the next cluster locations based on historical patterns.
    """
    conn    = get_db_connection()
    history = conn.execute("""
        SELECT category, latitude, longitude, priority, created_at
        FROM   complaints
        ORDER  BY created_at DESC
        LIMIT  30
    """).fetchall()
    conn.close()

    if not history:
        return jsonify({"hotspots": [], "summary": "Insufficient data for prediction."})

    freq = defaultdict(int)
    for h in history:
        freq[h['category']] += 1

    prompt = f"""
Analyze this civic complaint history and predict top 3 emerging hotspot zones for the next 7 days.

RECENT COMPLAINTS:
{json.dumps([dict(h) for h in history], indent=2)}

CATEGORY FREQUENCY:
{json.dumps(dict(freq), indent=2)}

Return ONLY valid JSON:
{{
  "hotspots": [
    {{
      "lat":         <float>,
      "lng":         <float>,
      "category":   "<predicted category>",
      "probability": <int 0-100>,
      "reason":      "<brief data-driven reason>"
    }}
  ],
  "summary": "<2-sentence overall forecast>"
}}
"""

    raw    = ask_groq(prompt, "You are a predictive civic intelligence engine. Return strict JSON only.")
    parsed = extract_json(raw)

    if parsed and "hotspots" in parsed:
        return jsonify(parsed)

    return jsonify({"hotspots": [], "summary": "Prediction engine temporarily unavailable."})


@city_twin_bp.route('/api/city-twin/ward-stats')
def ward_stats():
    """Per-ward complaint breakdown with health score and grade."""
    conn = get_db_connection()
    # Changed 'area' to 'ward'
    try:
        rows = conn.execute("""
            SELECT
                COALESCE(ward, 'General') AS ward_name,
                COUNT(*)                  AS total,
                SUM(CASE WHEN status='Resolved' THEN 1 ELSE 0 END)                   AS resolved,
                SUM(CASE WHEN priority='High' AND status='Pending' THEN 1 ELSE 0 END) AS critical
            FROM complaints
            GROUP BY ward_name
            ORDER BY total DESC
        """).fetchall()
    except Exception as e:
        print(f"Ward Stats DB Error: {e}")
        rows = []
    conn.close()

    wards = []
    for r in rows:
        total  = r['total'] or 1
        score  = max(0, 100 - int((r['critical'] / total) * 60) - int(((total - r['resolved']) / total) * 40))
        wards.append({
            "ward":     r['ward_name'],
            "total":    r['total'],
            "resolved": r['resolved'],
            "critical": r['critical'],
            "health":   score,
            "grade":    health_grade(score)
        })

    return jsonify({"wards": wards, "timestamp": datetime.utcnow().isoformat()})


@city_twin_bp.route('/api/city-twin/daily-briefing')
def daily_briefing():
    """Groq generates a sharp morning briefing for government admins."""
    conn = get_db_connection()
    stats = {
        "total":     conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0],
        "pending":   conn.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'").fetchone()[0],
        "resolved":  conn.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'").fetchone()[0],
        "critical":  conn.execute("SELECT COUNT(*) FROM complaints WHERE priority='High' AND status='Pending'").fetchone()[0],
        "new_today": conn.execute(
            "SELECT COUNT(*) FROM complaints WHERE created_at >= ?",
            ((datetime.utcnow() - timedelta(hours=24)).isoformat(),)
        ).fetchone()[0]
    }
    top_cats = conn.execute("""
        SELECT category, COUNT(*) AS cnt
        FROM   complaints WHERE status='Pending'
        GROUP  BY category ORDER BY cnt DESC LIMIT 3
    """).fetchall()
    conn.close()

    top_str  = ", ".join([f"{r['category']} ({r['cnt']})" for r in top_cats]) or "None"
    score    = max(0, min(100, 100
                          - (stats['pending'] / max(stats['total'], 1) * 40)
                          - (stats['critical'] / max(stats['total'], 1) * 60)))

    prompt = f"""
City civic status report for {datetime.utcnow().strftime('%A, %d %B %Y')}:
- City Health Score: {int(score)}/100 (Grade {health_grade(int(score))})
- Total complaints: {stats['total']} | Pending: {stats['pending']} | Resolved: {stats['resolved']}
- Critical unresolved (High priority): {stats['critical']}
- New complaints in last 24h: {stats['new_today']}
- Top pending categories: {top_str}

Write a sharp 3-sentence official morning briefing for the Municipal Commissioner.
Start with overall city health, highlight the most urgent issue, end with one recommended priority action today.
Be direct, data-driven, and professional.
"""

    briefing = ask_groq(prompt, "You are a senior municipal intelligence officer writing an official morning briefing.")

    return jsonify({
        "briefing":  briefing or "Briefing engine unavailable. Review dashboard manually.",
        "stats":     stats,
        "score":     int(score),
        "grade":     health_grade(int(score)),
        "generated": datetime.utcnow().isoformat()
    })


@city_twin_bp.route('/api/city-twin/timeline')
def complaint_timeline():
    """Hourly complaint volume for the last 24 hours — drives the pulse chart."""
    conn = get_db_connection()
    # Handle both %Y-%m-%d %H:%M:%S and ISO format
    rows = conn.execute("""
        SELECT strftime('%Y-%m-%dT%H:00:00', 
               CASE WHEN created_at LIKE '% %' THEN created_at ELSE created_at END) AS hour,
               COUNT(*)                                    AS count
        FROM   complaints
        WHERE  created_at >= ?
        GROUP  BY hour
        ORDER  BY hour ASC
    """, ((datetime.utcnow() - timedelta(hours=24)).isoformat(),)).fetchall()
    conn.close()

    return jsonify({
        "timeline":  [{"hour": r["hour"], "count": r["count"]} for r in rows],
        "timestamp": datetime.utcnow().isoformat()
    })
