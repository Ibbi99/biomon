# firebase_client.py
#
# Wrapper around the Firebase Admin SDK.
# Handles initialization and provides read/write methods
# for all Firebase paths used by the backend.
#
# Firebase structure written by this client:
#   /patients/{id}/live/vitals          ← written by patient_simulator.py / ESP32
#   /patients/{id}/live/ecg             ← written by patient_simulator.py / ESP32
#   /patients/{id}/processed/ecg_latest ← written by PatientService (filtered ECG)
#   /patients/{id}/dashboard/current    ← written by PatientService (full dashboard payload)

import os
from typing import Any, Dict

import firebase_admin
from firebase_admin import credentials, db

from config import DATABASE_URL, FIREBASE_KEY_PATH


class FirebaseClient:
    def __init__(self, database_url: str = DATABASE_URL, key_path: str = FIREBASE_KEY_PATH):
        if not os.path.exists(key_path):
            raise FileNotFoundError(f"Firebase key not found: {key_path}")

        # Only initialize once — Firebase Admin SDK raises an error if initialized twice
        if not firebase_admin._apps:
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred, {"databaseURL": database_url})

    def get_patients_root(self) -> Dict[str, Any]:
        """
        Returns the entire /patients node as a dict.
        Used by app.py to iterate over all patients each poll cycle.
        """
        return db.reference("/patients").get() or {}

    def get_live_vitals(self, patient_data: Dict[str, Any]) -> Dict[str, Any] | None:
        """
        Extracts the live/vitals dict from a patient's data snapshot.
        Returns None if the path doesn't exist or is malformed.
        """
        live = patient_data.get("live")
        if not isinstance(live, dict):
            return None
        vitals = live.get("vitals")
        if not isinstance(vitals, dict):
            return None
        return vitals

    def get_live_ecg(self, patient_data: Dict[str, Any]) -> Dict[str, Any] | None:
        """
        Extracts the live/ecg dict from a patient's data snapshot.
        Returns None if the path doesn't exist or is malformed.
        """
        live = patient_data.get("live")
        if not isinstance(live, dict):
            return None
        ecg = live.get("ecg")
        if not isinstance(ecg, dict):
            return None
        return ecg

    def save_processed_wrist(self, patient_id: str, payload: Dict[str, Any]) -> None:
        """Saves processed wrist data to /patients/{id}/processed/wrist_latest."""
        db.reference(f"/patients/{patient_id}/processed/wrist_latest").set(payload)

    def save_ecg_result(self, patient_id: str, payload: Dict[str, Any]) -> None:
        """Saves the filtered ECG analysis result to /patients/{id}/processed/ecg_latest."""
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