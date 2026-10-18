"""Blueprint routes for standalone RAG interactions."""
import logging
from functools import wraps
from flask import Blueprint, request, jsonify, session
from flask_wtf.csrf import validate_csrf

from .service import ask

logger = logging.getLogger("civicpulse_rag")

rag_bp = Blueprint("rag", __name__)


def api_login_required(f):
    """Decorator ensuring user is authenticated for API requests."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required. Please log in."}), 401
        return f(*args, **kwargs)
    return decorated_function


def verify_csrf():
    """Verify CSRF token from header or JSON body."""
    csrf_token = (
        request.headers.get("X-CSRFToken")
        or request.headers.get("X-CSRF-Token")
    )
    if not csrf_token and request.is_json:
        body = request.get_json(silent=True) or {}
        csrf_token = body.get("csrf_token")

    if not csrf_token:
        raise ValueError("Missing CSRF token")

    validate_csrf(csrf_token)


@rag_bp.route("/api/rag/ask", methods=["POST"])
@api_login_required
def rag_ask():
    """Endpoint for verified civic knowledge retrieval and answering.

    Enforces authentication, CSRF token validation, payload limits (max 500 chars),
    and rate limiting.
    """
    # 1. CSRF Verification
    try:
        verify_csrf()
    except Exception as e:
        logger.warning(f"CSRF verification failed on /api/rag/ask: {e}")
        return jsonify({"error": "CSRF verification failed."}), 400

    # 2. JSON Payload Validation
    if not request.is_json:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    data = request.get_json(silent=True) or {}
    question = data.get("question", "")

    if not isinstance(question, str):
        return jsonify({"error": "Field 'question' must be a string."}), 400

    question = question.strip()
    if not question:
        return jsonify({"error": "Question cannot be empty."}), 400

    if len(question) > 500:
        return jsonify({"error": "Question exceeds maximum limit of 500 characters."}), 400

    history = data.get("history")
    if history is not None and not isinstance(history, list):
        history = None

    # 3. RAG Retrieval and Answering
    try:
        result = ask(question, history=history)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Unhandled error in rag_ask: {e}")
        return jsonify({"error": "Failed to retrieve verified information."}), 500
