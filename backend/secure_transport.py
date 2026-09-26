"""Signed JSON transport for pipeline messages."""

import socket
import json
from crypto_utils import make_envelope, verify_envelope


class SecureSender:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, payload: dict):
        envelope = make_envelope(payload)
        self.sock.sendto(json.dumps(envelope).encode(), (self.host, self.port))


class SecureReceiver:
    def __init__(self, bind_host, bind_port, max_age_sec=60):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((bind_host, bind_port))
        self.sock.setblocking(False)
        self.max_age = max_age_sec
        self.rejected = 0

    def poll(self):
        """Non-blocking. Returns list of verified payloads."""
        verified = []
        try:
            while True:
                data, addr = self.sock.recvfrom(8192)
                try:
                    envelope = json.loads(data.decode())
                except Exception:
                    self.rejected += 1
                    print(f"[Secure] Malformed from {addr}")
                    continue

                ok, reason = verify_envelope(envelope, self.max_age)
                if not ok:
                    self.rejected += 1
                    print(f"[Secure] ❌ Rejected from {addr}: {reason}")
                    continue

                verified.append(envelope['payload'])
        except BlockingIOError:
            pass
        return verified