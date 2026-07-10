import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import wfdb
import wfdb.processing
from analyzer.ecg_analyzer import ECGAnalyzer
from models import ChestData

# Validates ecg_analyzer.py against PhysioNet MIT-BIH Arrhythmia Database.
#
# Downloads a real ECG record, runs it through our analyzer,
# and compares detected R-peaks against the clinical annotations.
# @author Cristina Vedinas
#
# Usage:
#   python scripts/validate_physionet.py
#
# Records available (MIT-BIH):
#   100 — Normal sinus rhythm
#   101 — Normal + occasional PVC
#   105 — Atrial fibrillation
#   108 — Ventricular tachycardia
#   200 — Frequent PVCs
#
# Metrics:
#   Sensitivity (Se) = TP / (TP + FN)  — how many real peaks we found
#   Precision  (PPV) = TP / (TP + FP)  — how many of our peaks are real
#   F1 score         = 2 * Se * PPV / (Se + PPV)


# ── Configuration ─────────────────────────────────────────────
RECORD_NAME = "105"  # MIT-BIH record to test
SAMPLING_RATE = 360  # MIT-BIH is 360 Hz
BATCH_SIZE = 1800  # 5 seconds of data (5 * 360)
TOLERANCE_MS = 150  # ±150ms tolerance for peak matching
TOLERANCE_SAMPLES = int(TOLERANCE_MS / 1000 * SAMPLING_RATE)

# ── Download and load record ───────────────────────────────────
print(f"=== PhysioNet Validation: MIT-BIH Record {RECORD_NAME} ===\n")
print(f"Downloading record {RECORD_NAME} from PhysioNet...")

record = wfdb.rdrecord(os.path.join("scripts", "physionet_data", RECORD_NAME))
annotation = wfdb.rdann(os.path.join("scripts", "physionet_data", RECORD_NAME), "atr")

print(f"Record loaded: {record.sig_len} samples at {record.fs} Hz")
print(f"Duration: {record.sig_len / record.fs:.1f} seconds")
print(f"Channels: {record.sig_name}")

# Use channel 0 (MLII lead — best for R-peak detection)
signal = record.p_signal[:, 0].tolist()
fs = record.fs

# Get reference R-peak annotations (beat annotations only)
beat_types = {
    "N",
    "L",
    "R",
    "B",
    "A",
    "a",
    "J",
    "S",
    "V",
    "r",
    "F",
    "e",
    "j",
    "n",
    "E",
    "/",
    "f",
    "Q",
    "?",
}
ref_peaks = [
    s for s, sym in zip(annotation.sample, annotation.symbol) if sym in beat_types
]

print(f"Reference peaks (clinical annotations): {len(ref_peaks)}")

# ── Run analysis in batches ────────────────────────────────────
analyzer = ECGAnalyzer()
all_detected_peaks = []
results = []

num_batches = len(signal) // BATCH_SIZE
print(
    f"\nAnalyzing {num_batches} batches of {BATCH_SIZE} samples ({BATCH_SIZE/fs:.1f}s each)...\n"
)

for i in range(num_batches):
    start = i * BATCH_SIZE
    end = start + BATCH_SIZE
    batch = signal[start:end]

    chest = ChestData(
        ecg_batch=batch,
        timestamp=int(start / fs * 1000),
        patient_id="physionet_test",
        source_type="physionet",
        sampling_rate=float(fs),
        expected_batch_size=BATCH_SIZE,
        missing_samples=0,
    )

    result = analyzer.analyze(chest)

    # Convert local peak indices to global sample indices
    global_peaks = [p + start for p in result.peaks]
    all_detected_peaks.extend(global_peaks)

    results.append(
        {
            "batch": i + 1,
            "verified_hr": result.verified_hr,
            "confidence": result.confidence,
            "quality": result.quality,
            "peaks_found": len(result.peaks),
        }
    )

    print(
        f"Batch {i+1:2d}/{num_batches} | " f"HR={result.verified_hr:.1f} BPM | "
        if result.verified_hr
        else f"Batch {i+1:2d}/{num_batches} | HR=None | "
        f"Confidence={result.confidence:.2f} | "
        f"Quality={result.quality} | "
        f"Peaks={len(result.peaks)}"
    )

# ── Compare detected peaks with reference ──────────────────────
print(f"\n=== Peak Detection Accuracy ===\n")

# Only compare peaks within the analyzed range
max_sample = num_batches * BATCH_SIZE
ref_in_range = [p for p in ref_peaks if p < max_sample]

TP = 0  # True Positives  — detected peak matches a reference peak
FP = 0  # False Positives — detected peak has no matching reference
FN = 0  # False Negatives — reference peak not detected

matched_ref = set()

for det_peak in all_detected_peaks:
    # Find closest reference peak within tolerance
    closest = min(ref_in_range, key=lambda r: abs(r - det_peak), default=None)
    if closest is not None and abs(closest - det_peak) <= TOLERANCE_SAMPLES:
        if closest not in matched_ref:
            TP += 1
            matched_ref.add(closest)
        else:
            FP += 1  # duplicate detection
    else:
        FP += 1

FN = len(ref_in_range) - len(matched_ref)

sensitivity = TP / (TP + FN) if (TP + FN) > 0 else 0
precision = TP / (TP + FP) if (TP + FP) > 0 else 0
f1 = (
    2 * sensitivity * precision / (sensitivity + precision)
    if (sensitivity + precision) > 0
    else 0
)

print(f"Reference peaks in range : {len(ref_in_range)}")
print(f"Detected peaks           : {len(all_detected_peaks)}")
print(f"True Positives  (TP)     : {TP}")
print(f"False Positives (FP)     : {FP}")
print(f"False Negatives (FN)     : {FN}")
print(f"\nSensitivity (Se)  : {sensitivity:.3f}  ({sensitivity*100:.1f}%)")
print(f"Precision   (PPV) : {precision:.3f}  ({precision*100:.1f}%)")
print(f"F1 Score          : {f1:.3f}  ({f1*100:.1f}%)")

# ── Per-batch summary ──────────────────────────────────────────
print(f"\n=== Per-Batch HR Summary ===\n")
valid = [r for r in results if r["verified_hr"] is not None]
if valid:
    hrs = [r["verified_hr"] for r in valid]
    print(f"Batches with valid HR : {len(valid)}/{num_batches}")
    print(f"HR range              : {min(hrs):.1f} – {max(hrs):.1f} BPM")
    print(f"HR mean               : {sum(hrs)/len(hrs):.1f} BPM")
    avg_conf = sum(r["confidence"] for r in valid) / len(valid)
    print(f"Avg confidence        : {avg_conf:.3f}")
else:
    print("No valid HR detected in any batch.")

print(f"\n=== Done ===")
