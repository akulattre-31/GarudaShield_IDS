"""
M3 Command Monitor
==================

Observes drone telemetry to infer command-level attacks.

Key insight: M3 never sees M4's outgoing commands (those go to MAVProxy,
not to us). Instead, M3 sees the drone's RESPONSE to those commands:

  M4 sends COMMAND_LONG  →  M2  →  SITL  →  drone reacts
                                                ↓
                     emits COMMAND_ACK, updates HEARTBEAT,
                     emits PARAM_VALUE, changes ATTITUDE, etc.
                                                ↓
                                    MAVProxy broadcasts to M3
                                                ↓
                                    CommandMonitor observes these

Feature outputs (per 1-second sliding window):
  cmd_mode_changes    — # of HEARTBEAT custom_mode transitions
  cmd_arm_changes     — # of HEARTBEAT armed-state transitions
  cmd_param_changes   — # of PARAM_VALUE events with actual value change
  cmd_ack_rate        — # of COMMAND_ACK messages (drone echoing commands)
  cmd_yaw_rate_max    — max |yawspeed| from ATTITUDE (rad/s)
  cmd_yaw_jump        — max |yaw change| within window (rad)

FIX (sysid filtering):
  Previously this class tried to filter out MAVProxy's/GCS's own
  HEARTBEAT with `if autopilot == 0: return`. That's wrong — a GCS/
  MAVProxy heartbeat reports autopilot = MAV_AUTOPILOT_INVALID (8),
  not 0, so the check never actually filtered anything, and GCS
  heartbeats could pollute last_mode/last_armed tracking (spurious or
  missed ARM_DISARM_ATTACK / MODE_CHANGE_ATTACK). Fixed by filtering
  on sysid instead (same pattern as cyber_engine.SequenceValidator),
  applied to every message type this class consumes.

FIX (grace period):
  Every normal flight legitimately arms once and often switches mode
  once (e.g. STABILIZE -> GUIDED) before takeoff. The original rules
  ('any arm/mode transition is suspicious') flagged that first, totally
  normal transition as an attack. Fixed with a grace period: the first
  arm transition and first mode transition observed are treated as
  expected pre-flight setup and NOT counted toward the alerting
  features. Any transition after that (a mid-flight disarm, a forced
  mode change once already flying — which is what the reference attack
  scripts actually do) is still counted exactly as before.
"""

import time
from collections import deque


class CommandMonitor:
    """
    Sliding-window tracker for command-level drone responses.

    Call observe(msg) for every incoming MAVLink message.
    Call snapshot() to get aggregated features for the current window.
    """

    def __init__(self, window_sec=1.0, expected_sysid=1,
                 arm_grace=1, mode_grace=1):
        self.window_sec = window_sec
        self.expected_sysid = expected_sysid
        self.arm_grace = arm_grace       # # of arm transitions to exempt
        self.mode_grace = mode_grace     # # of mode transitions to exempt
        self._arm_transitions_seen = 0
        self._mode_transitions_seen = 0

        # State trackers
        self.last_mode = None
        self.last_armed = None
        self._param_values = {}     # {param_id: last_value}

        # Timestamped event queues (per window)
        self.mode_change_times = deque(maxlen=200)
        self.arm_change_times = deque(maxlen=200)
        self.param_change_times = deque(maxlen=200)
        self.command_ack_times = deque(maxlen=500)

        # Continuous samples (need value, not just timestamp)
        self.yaw_samples = deque(maxlen=500)   # [(t, yawspeed), ...]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _trim(self, now):
        """Drop events older than window_sec."""
        cutoff = now - self.window_sec

        for q in (self.mode_change_times,
                  self.arm_change_times,
                  self.param_change_times,
                  self.command_ack_times):
            while q and q[0] < cutoff:
                q.popleft()

        while self.yaw_samples and self.yaw_samples[0][0] < cutoff:
            self.yaw_samples.popleft()

    def _from_drone(self, msg):
        """
        True if msg's source sysid matches the drone we're tracking.
        Rejects GCS/MAVProxy self-heartbeats, spoofed sysids, and any
        other non-drone source, so command-level features only ever
        reflect the drone's own state/responses.
        """
        sysid = msg.get_srcSystem() if hasattr(msg, 'get_srcSystem') else None
        if sysid is None:
            # Can't determine source — be conservative and accept,
            # rather than silently dropping all command-level detection.
            return True
        return sysid == self.expected_sysid

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def observe(self, msg):
        """Feed one MAVLink message. Called on every received message."""
        if not self._from_drone(msg):
            return

        now = time.time()
        msg_type = msg.get_type()

        # -------- HEARTBEAT: arm state + flight mode --------
        if msg_type == 'HEARTBEAT':
            mode = getattr(msg, 'custom_mode', None)
            armed = bool(msg.base_mode & 128)  # MAV_MODE_FLAG_SAFETY_ARMED

            if self.last_mode is not None and mode != self.last_mode:
                self._mode_transitions_seen += 1
                if self._mode_transitions_seen > self.mode_grace:
                    self.mode_change_times.append(now)
                else:
                    print(f"[CmdMonitor] Mode change #{self._mode_transitions_seen} "
                          f"treated as expected pre-flight setup — not flagged")
            self.last_mode = mode

            if self.last_armed is not None and armed != self.last_armed:
                self._arm_transitions_seen += 1
                if self._arm_transitions_seen > self.arm_grace:
                    self.arm_change_times.append(now)
                else:
                    print(f"[CmdMonitor] Arm/disarm change #{self._arm_transitions_seen} "
                          f"treated as expected pre-flight arm — not flagged")
            self.last_armed = armed

        # -------- ATTITUDE: yaw rate tracking --------
        elif msg_type == 'ATTITUDE':
            yawspeed = getattr(msg, 'yawspeed', 0.0)
            self.yaw_samples.append((now, float(yawspeed)))

        # -------- PARAM_VALUE: only count if VALUE changes --------
        elif msg_type == 'PARAM_VALUE':
            pid = getattr(msg, 'param_id', None)
            val = getattr(msg, 'param_value', None)

            # SITL broadcasts hundreds of PARAM_VALUE messages
            # on startup and whenever a GCS requests PARAM_REQUEST_LIST.
            # We only care about actual value CHANGES (attacks).
            if pid is not None and val is not None:
                # param_id may be bytes or str depending on pymavlink version
                key = pid.decode() if isinstance(pid, bytes) else str(pid)
                prev = self._param_values.get(key)
                if prev is not None and abs(float(val) - float(prev)) > 1e-9:
                    self.param_change_times.append(now)
                self._param_values[key] = float(val)

        # -------- COMMAND_ACK: drone echoing incoming commands --------
        elif msg_type == 'COMMAND_ACK':
            self.command_ack_times.append(now)

        self._trim(now)

    def snapshot(self):
        """
        Return aggregated command-level features for the current window.
        Called by runtime_engine during feature extraction.
        """
        now = time.time()
        self._trim(now)

        # Yaw stats
        yaw_rate_max = 0.0
        yaw_jump = 0.0
        if len(self.yaw_samples) >= 2:
            rates = [abs(r) for _, r in self.yaw_samples]
            yaw_rate_max = max(rates) if rates else 0.0
            yaw_jump = abs(self.yaw_samples[-1][1] - self.yaw_samples[0][1])

        return {
            'cmd_mode_changes':   len(self.mode_change_times),
            'cmd_arm_changes':    len(self.arm_change_times),
            'cmd_param_changes':  len(self.param_change_times),
            'cmd_ack_rate':       len(self.command_ack_times),
            'cmd_yaw_rate_max':   yaw_rate_max,
            'cmd_yaw_jump':       yaw_jump,
        }
