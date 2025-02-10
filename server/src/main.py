from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
from functools import wraps
import os
from sys import exit

app = Flask(__name__)

# Configuration from environment variables
DATABASE = os.getenv('DATABASE_PATH')
AUTH_TOKENS_JSON = os.getenv('AUTH_TOKENS')

# Validate required environment variables
if not DATABASE:
    print("Error: DATABASE_PATH environment variable is required")
    exit(1)
if not AUTH_TOKENS_JSON:
    print("Error: AUTH_TOKENS environment variable is required")
    exit(1)

# Parse AUTH_TOKENS JSON
try:
    import json
    AUTH_TOKENS = json.loads(AUTH_TOKENS_JSON)
    if not isinstance(AUTH_TOKENS, dict):
        print("Error: AUTH_TOKENS must be a JSON object")
        exit(1)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON in AUTH_TOKENS: {e}")
    exit(1)

def init_db():
    print('init_db()')
    """Initialize the database and create the logs table if it doesn't exist."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS request_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            identity TEXT NOT NULL,
            request_body TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def require_token(f):
    """Decorator to check for valid bearer token based on identity."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'error': 'No authorization header'}), 401
            
        try:
            # Extract the token from "Bearer <token>"
            token_type, token = auth_header.split()
            if token_type.lower() != 'bearer':
                return jsonify({'error': 'Invalid authorization type'}), 401

            # Get identity from request JSON
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400

            request_data = request.get_json()
            identity = request_data.get('identity')

            if not identity:
                return jsonify({'error': 'Identity field is required'}), 400

            # Check if identity exists and token matches
            expected_token = AUTH_TOKENS.get(identity)
            if not expected_token:
                return jsonify({'error': 'Invalid identity'}), 401

            if token != expected_token:
                return jsonify({'error': 'Invalid token for given identity'}), 401
                
        except ValueError:
            return jsonify({'error': 'Invalid authorization format'}), 401
            
        return f(*args, **kwargs)
    return decorated

def log_request(request_body, identity):
    """Log the request body and identity to the database."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    timestamp = datetime.utcnow().isoformat()
    c.execute(
        'INSERT INTO request_logs (timestamp, identity, request_body) VALUES (?, ?, ?)',
        (timestamp, identity, str(request_body))
    )
    conn.commit()
    conn.close()

@app.route('/log', methods=['POST'])
@require_token
def log_endpoint():
    """Endpoint to receive and log JSON requests."""
    try:
        request_body = request.get_json()
        identity = request_body['identity']  # We know this exists because of @require_token
        log_request(request_body, identity)
        return jsonify({'status': 'success', 'message': 'Request logged'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_db()  # Initialize database and create table if needed
