# app.py
#
# Main entry point for the Python processing server.
# Runs a continuous poll loop that reads raw sensor data from Firebase,
# processes it through the analysis pipeline, and writes results back to Firebase.
#
# Poll cycle (every POLL_INTERVAL_SECONDS):
#   1. Read all patients from /patients
#   2. For each patient:
#      a. Get live/vitals → WristAnalyzer  → sanitize HR, SpO2, Temp
#      b. Get live/ecg    → ECGAnalyzer    → filter, detect R-peaks, calculate HR
#      c. AlertService    → compare against thresholds → STABLE / WARNING / CRITICAL
#      d. DashboardService→ build payload dict
#      e. Save to /patients/{id}/dashboard/current  ← read by TypeScript frontend
#   3. Print summary line to terminal

import time

from config import POLL_INTERVAL_SECONDS
from firebase_client import FirebaseClient
from services.patient_service import PatientService


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

            try:
                result = patient_service.process_patient(
                    patient_id, raw_wrist, raw_chest,
                    firebase_client=firebase_client,
                )
                payload = result["dashboard_payload"]

                print(
                    f"[{patient_id}] "
                    f"status={payload['status']} "
                    f"HR={payload['heart_rate']} "
                    f"SpO2={payload['spo2']} "
                    f"Temp={payload['temp']} "
                    f"VerifiedHR={payload['verified_hr']}"
                )
            except Exception as e:
                print(f"[{patient_id}] processing error: {e}")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()