from config import (
    ALERT_HR_HIGH,
    ALERT_HR_LOW,
    ALERT_SPO2_CRITICAL,
    ALERT_SPO2_LOW,
    ALERT_TEMP_CRITICAL,
    ALERT_TEMP_HIGH,
)
from models import DashboardStatus, ECGAnalysisResult, WristData

# Evaluates patient vitals against clinical thresholds and returns
# an alert status (STABLE / WARNING / CRITICAL) with a descriptive message.
# @author Cristina Vedinas
#
# Priority order (highest severity checked first):
#   CRITICAL: SpO2 < 88%, HR < 35 or > 160, Temp >= 39°C
#   WARNING:  SpO2 < 92%, HR < 50 or > 120, Temp >= 38°C
#   STABLE:   all values within normal range, or no data available
#
# For heart rate, the ECG-verified HR is preferred over the wrist sensor HR
# when available, as it is more reliable.


class AlertService:
    def evaluate(
        self,
        wrist: WristData | None,
        ecg_result: ECGAnalysisResult | None,
    ) -> DashboardStatus:
        """
        Evaluates current vitals and returns a DashboardStatus with alert level.

        Args:
            wrist:      Sanitized wrist sensor data (HR, SpO2, Temp), or None
            ecg_result: ECG analysis result (verified HR, confidence), or None

        Returns:
            DashboardStatus with status, message, all vital values, and timestamp
        """
        timestamp = 0
        hr = None
        spo2 = None
        temp = None
        verified_hr = None

        if wrist:
            timestamp = wrist.timestamp
            hr = wrist.heart_rate
            spo2 = wrist.spo2
            temp = wrist.temperature

        if ecg_result:
            # Use the most recent timestamp across both data sources
            timestamp = max(timestamp, ecg_result.timestamp)
            verified_hr = ecg_result.verified_hr

        status = "STABLE"
        message = "Patient stable"

        # Prefer ECG-verified HR over wrist HR for alert evaluation
        heart_rate_to_use = verified_hr if verified_hr is not None else hr

        # Evaluate in order from most critical to least critical
        if spo2 is not None and spo2 < ALERT_SPO2_CRITICAL:
            status = "CRITICAL"
            message = "Critical oxygen saturation"
        elif heart_rate_to_use is not None and (
            heart_rate_to_use < 35 or heart_rate_to_use > 160
        ):
            status = "CRITICAL"
            message = "Critical heart rate"
        elif temp is not None and temp >= ALERT_TEMP_CRITICAL:
            status = "CRITICAL"
            message = "Critical temperature"
        elif spo2 is not None and spo2 < ALERT_SPO2_LOW:
            status = "WARNING"
            message = "Low oxygen saturation"
        elif heart_rate_to_use is not None and (
            heart_rate_to_use < ALERT_HR_LOW or heart_rate_to_use > ALERT_HR_HIGH
        ):
            status = "WARNING"
            message = "Abnormal heart rate"
        elif temp is not None and temp >= ALERT_TEMP_HIGH:
            status = "WARNING"
            message = "Elevated temperature"

        return DashboardStatus(
            status=status,
            message=message,
            heart_rate=hr,
            spo2=spo2,
            temperature=temp,
            verified_hr=verified_hr,
            timestamp=timestamp,
        )
