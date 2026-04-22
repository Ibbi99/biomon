# analyzer/wrist_analyzer.py
#
# Sanitizes raw wrist sensor data from Firebase before it enters the pipeline.
# Handles both camelCase (ESP32 / simulator) and snake_case field names.
# Validates values against physiologically plausible ranges — out-of-range
# values are set to None rather than passed downstream as bad data.
#
# Valid ranges:
#   HR:   20 – 240 BPM
#   SpO2: 50 – 100 %
#   Temp: 30 – 45 °C

from models import WristData


class WristAnalyzer:
    def sanitize(self, raw: dict) -> WristData:
        """
        Converts a raw Firebase vitals dict into a validated WristData object.

        Accepts both naming conventions:
          - "heart_rate" (snake_case, from Python models)
          - "heartRate"  (camelCase, from ESP32 firmware and simulator)
          - "temperature" or "temp"

        Args:
            raw: Dict from /patients/{id}/live/vitals

        Returns:
            WristData with invalid fields set to None
        """
        hr = self._to_float(raw.get("heart_rate") or raw.get("heartRate"))
        spo2 = self._to_float(raw.get("spo2"))
        temp = self._to_float(raw.get("temp") or raw.get("temperature"))
        timestamp = self._to_int(raw.get("timestamp"))

        # Reject physiologically impossible values
        if hr is not None and not (20 <= hr <= 240):
            hr = None
        if spo2 is not None and not (50 <= spo2 <= 100):
            spo2 = None
        if temp is not None and not (30 <= temp <= 45):
            temp = None

        return WristData(
            heart_rate=hr,
            spo2=spo2,
            temperature=temp,
            timestamp=timestamp,
        )

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