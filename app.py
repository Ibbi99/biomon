import time

from config import POLL_INTERVAL_SECONDS
from firebase_client import FirebaseClient
from services.patient_service import PatientService

# Main entry point for the Python processing server.
# Runs a continuous poll loop that reads raw sensor data from Firebase,
# processes it through the analysis pipeline, and writes results back to Firebase.
#
# Poll cycle (every POLL_INTERVAL_SECONDS):
#   1. Read all patients from /patients
#   2. For each patient:
#      a. Get live/vitals -> WristAnalyzer  -> sanitize HR, SpO2, Temp
#      b. Get live/ecg    -> ECGAnalyzer    -> filter, detect R-peaks, calculate HR
#      c. AlertService    -> compare against thresholds -> STABLE / WARNING / CRITICAL
#      d. DashboardService-> build payload dict
#      e. Save to /patients/{id}/dashboard/current  <- read by TypeScript frontend
#   3. Print summary line to terminal
#
# ECG stale detection:
#   ESP32 timestamps may be Unix ms (NTP synced) or relative millis() values.
#   Relative timestamps (before year 2020) are skipped — they cannot be compared
#   to wall clock time and would always appear stale.
# @author Cristina Vedinas


# ECG data older than this is discarded (electrode disconnected / device offline)
ECG_STALE_THRESHOLD_MS = 10_000

# Unix ms for 2020-01-01 — used to detect relative millis() timestamps
EPOCH_2020_MS = 1_577_836_800_000


def is_stale(timestamp_ms: int) -> bool:
    """
    Returns True if the timestamp is a valid Unix ms timestamp AND
    is older than ECG_STALE_THRESHOLD_MS.

    Relative timestamps (millis() from ESP32 without NTP) are always
    below EPOCH_2020_MS and cannot be compared to wall clock time.
    """
    if not timestamp_ms:
        return False
    if timestamp_ms < EPOCH_2020_MS:
        # Relative timestamp — cannot determine staleness, treat as fresh
        return False
    now_ms = int(time.time() * 1000)
    return (now_ms - timestamp_ms) > ECG_STALE_THRESHOLD_MS


def main():
    firebase_client = FirebaseClient()
    patient_service = PatientService()

    print("=== CENTRAL PROCESSING SERVER STARTED ===")

    while True:
        root = firebase_client.get_patients_root()

        if not isinstance(root, dict):
            print("Firebase root is not a dictionary. Retrying...")
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        for patient_id, patient_data in root.items():
            if not patient_id.startswith("Patient_"):
                continue
            if not isinstance(patient_data, dict):
                continue

            raw_wrist = firebase_client.get_live_vitals(patient_data)
            raw_chest = firebase_client.get_live_ecg(patient_data)

            # Discard stale ECG (only for absolute Unix timestamps)
            if isinstance(raw_chest, dict):
                ecg_ts = raw_chest.get("timestamp", 0)
                batch = raw_chest.get("ecg_batch", [])
                print(f"[{patient_id}] ECG batch size={len(batch)} ts={ecg_ts}")
                if is_stale(ecg_ts):
                    age_sec = (int(time.time() * 1000) - ecg_ts) / 1000
                    print(f"[{patient_id}] Stale ECG ({age_sec:.1f}s old) — discarding")
                    raw_chest = None

            try:
                result = patient_service.process_patient(
                    patient_id,
                    raw_wrist,
                    raw_chest,
                    firebase_client=firebase_client,
                )
                payload = result["dashboard_payload"]

                print(
                    f"[{patient_id}] "
                    f"status={payload['status']} "
                    f"HR={payload['heart_rate']} "
                    f"SpO2={payload['spo2']} "
                    f"Temp={payload['temp']} "
                    f"VerifiedHR={payload['verified_hr']} "
                    f"quality={payload['quality']}"
                )
            except Exception as e:
                import traceback

                print(f"[{patient_id}] processing error: {e}")
                traceback.print_exc()

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
