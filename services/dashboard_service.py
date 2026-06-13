# services/dashboard_service.py
#
# Assembles the final dashboard payload dict that gets written to Firebase
# at /patients/{id}/dashboard/current.
#
# This payload is read directly by the TypeScript frontend (FirebaseService.ts)
# and mapped to the DashboardPayload interface (DashboardPayload.ts).
#
# All field names here must match the DashboardPayload TypeScript interface.
#
# Source priority for verified_hr:
#   1. ECG-verified HR (ECGAnalyzer) — most reliable, when ECG sensor present
#   2. Wrist sensor HR (MAX30100)    — fallback for devices without ECG (e.g. Patient_02)
#   3. None                          — no data available
#
# quality field values:
#   "good" / "fair" / "poor"  — ECG present and analyzed
#   "wrist_only"               — no ECG sensor, HR from MAX30100 only
#   "invalid"                  — no data at all

from models import DashboardStatus, ECGAnalysisResult, WristData


class DashboardService:
    def build_payload(
        self,
        status: DashboardStatus,
        ecg_result: ECGAnalysisResult | None,
        wrist: WristData | None = None,
    ) -> dict:
        """
        Builds the Firebase payload dict from the alert status, ECG result,
        and wrist sensor data.

        Args:
            status:     Output of AlertService.evaluate() — vitals + alert level
            ecg_result: Output of ECGAnalyzer.analyze(), or None if ECG unavailable
            wrist:      Sanitized wrist data, used as HR fallback when ECG absent

        Returns:
            Dict ready to be written to Firebase via firebase_client.save_dashboard_data()
        """
        # verified_hr: prefer ECG, fall back to wrist HR (e.g. Patient_02 / MAX30100 only)
        verified_hr = status.verified_hr  # set by AlertService from ecg_result
        if verified_hr is None and wrist is not None:
            verified_hr = wrist.heart_rate

        # quality and confidence: reflect actual data source
        if ecg_result is not None:
            quality = ecg_result.quality
            confidence = ecg_result.confidence
            source_type = ecg_result.source_type
            sampling_rate = ecg_result.sampling_rate
            missing_samples = ecg_result.missing_samples
            ecg_filtered = ecg_result.filtered_signal
            ecg_peaks = ecg_result.peaks
        elif verified_hr is not None:
            # Wrist sensor only — HR is valid but no ECG pipeline ran
            quality = "wrist_only"
            confidence = 0.6  # moderate confidence: single optical sensor
            source_type = "wrist_sensor"
            sampling_rate = None
            missing_samples = 0
            ecg_filtered = []
            ecg_peaks = []
        else:
            # No data at all
            quality = "invalid"
            confidence = 0.0
            source_type = "unknown"
            sampling_rate = None
            missing_samples = 0
            ecg_filtered = []
            ecg_peaks = []

        return {
            # Alert status (from AlertService)
            "status": status.status,
            "message": status.message,
            # Vital signs (from wrist sensor)
            "heart_rate": status.heart_rate,
            "spo2": status.spo2,
            "temp": status.temperature,
            "timestamp": status.timestamp,
            # Best available HR — ECG if present, wrist otherwise
            "verified_hr": verified_hr,
            # ECG / signal quality fields
            "ecg_filtered": ecg_filtered,
            "ecg_peaks": ecg_peaks,
            "confidence": confidence,
            "quality": quality,
            "source_type": source_type,
            "sampling_rate": sampling_rate,
            "missing_samples": missing_samples,
        }
