# simulators/scenarios.py
#
# Defines clinical scenarios for Patient_01 (virtual patient).
# Each scenario returns a dict with heart_rate, spo2, and temp values
# that simulate a specific medical condition.
#
# Used by patient_simulator.py, which cycles through scenarios every 15 seconds.
#
# Scenarios:
#   normal         — healthy baseline (HR 68-82, SpO2 97-99, Temp 36.4-36.9)
#   tachycardia    — elevated heart rate (HR 120-145)   -> WARNING
#   hypoxia        — low oxygen saturation (SpO2 82-89) -> WARNING / CRITICAL
#   fever          — elevated temperature (Temp 38.1-39.5) -> WARNING / CRITICAL
#   cardiac_arrest — HR=0, critically low SpO2          -> CRITICAL

import random
import time


class ScenarioFactory:

    @staticmethod
    def normal() -> dict:
        """Healthy adult at rest."""
        return {
            "heart_rate": random.randint(68, 82),
            "spo2": random.randint(97, 99),
            "temp": round(random.uniform(36.4, 36.9), 1),
        }

    @staticmethod
    def tachycardia() -> dict:
        """Elevated heart rate — triggers WARNING (HR > 120 BPM)."""
        return {
            "heart_rate": random.randint(120, 145),
            "spo2": random.randint(95, 98),
            "temp": round(random.uniform(36.7, 37.3), 1),
        }

    @staticmethod
    def hypoxia() -> dict:
        """Low oxygen saturation — triggers WARNING (SpO2 < 92) or CRITICAL (SpO2 < 88)."""
        return {
            "heart_rate": random.randint(95, 120),
            "spo2": random.randint(82, 89),
            "temp": round(random.uniform(36.5, 37.2), 1),
        }

    @staticmethod
    def fever() -> dict:
        """Elevated temperature — triggers WARNING (>= 38 C) or CRITICAL (>= 39 C)."""
        return {
            "heart_rate": random.randint(90, 110),
            "spo2": random.randint(95, 98),
            "temp": round(random.uniform(38.1, 39.5), 1),
        }

    @staticmethod
    def cardiac_arrest() -> dict:
        """
        Simulated cardiac arrest — HR=0, critically low SpO2.
        HR=0 is rejected by WristAnalyzer (below the minimum of 20 BPM),
        so heart rate shows as None / '--' in the dashboard. This is intentional.
        """
        return {
            "heart_rate": 0,
            "spo2": random.randint(60, 80),
            "temp": round(random.uniform(35.5, 36.5), 1),
        }

    @staticmethod
    def now_ms() -> int:
        """Returns the current Unix timestamp in milliseconds."""
        return int(time.time() * 1000)