import time
from models import WristData

# Sanitizes raw wrist sensor data from Firebase before it enters the pipeline.
# Handles both camelCase (ESP32 / simulator) and snake_case field names.
# Validates values against physiologically plausible ranges — out-of-range
# values are set to None rather than passed downstream as bad data.
# @author Cristina Vedinas
#
# Valid ranges:
#   HR:   20 – 200 BPM  (MAX30100 returns 255 when no finger — reject it)
#   SpO2: 50 – 100 %
#   Temp: 10 – 45 °C    (HTU21D measures ambient air — not body temperature)
#                        Lower bound 10°C covers cold environments.
#                        Upper bound 45°C covers warm skin proximity.
#
# Note on temperature source:
#   Patient_02 uses HTU21D (ambient sensor), not a body-contact thermometer.
#   The sensor reads air temperature near the wrist unit (~25–35°C typical).
#   This is documented as ambient_temp in the dashboard payload.
#
# Stale data detection:
#   ESP32 timestamps are Unix milliseconds obtained via NTP (configTime).
#   If the timestamp looks like a relative millis() value (< year 2020 epoch),
#   staleness check is skipped to avoid false rejections.
#   Otherwise, data older than STALE_THRESHOLD_MS (15 seconds) is rejected.


STALE_THRESHOLD_MS = 15_000

# Unix ms for 2020-01-01 00:00:00 UTC — used to detect relative timestamps
EPOCH_2020_MS = 1_577_836_800_000


class WristAnalyzer:
    def sanitize(self, raw: dict) -> WristData:
        """
        Converts a raw Firebase vitals dict into a validated WristData object.

        Accepts both naming conventions:
          - "heart_rate" (snake_case) / "heartRate" (camelCase from ESP32)
          - "temperature" / "temp"

        Returns WristData with all None values if data is stale (> 15s old).
        """
        timestamp = self._to_int(raw.get("timestamp"))

        # Stale data check
        # Skip if timestamp looks like ESP32 relative millis() (before year 2020)
        now_ms = int(time.time() * 1000)
        if timestamp > EPOCH_2020_MS:
            age_ms = now_ms - timestamp
            if age_ms > STALE_THRESHOLD_MS:
                age_sec = age_ms / 1000
                print(
                    f"[WristAnalyzer] Stale data ({age_sec:.1f}s old) — treating vitals as missing"
                )
                return WristData(
                    heart_rate=None,
                    spo2=None,
                    temperature=None,
                    timestamp=timestamp,
                )
        else:
            # Relative timestamp from ESP32 millis() — cannot check staleness
            print(
                f"[WristAnalyzer] Relative timestamp detected ({timestamp}ms) — skipping stale check"
            )

        hr = self._to_float(raw.get("heart_rate") or raw.get("heartRate"))
        spo2 = self._to_float(raw.get("spo2"))
        temp = self._to_float(raw.get("temp") or raw.get("temperature"))

        # Reject physiologically impossible values
        # HR: MAX30100 returns 255 when no finger is detected
        if hr is not None and not (20 <= hr <= 200):
            hr = None
        if spo2 is not None and not (50 <= spo2 <= 100):
            spo2 = None
        # Temp: HTU21D ambient range — 10°C (cold room) to 45°C (warm near skin)
        if temp is not None and not (10.0 <= temp <= 45.0):
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
