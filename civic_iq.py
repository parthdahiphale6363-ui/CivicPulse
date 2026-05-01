from flask import Blueprint, render_template, request, jsonify, session
import os
import json
import requests
import re
from datetime import datetime

civic_iq_bp = Blueprint('civic_iq', __name__, template_folder='templates')

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def ask_groq(prompt, system_message="You are a senior civic intelligence officer in India.", temperature=0.5):
    if not GROQ_API_KEY:
        return None
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": 2048,
            "response_format": {"type": "json_object"}
        }
        res = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"CivicIQ AI Error: {e}")
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
