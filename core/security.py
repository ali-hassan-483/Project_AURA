import hmac
import hashlib
import time
from typing import Optional, Dict
import jwt
from fastapi import Request, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config.settings import settings

security = HTTPBearer(auto_error=False)

def verify_whatsapp_signature(payload_bytes: bytes, signature_header: Optional[str]) -> bool:
    """
    Validates X-Hub-Signature-256 header sent by Meta WhatsApp Cloud API.
    Header format: 'sha256=<hex_digest>'
    """
    if not settings.WHATSAPP_APP_SECRET:
        # If secret is not set in development, log warning but allow or fail safely
        return True
    
    if not signature_header:
        return False
    
    parts = signature_header.split("sha256=")
    if len(parts) != 2:
        return False
    
    expected_hash = parts[1]
    mac = hmac.new(
        key=settings.WHATSAPP_APP_SECRET.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256
    )
    generated_hash = mac.hexdigest()
    return hmac.compare_digest(generated_hash, expected_hash)

def create_admin_jwt(username: str, expires_delta_seconds: int = 86400 * 7) -> str:
    """Generates a secure JWT token for Admin Dashboard access"""
    payload = {
        "sub": username,
        "role": "admin",
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_delta_seconds
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def verify_admin_jwt(token: str) -> Optional[Dict]:
    """Decodes and validates admin JWT"""
    try:
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if decoded.get("role") == "admin":
            return decoded
        return None
    except Exception:
        return None

def verify_admin_credentials(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> Dict:
    """FastAPI dependency to protect admin endpoints"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = verify_admin_jwt(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired admin session token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

class SimpleRateLimiter:
    """In-memory sliding window rate limiter"""
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        timestamps = self.requests.get(client_id, [])
        # filter out expired timestamps
        valid_timestamps = [t for t in timestamps if now - t < self.window_seconds]
        if len(valid_timestamps) >= self.max_requests:
            self.requests[client_id] = valid_timestamps
            return False
        valid_timestamps.append(now)
        self.requests[client_id] = valid_timestamps
        return True

rate_limiter = SimpleRateLimiter()
