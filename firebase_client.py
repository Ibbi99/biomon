import os
import time
from typing import Any, Dict

import firebase_admin
from firebase_admin import credentials, db

from config import DATABASE_URL, FIREBASE_KEY_PATH

# Wrapper around the Firebase Admin SDK.
# Handles initialization and provides read/write methods
# for all Firebase paths used by the backend.
#
# Firebase structure written by this client:
#   /patients/{id}/live/vitals                  <- written by ESP32 / simulator
#   /patients/{id}/live/ecg                     <- written by ESP32 / simulator
#   /patients/{id}/processed/ecg_latest         <- written by PatientService (filtered ECG)
#   /patients/{id}/dashboard/current            <- written by PatientService (full dashboard payload)
#   /patients/{id}/history/ecg_processed/{ts}   <- written by PatientService (verified_hr per batch)
#   /patients/{id}/history/vitals/{ts}          <- written by PatientService (HR/SpO2/Temp per cycle)
# @author Cristina Vedinas


class FirebaseClient:
    def __init__(
        self, database_url: str = DATABASE_URL, key_path: str = FIREBASE_KEY_PATH
    ):
        if not os.path.exists(key_path):
            raise FileNotFoundError(f"Firebase key not found: {key_path}")

        if not firebase_admin._apps:
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred, {"databaseURL": database_url})

    def get_patients_root(self) -> Dict[str, Any]:
        """Returns the entire /patients node. Used by app.py each poll cycle."""
        return db.reference("/patients").get() or {}

    def get_live_vitals(self, patient_data: Dict[str, Any]) -> Dict[str, Any] | None:
        """Extracts live/vitals dict from a patient snapshot."""
        live = patient_data.get("live")
        if not isinstance(live, dict):
            return None
        vitals = live.get("vitals")
        if not isinstance(vitals, dict):
            return None
        return vitals

    def get_live_ecg(self, patient_data: Dict[str, Any]) -> Dict[str, Any] | None:
        """Extracts live/ecg dict from a patient snapshot."""
        live = patient_data.get("live")
        if not isinstance(live, dict):
            return None
        ecg = live.get("ecg")
        if not isinstance(ecg, dict):
            return None
        return ecg

    def get_patient_name(self, patient_id: str) -> str:
        """Reads the current patient name from /patients/{id}/profile/name.
        Returns the patient_id itself if no name has been set yet."""
        name = db.reference(f"/patients/{patient_id}/profile/name").get()
        return name if isinstance(name, str) and name.strip() else patient_id

    def save_processed_wrist(self, patient_id: str, payload: Dict[str, Any]) -> None:
        """Saves processed wrist data to /patients/{id}/processed/wrist_latest."""
        db.reference(f"/patients/{patient_id}/processed/wrist_latest").set(payload)

    def save_ecg_result(self, patient_id: str, payload: Dict[str, Any]) -> None:
        """Saves the filtered ECG result to /patients/{id}/processed/ecg_latest."""
        db.reference(f"/patients/{patient_id}/processed/ecg_latest").set(payload)

    def save_analysis_result(self, patient_id: str, payload: Dict[str, Any]) -> None:
        """Saves a generic analysis result to /patients/{id}/analysis_result."""
        db.reference(f"/patients/{patient_id}/analysis_result").set(payload)

    def save_dashboard_data(self, patient_id: str, payload: Dict[str, Any]) -> None:
        """
        Saves the full dashboard payload to /patients/{id}/dashboard/current.
        This is the path read by the TypeScript frontend (FirebaseService.ts).
        """
        db.reference(f"/patients/{patient_id}/dashboard/current").set(payload)

    def save_ecg_history_entry(self, patient_id: str, ecg_result: Any) -> None:
        """
        Saves a compact ECG summary to /patients/{id}/history/ecg_processed/{ts}.
        Saves only lightweight fields (NOT ecg_filtered array) to avoid
        filling Firebase with 200 values per second.
        Used by the history chart to show verified_hr and confidence over time.
        """
        ts = int(time.time() * 1000)
        payload = {
            "timestamp": ts,
            "patient_name": self.get_patient_name(patient_id),
            "verified_hr": ecg_result.verified_hr,
            "confidence": ecg_result.confidence,
            "quality": ecg_result.quality,
            "missing_samples": ecg_result.missing_samples,
        }
        db.reference(f"/patients/{patient_id}/history/ecg_processed/{ts}").set(payload)

    def save_vitals_history_entry(
        self, patient_id: str, wrist: Any, verified_hr: Any
    ) -> None:
        """
        Saves a compact vitals summary to /patients/{id}/history/vitals/{ts}.
        Called every poll cycle when wrist data has at least one valid field.

        Uses server time as the key — ESP32 timestamps may be relative millis(),
        unsuitable as Firebase keys or for orderByChild("timestamp") queries.

        Fields saved match VitalsEntry interface in HistoryChart.ts:
            heartRate   — raw HR from wrist sensor (MAX30100), camelCase for HistoryChart
            verified_hr — best available HR (ECG if present, wrist otherwise)
            spo2        — oxygen saturation %
            temperature — ambient temperature from HTU21D (deg C)
            timestamp   — Unix ms (server time) — used by fetchHistory orderByChild
        """
        if wrist is None:
            return
        # Only save if we have at least one valid vital
        if (
            wrist.heart_rate is None
            and wrist.spo2 is None
            and wrist.temperature is None
        ):
            return

        ts = int(time.time() * 1000)
        payload = {
            "timestamp": ts,
            "patient_name": self.get_patient_name(patient_id),
            "heartRate": wrist.heart_rate,  # camelCase — matches VitalsEntry in HistoryChart.ts
            "verified_hr": verified_hr,
            "spo2": wrist.spo2,
            "temperature": wrist.temperature,
        }
        db.reference(f"/patients/{patient_id}/history/vitals/{ts}").set(payload)
