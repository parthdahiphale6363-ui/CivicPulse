from flask import Blueprint, render_template, request, jsonify, session
import os
import json
import requests
import re
import time
from datetime import datetime

civic_iq_bp = Blueprint('civic_iq', __name__, template_folder='templates')

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Retry config for Groq rate limits
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 2  # 2s, 4s, 8s exponential backoff

def strip_think_tags(text):
    """Strip <think>...</think> reasoning blocks that Qwen models add to responses."""
    if not text:
        return text
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    return cleaned if cleaned else text

def ask_groq(prompt, system_message="You are a senior civic intelligence officer in India.", temperature=0.5):
    if not GROQ_API_KEY:
        return None

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"}
    }

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            res = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)

            # Handle 429 rate limit with retry
            if res.status_code == 429:
                retry_after = res.headers.get("Retry-After")
                if retry_after:
                    wait = float(retry_after)
                else:
                    wait = BASE_BACKOFF_SECONDS * (2 ** attempt)
                print(f"CivicIQ: Rate limited (429). Retrying in {wait}s (attempt {attempt + 1}/{MAX_RETRIES + 1})")
                if attempt < MAX_RETRIES:
                    time.sleep(wait)
                    continue
                else:
                    res.raise_for_status()  # Final attempt — let it raise

            res.raise_for_status()
            raw = res.json()["choices"][0]["message"]["content"]
            return strip_think_tags(raw)

        except Exception as e:
            last_error = e
            # Only retry on rate limits; other errors fail immediately
            if res is not None and res.status_code == 429 and attempt < MAX_RETRIES:
                continue
            print(f"CivicIQ AI Error: {e}")
            return None

    print(f"CivicIQ AI Error: All {MAX_RETRIES + 1} attempts failed. Last error: {last_error}")
    return None

@civic_iq_bp.route('/civic-iq')
def civic_iq_home():
    return render_template('civic_iq.html')

@civic_iq_bp.route('/api/civic-iq/scan', methods=['POST'])
def scan_city():
    city = request.json.get('city', '').strip()
    if not city:
        return jsonify({"error": "City name is required"}), 400

    prompt = f"""
Generate a high-fidelity civic intelligence report for the city of {city}, India.
Analyze historical trends, urban planning challenges, and common citizen grievances for this specific city.

Return a JSON object with the following structure:
{{
  "city": "{city}",
  "health_score": <int 0-100>,
  "grade": "<A|B|C|D|F>",
  "summary": "<2-sentence sharp city overview>",
  "top_problems": [
    {{
      "issue": "<problem name>",
      "dept": "<specific Indian govt dept name, e.g., BMC, PWD, DISCOM>",
      "contact_number": "<Actual municipal helpline or local office number for this specific dept and issue in that city>",
      "legal_rights": "<brief mention of constitutional or municipal rights/acts>",
      "action_guide": "<who to call, how to escalate>",
      "rti_template": "<A complete, professional RTI application text for this specific issue into their department>"
    }},
    ... (total 5 issues)
  ],
  "escalation_matrix": [
    {{"level": "Level 1: Local", "entity": "Ward Office / Junior Engineer"}},
    {{"level": "Level 2: Zonal", "entity": "Deputy Commissioner"}},
    {{"level": "Level 3: Central", "entity": "Municipal Commissioner / Mayor"}}
  ],
  "city_directory": [
    {{"dept": "Police Control", "contact": "100"}},
    {{"dept": "Fire Brigade", "contact": "101"}},
    {{"dept": "Ambulance", "contact": "108"}},
    {{"dept": "Municipal HQ", "contact": "<official number>"}},
    {{"dept": "Women's Helpline", "contact": "1091"}},
    {{"dept": "Electricity Board", "contact": "<official number>"}}
  ]
}}
Ensure the data is realistic for {city}.
"""

    raw_res = ask_groq(prompt, "You are a professional civic consultant specializing in Indian municipal governance. Return ONLY JSON.")
    
    if not raw_res:
        # Fallback dummy data if AI fails
        return jsonify({
            "error": "AI Engine is temporarily unavailable. Local data connectivity issue.",
            "fallback": True
        })

    try:
        data = json.loads(raw_res)
        return jsonify(data)
    except:
        return jsonify({"error": "Data synthesis failed."}), 500
