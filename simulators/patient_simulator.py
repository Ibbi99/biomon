import math
import os
import random
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from firebase_client import FirebaseClient
from simulators.scenarios import ScenarioFactory
from firebase_admin import db

# Simulates Patient_01 by generating realistic vital signs and ECG data
# and pushing them to Firebase every second.
# @author Cristina Vedinas
#
# The Python processor (app.py) then reads this data and processes it
# exactly like it would for a real ESP32 patient.
#
# Scenario cycling: every 15 seconds the simulator switches to the next scenario.
# Scenarios: normal -> tachycardia -> hypoxia -> fever -> cardiac_arrest -> (repeat)
#
# Firebase paths written by this simulator:
#   /patients/Patient_01/live/vitals    <- HR, SpO2, Temp
#   /patients/Patient_01/live/ecg       <- ECG batch (200 samples at 200 Hz)
#   /patients/Patient_01/history/vitals <- append-only history


ECG_BATCH_SIZE = 400  # Samples per batch (matches ESP32 firmware)
ECG_SAMPLING_RATE = 200  # Hz (matches ESP32 firmware)


def build_vitals_payload(data: dict) -> dict:
    """
    Builds the vitals dict written to /live/vitals.
    Uses camelCase field names to match the ESP32 firmware format.
    WristAnalyzer handles both heartRate and heart_rate via its fallback logic.
    """
    return {
        "heartRate": data["heart_rate"],
        "spo2": data["spo2"],
        "temperature": data["temp"],
        "source_type": "simulated",
        "timestamp": ScenarioFactory.now_ms(),
    }


def generate_ecg_batch(
    hr: float, points: int = ECG_BATCH_SIZE, sampling_rate: float = ECG_SAMPLING_RATE
) -> list[float]:
    """
    Generates a synthetic ECG signal with realistic P-QRS-T morphology.

    Each wave component is modeled using a Gaussian function:
      - P wave : atrial depolarization at ~15% of the cardiac cycle
      - Q wave : small negative deflection before the R peak (~28%)
      - R wave : tall positive spike (main QRS peak) at ~31%
      - S wave : small negative deflection after the R peak (~34%)
      - T wave : ventricular repolarization at ~55% of the cycle

    Gaussian noise (std=0.04) is added to simulate electrode and motion artifacts.

    The signal dynamic range (~1.5-2.0) exceeds the PatientService viability
    threshold of 0.5, so it always passes the _is_viable_ecg_batch() check.

    Args:
        hr:           Heart rate in BPM (used to calculate samples per beat)
        points:       Total number of samples to generate
        sampling_rate: Sampling frequency in Hz

    Returns:
        List of float amplitude values
    """
    hr = max(hr, 30.0)  # Avoid division by zero for cardiac_arrest scenario (HR=0)
    samples_per_beat = int(sampling_rate * 60.0 / hr)
    ecg = []

    for i in range(points):
        phase = (i % samples_per_beat) / samples_per_beat  # 0.0 to 1.0 within one beat

        # P wave — atrial depolarization
        p_wave = (
            0.25 * math.exp(-((phase - 0.15) ** 2) / (2 * 0.007**2))
            if 0.05 < phase < 0.25
            else 0.0
        )

        # QRS complex — ventricular depolarization
        q_wave = -0.15 * math.exp(-((phase - 0.28) ** 2) / (2 * 0.003**2))
        r_wave = 1.50 * math.exp(-((phase - 0.31) ** 2) / (2 * 0.003**2))
        s_wave = -0.25 * math.exp(-((phase - 0.34) ** 2) / (2 * 0.003**2))
        qrs = q_wave + r_wave + s_wave

        # T wave — ventricular repolarization
        t_wave = 0.35 * math.exp(-((phase - 0.55) ** 2) / (2 * 0.025**2))

        # Gaussian noise — simulates electrode and motion artifacts
        noise = random.gauss(0, 0.04)

        ecg.append(p_wave + qrs + t_wave + noise)

    return ecg


def build_ecg_payload(hr: float) -> dict:
    """Builds the ECG dict written to /live/ecg."""
    return {
        "ecg_batch": generate_ecg_batch(hr),
        "expected_batch_size": ECG_BATCH_SIZE,
        "sampling_rate": ECG_SAMPLING_RATE,
        "source_type": "simulated",
        "timestamp": ScenarioFactory.now_ms(),
    }


def push_live_data(patient_id: str, vitals: dict, ecg: dict) -> None:
    """Writes vitals and ECG to /patients/{id}/live in a single Firebase set() call."""
    db.reference(f"/patients/{patient_id}/live").set({"vitals": vitals, "ecg": ecg})


def push_history_vitals(patient_id: str, payload: dict) -> None:
    """Appends a vitals snapshot to /patients/{id}/history/vitals (Firebase push key)."""
    db.reference(f"/patients/{patient_id}/history/vitals").push(payload)


def main():
    FirebaseClient()  # Initialize Firebase connection

    scenarios = [
        ("normal", ScenarioFactory.normal),
        ("tachycardia", ScenarioFactory.tachycardia),
        ("hypoxia", ScenarioFactory.hypoxia),
        ("fever", ScenarioFactory.fever),
        ("cardiac_arrest", ScenarioFactory.cardiac_arrest),
    ]

    patient_id = "Patient_01"
    index = 0  # Current scenario index
    counter = 0  # Seconds elapsed in current scenario

    print("=== PATIENT SIMULATOR STARTED ===")

    while True:
        name, scenario_fn = scenarios[index]
        data = scenario_fn()

        vitals_payload = build_vitals_payload(data)
        ecg_payload = build_ecg_payload(data["heart_rate"])

        push_live_data(patient_id, vitals_payload, ecg_payload)
        push_history_vitals(patient_id, vitals_payload)

        ecg_batch = ecg_payload["ecg_batch"]
        dynamic_range = max(ecg_batch) - min(ecg_batch)
        print(
            f"[SIM] {patient_id} scenario={name} "
            f"HR={data['heart_rate']} SpO2={data['spo2']} Temp={data['temp']} "
            f"ecg_range={dynamic_range:.2f}"
        )

        time.sleep(1)
        counter += 1

        # Switch to the next scenario after 15 seconds
        if counter >= 15:
            counter = 0
            index = (index + 1) % len(scenarios)


if __name__ == "__main__":
    main()
