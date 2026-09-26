# 🛩️ M3 — Drone Intrusion Detection System (IDS)

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.3+-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)
![MAVLink](https://img.shields.io/badge/MAVLink-v2.0-4B8BBE?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Production--Ready-success?style=for-the-badge)

**Onboard cyber defence for UAVs — real-time, multi-layer, signed, and adaptive.**

[Overview](#-overview) • [Features](#-features) • [Quick Start](#-quick-start)

</div>

---

## 📖 Overview

**M3** is the **Detection Engine** of the Drone IDS — a modular, onboard cyber defence system designed for UAV platforms. It continuously monitors MAVLink telemetry, detects cyber-physical attacks in real time, dispatches autonomous failsafes, and produces a tamper-evident forensic log.

The system implements **seven independent detection layers**, statistical threshold derivation from normal flight data, **online adaptive recalibration**, and **HMAC-SHA256 signed alerts** to prevent forgery.


---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🎯 Detection
- ✅ **7 independent detection layers**
- ✅ Physics-based GPS spoofing (Extended Kalman Filter)
- ✅ Statistical rule engine (μ+5σ thresholds)
- ✅ **Unsupervised ML** for zero-day attacks
- ✅ **Online adaptive recalibration**
- ✅ Flight-phase aware (hover, cruise, takeoff, landing)

</td>
<td width="50%">

### 🔒 Security
- ✅ **HMAC-SHA256 signed alerts**
- ✅ Replay protection (timestamp + nonce)
- ✅ SHA-256 hash-chained forensics
- ✅ Constant-time signature verification
- ✅ Keys stored in chmod-600 file

</td>
</tr>
<tr>
<td>

### 🧩 Engineering
- ✅ No hardcoded thresholds (all data-derived)
- ✅ CLI-configurable
- ✅ Modular architecture
- ✅ Graceful shutdown + signal handling
- ✅ Latency measurement built-in

</td>
</tr>
</table>

---

## 🚀 Quick Start

### Prerequisites

bash
# System
Ubuntu 22.04+ / macOS / WSL2
Python 3.10+


### Installation
# Clone
git clone https://github.com/SoumyaAg16/m3.git
cd m3/m3_detection

# Virtual environment
uv venv --python 3.10
source .venv/bin/activate

# Dependencies
uv pip install pandas numpy scikit-learn joblib pymavlink filterpy scipy cryptography

### Attack coverage:

Attack	        Feature Triggered
GPS Spoofing	gps_jump, gps_cumulative_drift
GPS Jamming	packet_loss_rate, timestamp_max_gap
GPS Freeze	motion_consistency
Control Hijack	heading_change, vz_jump
Altitude Spoof	altitude_drift, altitude_velocity_mismatch


<div align="center">
⭐ Star this repo if it helped you!

Built with ❤️ for a safer sky.

</div>
