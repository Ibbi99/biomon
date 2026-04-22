# services/patient_service.py
#
# Orchestrates the full processing pipeline for a single patient per poll cycle.
# Called by app.py for every patient found in Firebase.
#
# Processing order:
#   1. Sanitize raw wrist data    -> WristAnalyzer.sanitize()
#   2. Validate and clean ECG     -> _clean_ecg_batch() + _is_viable_ecg_batch()
#   3. Analyze ECG signal         -> ECGAnalyzer.analyze()
#   4. Save filtered ECG          -> firebase_client.save_ecg_result()
#   5. Evaluate alert status      -> AlertService.evaluate()
#   6. Build dashboard payload    -> DashboardService.build_payload()
#   7. Save dashboard to Firebase -> firebase_client.save_dashboard_data()

import math

from analyzer.wrist_analyzer import WristAnalyzer
from analyzer.ecg_analyzer import ECGAnalyzer
from services.alert_service import AlertService
from services.dashboard_service import DashboardService
from config import DEFAULT_ECG_SAMPLING_RATE, SIMULATED_PATIENT_IDS
from models import ChestData, PatientState


class PatientService:
    def __init__(self):
        self.wrist_analyzer = WristAnalyzer()
        self.ecg_analyzer = ECGAnalyzer()
        self.alert_service = AlertService()
        self.dashboard_service = DashboardService()

    def process_patient(
        self,
        patient_id: str,
        raw_wrist: dict | None,
        raw_chest: dict | None,
        firebase_client=None,
    ) -> dict:
        state = PatientState(patient_id=patient_id)

        wrist = None
        if isinstance(raw_wrist, dict):
            wrist = self.wrist_analyzer.sanitize(raw_wrist)
            state.last_wrist = wrist

        ecg_result = None
        if isinstance(raw_chest, dict) and raw_chest.get("ecg_batch"):
            raw_batch = raw_chest.get("ecg_batch", [])
            cleaned_batch, missing_samples = self._clean_ecg_batch(raw_batch)

            if self._is_viable_ecg_batch(cleaned_batch):
                chest = ChestData(
                    ecg_batch=cleaned_batch,
                    timestamp=self._to_int(raw_chest.get("timestamp", 0)),
                    patient_id=patient_id,
                    source_type="simulated" if patient_id in SIMULATED_PATIENT_IDS else "firebase_real",
                    sampling_rate=self._to_float(raw_chest.get("sampling_rate")) or DEFAULT_ECG_SAMPLING_RATE,
                    expected_batch_size=self._to_int(raw_chest.get("expected_batch_size")) or len(raw_batch),
                    missing_samples=missing_samples,
                )

                ecg_result = self.ecg_analyzer.analyze(chest)
                state.last_ecg_result = ecg_result

                if firebase_client is not None:
                    filtered_payload = {
                        "ecg_filtered": ecg_result.filtered_signal,
                        "peaks": ecg_result.peaks,
                        "verified_hr": ecg_result.verified_hr,
                        "confidence": ecg_result.confidence,
                        "timestamp": ecg_result.timestamp,
                        "quality": ecg_result.quality,
                        "source_type": ecg_result.source_type,
                        "sampling_rate": ecg_result.sampling_rate,
                        "missing_samples": ecg_result.missing_samples,
                    }
                    firebase_client.save_ecg_result(patient_id, filtered_payload)
            else:
                ecg_result = None

        status = self.alert_service.evaluate(wrist, ecg_result)
        state.last_status = status

        dashboard_payload = self.dashboard_service.build_payload(status, ecg_result)

        if firebase_client is not None:
            firebase_client.save_dashboard_data(patient_id, dashboard_payload)

        return {
            "state": state,
            "dashboard_payload": dashboard_payload,
            "processed_wrist": {
                "heart_rate": wrist.heart_rate if wrist else None,
                "spo2": wrist.spo2 if wrist else None,
                "temp": wrist.temperature if wrist else None,
                "timestamp": wrist.timestamp if wrist else 0,
            } if wrist else None,
            "processed_ecg": {
                "filtered_signal": ecg_result.filtered_signal if ecg_result else [],
                "peaks": ecg_result.peaks if ecg_result else [],
                "verified_hr": ecg_result.verified_hr if ecg_result else None,
                "confidence": ecg_result.confidence if ecg_result else 0.0,
                "timestamp": ecg_result.timestamp if ecg_result else 0,
                "quality": ecg_result.quality if ecg_result else "invalid",
                "source_type": ecg_result.source_type if ecg_result else "unknown",
                "sampling_rate": ecg_result.sampling_rate if ecg_result else None,
                "missing_samples": ecg_result.missing_samples if ecg_result else 0,
            } if ecg_result else None,
        }

    def _clean_ecg_batch(self, raw_values) -> tuple[list[float], int]:
        cleaned = []
        missing = 0
        for value in raw_values:
            try:
                x = float(value)
                if math.isnan(x) or math.isinf(x):
                    missing += 1
                    continue
                cleaned.append(x)
            except (TypeError, ValueError):
                missing += 1
        return cleaned, missing

    def _is_viable_ecg_batch(self, signal: list[float]) -> bool:
        """
        Accepts any batch with at least 20 samples and minimal signal presence.
        Threshold of 0.005 accepts both normal ECG (range ~1.5-2.0) and
        flatline signals from cardiac arrest (range ~0.02).
        Rejects truly empty or corrupt batches.
        """
        if len(signal) < 20:
            return False
        dynamic_range = max(signal) - min(signal)
        return dynamic_range >= 0.005

    @staticmethod
    def _to_float(value):
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
