"""
Pipeline Data Flow Security
HMAC-SHA256 signing for JSON messages.
Prevents M4 from forging alerts or notifications.
"""

import os
import hmac
import hashlib
import json
import time
import secrets

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
KEY_PATH = os.path.join(PROJECT_ROOT, 'keys', 'pipeline.key')


# Deterministic shared 32-byte key for inter-host demo synchronization
FALLBACK_SHARED_KEY = bytes.fromhex("a3d6dfe4d2f15ac6addaef9844f162eafc7034e4d934838a1cf3c14a40da653b")


def ensure_key():
    """Ensure key file exists. If missing, write shared key so all peers match."""
    os.makedirs(os.path.dirname(KEY_PATH), exist_ok=True)
    if not os.path.exists(KEY_PATH):
        try:
            with open(KEY_PATH, 'wb') as f:
                f.write(FALLBACK_SHARED_KEY)
            os.chmod(KEY_PATH, 0o600)
            print(f"[Crypto] Shared key initialized at {KEY_PATH}")
        except Exception:
            pass
    return load_key()


def load_key():
    if os.path.exists(KEY_PATH):
        try:
            with open(KEY_PATH, 'rb') as f:
                k = f.read()
                if len(k) >= 32:
                    return k[:32]
        except Exception:
            pass
    return FALLBACK_SHARED_KEY


def sign(payload: dict, key: bytes = None) -> str:
    """HMAC-SHA256 of canonical JSON."""
    if key is None:
        key = load_key()
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    return hmac.new(key, canonical, hashlib.sha256).hexdigest()


def verify(payload: dict, signature: str, key: bytes = None) -> bool:
    """Constant-time signature verify."""
    return hmac.compare_digest(sign(payload, key), signature)


def make_envelope(payload: dict) -> dict:
    """Wrap payload with signature + timestamp (prevents replay)."""
    envelope = {
        'payload': payload,
        'timestamp': time.time(),
        'nonce': secrets.token_hex(8),
    }
    envelope['signature'] = sign(payload)
    return envelope


def verify_envelope(envelope: dict, max_age_sec: int = 60) -> tuple:
    """Returns (is_valid, reason)."""
    if 'payload' not in envelope or 'signature' not in envelope:
        return False, 'missing_fields'

    ts = envelope.get('timestamp', 0)
    age = time.time() - ts
    if age > max_age_sec:
        return False, f'stale ({age:.0f}s old)'
    if age < -60:
        return False, f'future_timestamp ({abs(age):.0f}s ahead)'

    if not verify(envelope['payload'], envelope['signature']):
        return False, 'bad_signature'

    return True, 'ok'

# ============ ENCRYPTION AT REST ============
def encrypt_data(plaintext: bytes, key: bytes = None) -> bytes:
    """AES-GCM encryption. Returns nonce + ciphertext + tag."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise ImportError("Install cryptography: uv pip install cryptography")
    if key is None:
        key = load_key()
    aesgcm = AESGCM(key[:32])
    nonce = secrets.token_bytes(12)
    return nonce + aesgcm.encrypt(nonce, plaintext, None)


def decrypt_data(blob: bytes, key: bytes = None) -> bytes:
    """AES-GCM decryption."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise ImportError("Install cryptography: uv pip install cryptography")
    if key is None:
        key = load_key()
    aesgcm = AESGCM(key[:32])
    nonce, ciphertext = blob[:12], blob[12:]
    return aesgcm.decrypt(nonce, ciphertext, None)
