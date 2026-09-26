"""
M3 Forensics — Encrypted + Hash-Chained Ledger
Tamper-evident incident log with AES-GCM encryption at rest.
"""

import os
import json
import hashlib
import time
from crypto_utils import encrypt_data, decrypt_data

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_LEDGER = os.path.join(PROJECT_ROOT, 'logs', 'incident_ledger.enc')


class IncidentLedger:
    def __init__(self, path=DEFAULT_LEDGER):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.entries = self._load()

    def _load(self):
        """Load and decrypt existing ledger."""
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, 'rb') as f:
                blob = f.read()
            plaintext = decrypt_data(blob)
            return json.loads(plaintext.decode())
        except Exception as e:
            print(f"[Ledger] Load failed: {e}")
            return []

    def _save(self):
        """Encrypt and save ledger."""
        plaintext = json.dumps(self.entries, indent=2).encode()
        blob = encrypt_data(plaintext)
        with open(self.path, 'wb') as f:
            f.write(blob)

    def _last_hash(self):
        return self.entries[-1]['hash'] if self.entries else '0' * 64

    def log(self, attack_type, confidence, source, features=None):
        """Add a new hash-chained entry."""
        entry = {
            'timestamp': time.time(),
            'iso_time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'attack_type': attack_type,
            'confidence': round(confidence, 4),
            'source': source,
            'features': features or {},
            'prev_hash': self._last_hash(),
        }
        payload = json.dumps({k: v for k, v in entry.items() if k != 'hash'},
                             sort_keys=True).encode()
        entry['hash'] = hashlib.sha256(payload).hexdigest()
        self.entries.append(entry)
        self._save()
        return entry['hash']

    def verify(self):
        """Verify full hash chain."""
        prev = '0' * 64
        for e in self.entries:
            if e['prev_hash'] != prev:
                return False, e['timestamp']
            payload = json.dumps({k: v for k, v in e.items() if k != 'hash'},
                                 sort_keys=True).encode()
            if hashlib.sha256(payload).hexdigest() != e['hash']:
                return False, e['timestamp']
            prev = e['hash']
        return True, None

    def export_plaintext(self, output_path):
        """Export human-readable JSON (for proposal/demo)."""
        with open(output_path, 'w') as f:
            json.dump(self.entries, f, indent=2)
        print(f"[Ledger] Exported {len(self.entries)} entries to {output_path}")