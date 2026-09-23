# 🛡️ GarudaShield: Autonomous Drone IDS & Simulation Testbed

Welcome to the **GarudaShield** collaborative simulation environment. This repository houses the simulation pipeline, telemetry logging, attack injection testbed, and real-time network broadcast system designed to test and train our Machine Learning Intrusion Detection System (IDS).

---

## 👥 Tactical Role Roster

| Role | Codename | Primary Interface / Script | Function | Target Port |
| --- | --- | --- | --- | --- |
| **M1** | **Flight Controller** | `sim_vehicle.py` | Hosts SITL quadcopter physics & MAVProxy switchboard | Broadcasts all |
| **M2** | **Black Box** | `m2_logger.py` | Records high-variance telemetry logs with network jitter | Local (`14550`) |
| **M3** | **Shield Sentinel** | `team_listener.py` | Consumes decoded position/velocity telemetry for ML IDS | `14551` |
| **M4** | **Phantom Threat** | `m4_dynamic_injector.py` | Injects randomized speed, radius, and erratic mode overrides | `14552` |
| **M5** | **Tactical HUD** | Custom Frontend / `team_listener.py` | Real-time ground station & raw telemetry visualization | `69` |

---

## ⚡ Quickstart: ArduPilot SITL Setup (M1 Host Only)

If you are running the flight controller (M1), install ArduPilot SITL on Ubuntu / Pop!_OS:

```bash
# 1. Clone ArduPilot repository
cd ~
git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git
cd ardupilot

# 2. Run the environment install script (installs build toolchain & dependencies)
Tools/environment_install/install-prereqs-ubuntu.sh -y

# 3. Reload environment variables
source ~/.profile
source ~/.bashrc

# 4. Activate virtual environment
source ~/venv-ardupilot/bin/activate

```

---

## 📦 Python Environment Setup (All Teammates: M2, M3, M4, M5)

Every team member needs the Python client environment:

```bash
# 1. Clone this repository
git clone https://github.com/akulattre-31/GarudaShield_IDS.git
cd GarudaShield_IDS

# 2. Create and activate dedicated virtual environment
python3 -m venv drone_env
source drone_env/bin/activate

# 3. Install core dependencies
pip install --upgrade pip
pip install -r requirements.txt

```

*(Core requirement: `pymavlink`)*

---

## 🕹️ Flight Operations Guide

Follow this sequence to spin up flight operations across the squad:

### Phase 1: M1 Spins Up the Switchboard

M1 launches SITL with MAVLink 2.0 support and broadcasts UDP telemetry across assigned endpoints:

```bash
cd ~/ardupilot
source ~/venv-ardupilot/bin/activate

Tools/autotest/sim_vehicle.py -v ArduCopter -f quad --map --console \
  --mavproxy-args="--mav20" \
  --out=127.0.0.1:14550 \
  --out=127.0.0.1:14552 \
  --out=127.0.0.1:14554 \
  --out=<M3_IP_ADDRESS>:14551 \
  --out=<M5_IP_ADDRESS>:69

```

> 💡 **Tip:** If a teammate joins late, add them directly in the MAVProxy console without restarting:
> ```text
> output add <NEW_IP>:<PORT>
> 
> ```
> 
> 

---

### Phase 2: M1 Flight Checklist (In MAVProxy Terminal)

Wait until you see `pre-arm good` and EKF GPS initialization, then execute:

```text
GUIDED> arm throttle
GUIDED> takeoff 50

```

*Wait until the quadcopter ascends to 50 meters before initiating circular patrol:*

```text
GUIDED> mode CIRCLE

```

---

### Phase 3: Squad Sync

#### 📊 For M3 & M5 (Telemetry Consumers)

1. Open `team_listener.py`.
2. Ensure your assigned port is set:
* **M3:** `PORT = 14551`
* **M5:** `PORT = 69`


3. Execute:
```bash
# Standard execution for M3:
python3 team_listener.py

# For M5 (Port 69 is privileged, root required):
sudo python3 team_listener.py

```



#### 📁 For M2 (Dataset Recording)

```bash
python3 m2_logger.py

```

*Creates jitter-compensated `flight_data.csv` for ML training.*

#### 🎯 For M4 (Attacker Node)

```bash
python3 m4_dynamic_injector.py

```

*Attempts unauthorized command injection, trajectory deviation, and telemetry spoofs.*

---

## 🔐 Cryptographic Hardening (MAVLink 2 Signing)

To test our intrusion detection engine against malicious packet rejection, lock the flight link down with cryptographic authentication.

In the active **MAVProxy terminal**, run:

```text
module load signing
signing setup MySuperSecret32ByteTeamPassphrase

```

### What Happens:

* MAVProxy and ArduPilot exchange cryptographic shared secrets.
* Packets without a valid SHA-256 signature matching the secret key are dropped at the flight controller level.
* **M4's injector is instantly neutered** unless their attack script is updated to generate valid cryptographic HMAC signatures using the passphrase.

---

## 🛠️ Common Gotchas & Troubleshooting

* **Drone Refuses Takeoff (`Need Position Estimate`):**
The simulated EKF is still acquiring virtual GPS locks. Wait 15–30 seconds after launch until the HUD confirms `pre-arm good`.
* **Single vs. Double Dashes:**
`--console` and `--map` require double dashes (`--`). Single dashes cause sub-argument parsing crashes.
* **GitHub Push Rejection (`Invalid username or token`):**
GitHub requires Personal Access Tokens (PATs) instead of account passwords. Generate a token via **GitHub Settings ➔ Developer settings ➔ Personal access tokens (classic)** with `repo` scope enabled.
* **Port 69 Permission Errors (M5):**
Ports below 1024 are privileged on Linux. Always run listener instances on port 69 with `sudo`.
