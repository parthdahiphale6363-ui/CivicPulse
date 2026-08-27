import sys, base64
sys.path.append('.')
from app import ask_groq_vision

# Create a dummy 1x1 transparent png
png_b64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
prompt = '''Format your response as pure JSON like this: { "is_valid": true, "reason": "If false, why?", "issue_type": "Unknown", "severity_clues": "none"}'''
res = ask_groq_vision(png_b64, prompt)
print('Vision Response:', res)
