# CivicPulse 🏙️ - Smart Local Problem Reporting System

## Overview
CivicPulse is an AI-powered, modern civic engagement platform designed to bridge the gap between citizens and municipal authorities. It empowers users to seamlessly report local issues (such as potholes, water leakages, garbage, and streetlights) and provides administrators with a highly intelligent dashboard to triage, track, and resolve these complaints with maximum efficiency. 

By integrating the ultra-fast Groq LLM API, CivicPulse brings cutting-edge artificial intelligence right to the local neighborhood, making the reporting process intuitive, deduplicated, and predictive.

## 🚀 Key Features

### For Citizens:
1. **AI-Powered Smart Complaint Analyzer**: As users write a draft of their issue, the AI instantly detects the best category, assigns an objective severity score, restructures the complaint into formal official language, and suggests missing details before submission.
2. **Hyper-Accurate Location Engine**: Uses GPS and AI refining to turn messy locations ("near the big tree on Main St") into refined addresses with detected cross-streets, nearby landmarks, and an AI confidence score.
3. **Multimedia Evidence & Image Validation**: Supports image and video uploads (max 15s limit for efficiency). Uses Groq Vision models to automatically analyze photos, verify they are actual civic issues, and instantly reject irrelevant memes/selfies while extracting severity clues.
4. **Duplicate Detection System & Smart Merge**: Spatially queries locations within 200m to intercept duplicates. It suggests upvoting an existing issue instead to aggregate community demand rather than spamming municipal inboxes.
5. **CivicAI Chatbot**: A contextual 24/7 Groq-powered assistant that guides citizens on how to report issues, explains municipal laws, and links directly to relevant modules.
6. **AI Resolution Predictor**: When viewing an issue, AI predicts the *Estimated Time of Resolution* and the *Responsible Municipal Department* so citizens have completely transparent expectations.
7. **Civic Impact Score**: Every single complaint is dynamically parsed utilizing real-time parameters (historical category volumes, community upvotes, geographic landmarks near the hazard) to output a severity impact score from 0-100% paired with a Low/Moderate/Critical urgency badge.
8. **Trust Score System & Fix Streaks**: An anti-spam credibility logic. Active citizens earn trust points through verified reports and upvotes on their issues. "Fix Streaks" track consecutive active days (displays 🔥 flame badge) offering bonus points for consistency and resetting upon 3+ days of inactivity.
9. **Explain Simply Translator**: A quick-toggle button uses Groq to translate convoluted official municipal jargon updates into easy-to-understand plain language explanations on the fly.
10. **Live City Pulse Dashboard**: A geo-radar visual engine that scans live incoming complaints natively rendering animated map markers, daily totals, unresolved triage counts, alongside Groq summarizing the immediate daily infrastructure trends.

### For Administrators:
1. **Civic Health Heatmap Dashboard**: A centralized control center complete with a visual Leaflet.js-based interactive Map marking all active/resolved complaints across the city, color-coded by urgency.
2. **AI Actionable Insights**: Features an AI data analyst that summarizes overall civic trends (e.g., "32% increase in sanitation complaints").
3. **Draft Official Responses**: Instead of typing boilerplate responses, Admins input quick shorthand notes (e.g., "fixed pipe yesterday") and the AI expands it into a formal, empathetic public response.
4. **Proof-of-Resolution Workflow**: Requires civic workers to provide verified proof (simulated via strict admin actions) before fully closing out an urgent report.

---

## 🛠️ Tech Stack & Architecture

- **Backend Architecture**: Built in Python with **Flask**.
- **Database**: **SQLite** (Stores relational schemas containing everything from upvotes to geospatial coordinates).
- **Frontend Engine**: Pure **HTML/CSS/Vanilla JS** rendered via Jinja2 templates.
- **UI Design**: Modern **Glassmorphism**, neon-accented gradients, smooth animations, and fully responsive layouts. (CSS Variables & custom tokens).
- **Artificial Intelligence**: **Groq API** running `llama-3.3-70b-versatile` (or similar) to provide near-instant latency inference on complex text, JSON formatting, and structural generation.
- **Geospatial Processing**: **Geopy** for calculating physical geographic distances (meters) using GPS latitude/longitude.
- **Maps API**: OpenStreetMap (Nominatim API) for reverse geocoding and **Leaflet.js** for frontend heatmaps.
- **Notifications**: **Twilio** (SMS) and built-in **SMTP** for verified 6-digit real-time OTP routing.

---

## ⚙️ How It Works (The Core Loop)

1. **Sign Up & Verify**: Users register via Email/Mobile, secured and validated via instantaneous OTPs.
2. **Create a Report**: A citizen takes a picture and types an informal sentence. The **Smart Analyzer** converts it, the **Location Engine** refines the GPS tag, and it goes into the database safely bypassing duplicates (`Smart Merge`).
3. **Triage Strategy**: The backend applies an internal priority logic and the **Resolution Predictor** is locked in. High-priority items ping the top of the admin boards.
4. **Resolution**: The local authority receives the report on their heatmap, acts on it in the real world, types shorthand into the app, and the AI drafts the official public update.
5. **Community Closing Loop**: The issue is verified and closed, upgrading the reporter's `Trust Score` and opening the floor for resolution satisfaction feedback.

---

## 💻 Setup & Installation

**Prerequisites:** 
- Python 3.9+
- A valid Groq API Key
- (Optional) Twilio API credentials & SMTP settings for live OTP.

**1. Clone & Browse to the directory**
Navigate to inside the CivicPulse project folder.

**2. Install Dependencies**
```bash
pip install -r requirements.txt
```

**3. Configure Environment Variables**
Create a `.env` file in the root directory (use `.env.example` as a template):
```env
# SECURITY
SECRET_KEY=super_secret_session_key

# GROQ API (Required for all intelligent features)
GROQ_API_KEY=your_groq_api_key_here

# EMAIL / OTP (Optional)
MAIL_USERNAME=your_gmail@gmail.com
MAIL_PASSWORD=your_app_password

# TWILIO (Optional SMS OTP)
TWILIO_SID=your_sid
TWILIO_TOKEN=your_token
TWILIO_NUMBER=your_number
```

**4. Run the Application**
```bash
python app.py
```
*(The SQLite database `database.db` and all required schema migrations are initialized automatically).*

**5. Access the Web App**
Open your browser and navigate to: `http://127.0.0.1:5000`

> **Admin Access:** Login with the username `admin` and password `admin123` to access the Map Dashboard and civic resolution tools.

---
*Built with ❤️ and AI for a smarter generation of civic engagement.*
