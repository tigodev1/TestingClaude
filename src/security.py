"""
Advanced Security Features
- API key encryption
- Rate limiting
- Input validation
- CSRF protection
"""

import os
import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import request, jsonify, session


class EncryptionManager:
    """Handle encryption/decryption of sensitive data"""

    def __init__(self, key=None):
        if key:
            self.key = key.encode() if isinstance(key, str) else key
        else:
            self.key = self._generate_key()
        self.fernet = self._create_fernet()

    def _generate_key(self):
        """Generate a secure encryption key"""
        return Fernet.generate_key()

    def _create_fernet(self):
        """Create Fernet cipher from key"""
        # If key is not a valid Fernet key, derive one
        if len(self.key) != 44:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'datastore-manager-salt',
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.key))
            return Fernet(key)
        return Fernet(self.key)

    def encrypt(self, data):
        """Encrypt string data"""
        if isinstance(data, str):
            data = data.encode()
        encrypted = self.fernet.encrypt(data)
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, encrypted_data):
        """Decrypt string data"""
        if isinstance(encrypted_data, str):
            encrypted_data = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = self.fernet.decrypt(encrypted_data)
        return decrypted.decode()


class RateLimiter:
    """Custom rate limiting with sliding window"""

    def __init__(self, max_requests=100, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # IP -> [(timestamp, count)]

    def is_allowed(self, identifier):
        """Check if request is allowed"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)

        if identifier not in self.requests:
            self.requests[identifier] = []

        # Clean old requests
        self.requests[identifier] = [
            ts for ts in self.requests[identifier]
            if ts > window_start
        ]

        # Check count
        if len(self.requests[identifier]) >= self.max_requests:
            return False

        # Add current request
        self.requests[identifier].append(now)
        return True

    def get_remaining(self, identifier):
        """Get remaining requests in window"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)

        if identifier not in self.requests:
            return self.max_requests

        valid_requests = [
            ts for ts in self.requests[identifier]
            if ts > window_start
        ]
        return max(0, self.max_requests - len(valid_requests))

    def get_reset_time(self, identifier):
        """Get time until window resets"""
        if identifier not in self.requests or not self.requests[identifier]:
            return 0

        oldest = min(self.requests[identifier])
        reset_at = oldest + timedelta(seconds=self.window_seconds)
        remaining = (reset_at - datetime.utcnow()).total_seconds()
        return max(0, remaining)


class InputValidator:
    """Validate and sanitize user inputs"""

    @staticmethod
    def validate_datastore_name(name):
        """Validate datastore name format"""
        if not name or not isinstance(name, str):
            return False, "Datastore name is required"

        if len(name) > 50:
            return False, "Datastore name too long (max 50 characters)"

        # Only allow alphanumeric, underscore, hyphen
        if not all(c.isalnum() or c in '_-' for c in name):
            return False, "Datastore name contains invalid characters"

        return True, None

    @staticmethod
    def validate_key_name(key):
        """Validate entry key format"""
        if not key or not isinstance(key, str):
            return False, "Key name is required"

        if len(key) > 50:
            return False, "Key name too long (max 50 characters)"

        return True, None

    @staticmethod
    def validate_scope(scope):
        """Validate scope format"""
        if not scope or not isinstance(scope, str):
            return False, "Scope is required"

        if len(scope) > 50:
            return False, "Scope too long (max 50 characters)"

        return True, None

    @staticmethod
    def validate_universe_id(universe_id):
        """Validate universe ID format"""
        if not universe_id or not isinstance(universe_id, str):
            return False, "Universe ID is required"

        # Should be numeric
        if not universe_id.isdigit():
            return False, "Universe ID must be numeric"

        if len(universe_id) > 20:
            return False, "Universe ID too long"

        return True, None

    @staticmethod
    def validate_api_key(api_key):
        """Validate API key format (basic check)"""
        if not api_key or not isinstance(api_key, str):
            return False, "API key is required"

        if len(api_key) < 20:
            return False, "API key appears to be invalid (too short)"

        if len(api_key) > 1000:
            return False, "API key appears to be invalid (too long)"

        return True, None

    @staticmethod
    def sanitize_string(value, max_length=255):
        """Sanitize string input"""
        if not isinstance(value, str):
            return str(value)[:max_length]

        # Remove control characters
        value = ''.join(c for c in value if c.isprintable() or c in '\n\r\t')

        return value[:max_length]


def generate_csrf_token():
    """Generate CSRF token"""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']


def validate_csrf_token(token):
    """Validate CSRF token"""
    return token and session.get('csrf_token') == token


def require_csrf(f):
    """Decorator to require CSRF token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            if not validate_csrf_token(token):
                return jsonify({'error': 'Invalid CSRF token'}), 403
        return f(*args, **kwargs)
    return decorated_function


def hash_password(password):
    """Hash password with salt"""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode(),
        salt.encode(),
        100000
    )
    return f"{salt}${pwd_hash.hex()}"


def verify_password(password, hash_string):
    """Verify password against hash"""
    try:
        salt, pwd_hash = hash_string.split('$')
        new_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt.encode(),
            100000
        )
        return new_hash.hex() == pwd_hash
    except Exception:
        return False


def generate_api_token():
    """Generate secure API token"""
    return secrets.token_urlsafe(32)
