"""
M3 Cyber Engine
Rate limiter, sequence validator, sysid check.
"""

import time
from collections import deque


class RateLimiter:
    def __init__(self, max_hz=1000, window_sec=1.0):
        self.max_hz = max_hz
        self.window_sec = window_sec
        self.timestamps = deque()

    def check(self, timestamp=None):
        now = timestamp if timestamp else time.time()
        self.timestamps.append(now)
        while self.timestamps and now - self.timestamps[0] > self.window_sec:
            self.timestamps.popleft()
        rate = len(self.timestamps) / self.window_sec
        return rate > self.max_hz, rate

class SequenceValidator:
    """Detects rogue injection by sequence and sysid checks.
    
    Important: MAVLink maintains a separate sequence counter PER MESSAGE TYPE.
    So we must track seq per (sysid, compid, msgid), not just (sysid, compid).
    """
    def __init__(self, expected_sysid=1):
        self.expected_sysid = expected_sysid
        # Key: (sysid, compid, msgid) → last_seq
        self.last_seq = {}

    def check(self, sysid, compid, msgid, seq):
        """Returns list of alert strings (empty if OK)."""
        alerts = []
        key = (sysid, compid, msgid)

        # SysID check — but skip for GCS (sysid=255) and ground stations
        # In our demo, we only accept sysid=1 from the drone
        if sysid not in (self.expected_sysid, 255):
            alerts.append('ROGUE_INJECTION_ALERT')

        # Sequence check — per message type
        if key in self.last_seq:
            last = self.last_seq[key]
            expected = (last + 1) % 256
            if seq != expected:
                # Backward jump or way-off forward jump
                if seq < last and last - seq < 128:
                    alerts.append('ROGUE_INJECTION_ALERT')
                elif abs(seq - expected) > 5:
                    alerts.append('ROGUE_INJECTION_ALERT')

        self.last_seq[key] = seq
        return alerts
