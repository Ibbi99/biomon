# config.py
#
# Central configuration file for the entire Python backend.
# All thresholds, paths, and tuning parameters are defined here
# so they can be changed in one place without touching the logic files.

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Firebase connection
DATABASE_URL = "https://bachelordegree-6ed5c-default-rtdb.europe-west1.firebasedatabase.app/"
FIREBASE_KEY_PATH = os.path.join(BASE_DIR, "firebase_key.json")

# How often app.py polls Firebase for new data (in seconds)
POLL_INTERVAL_SECONDS = 0.5
FIREBASE_POLL_INTERVAL = POLL_INTERVAL_SECONDS

# Rolling history sizes for wrist and ECG data (unused in current version)
WRIST_HISTORY_SIZE = 10
ECG_HISTORY_SIZE = 500

# ECG filter parameters
ECG_BASELINE_WINDOW = 15   # Window size for baseline removal filter (samples)
ECG_SMOOTHING_WINDOW = 5   # Window size for moving average smoothing (samples)

# ECG analysis parameters
DEFAULT_ECG_SAMPLING_RATE = 100   # Hz — used when sampling_rate is missing from payload
ECG_SAMPLING_RATE = DEFAULT_ECG_SAMPLING_RATE

ECG_MIN_VALID_SAMPLES = 80        # Minimum samples needed to attempt analysis
ECG_REFRACTORY_PERIOD_SEC = 0.25  # Minimum time between two R-peaks (avoids double detection)
ECG_MIN_RR_SEC = 0.3              # Minimum valid RR interval (~200 BPM max)
ECG_MAX_RR_SEC = 2.0              # Maximum valid RR interval (~30 BPM min)

# Patient IDs that are simulated (vs real ESP32 devices)
# Used by PatientService to set source_type on ChestData
SIMULATED_PATIENT_IDS = {"Patient_01"}

# Alert thresholds — used by AlertService to determine status
ALERT_HR_LOW = 50           # BPM below this → WARNING
ALERT_HR_HIGH = 120         # BPM above this → WARNING
ALERT_SPO2_LOW = 92         # % below this → WARNING
ALERT_SPO2_CRITICAL = 88   # % below this → CRITICAL
ALERT_TEMP_HIGH = 38.0      # °C above this → WARNING
ALERT_TEMP_CRITICAL = 39.0  # °C above this → CRITICAL

# Aliases used in some older parts of the code
HR_LOW_THRESHOLD = ALERT_HR_LOW
HR_HIGH_THRESHOLD = ALERT_HR_HIGH
SPO2_LOW_THRESHOLD = ALERT_SPO2_LOW
TEMP_HIGH_THRESHOLD = ALERT_TEMP_HIGH