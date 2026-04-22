# services/dashboard_service.py
#
# Assembles the final dashboard payload dict that gets written to Firebase
# at /patients/{id}/dashboard/current.
#
# This payload is read directly by the TypeScript frontend (FirebaseService.ts)
# and mapped to the DashboardPayload interface (DashboardPayload.ts).
#
# All field names here must match the DashboardPayload TypeScript interface.

from models import DashboardStatus, ECGAnalysisResult


class DashboardService:
    def build_payload(
        self,
        status: DashboardStatus,
        ecg_result: ECGAnalysisResult | None,
    ) -> dict:
        """
        Builds the Firebase payload dict from the alert status and ECG result.

        Args:
            status:     Output of AlertService.evaluate() — vitals + alert level
            ecg_result: Output of ECGAnalyzer.analyze(), or None if ECG was unavailable

        Returns:
            Dict ready to be written to Firebase via firebase_client.save_dashboard_data()
        """
        return {
            # Alert status fields (from AlertService)
            "status": status.status,           # "STABLE" | "WARNING" | "CRITICAL"
            "message": status.message,         # Human-readable alert description

            # Vital signs (from wrist sensor)
            "heart_rate": status.heart_rate,   # BPM from MAX30100 / simulated
            "spo2": status.spo2,               # Oxygen saturation %
            "temp": status.temperature,        # Body temperature °C
            "timestamp": status.timestamp,     # Most recent timestamp (ms)

            # ECG-verified heart rate (more reliable than wrist HR when available)
            "verified_hr": status.verified_hr,

            # ECG analysis fields (empty/default if ECG was not processed)
            "ecg_filtered": ecg_result.filtered_signal if ecg_result else [],
            "ecg_peaks": ecg_result.peaks if ecg_result else [],
            "confidence": ecg_result.confidence if ecg_result else 0.0,
            "quality": ecg_result.quality if ecg_result else "invalid",
            "source_type": ecg_result.source_type if ecg_result else "unknown",
            "sampling_rate": ecg_result.sampling_rate if ecg_result else None,
            "missing_samples": ecg_result.missing_samples if ecg_result else 0,
        }