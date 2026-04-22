# analyzer/ecg_analyzer.py
#
# Analyzes a raw ECG batch and extracts clinically meaningful information.
#
# Processing pipeline (applied in analyze()):
#   1. Normalize        — zero-mean, unit-variance (z-score normalization)
#   2. MedianFilter     — remove impulse noise / spikes
#   3. BaselineRemoval  — remove slow drift (breathing, electrode movement)
#   4. MovingAverage    — smooth high-frequency noise
#   5. Enhance QRS      — differentiate + square + integrate to amplify R-peaks
#   6. Detect R-peaks   — threshold-based peak detection with refractory period
#   7. Calculate HR     — from average RR interval (60 / avg_RR)
#   8. Calculate confidence — weighted score based on RR consistency, duration, completeness
#
# Output: ECGAnalysisResult with filtered signal, peaks, verified HR, and quality metrics.

from typing import List

from config import (
    DEFAULT_ECG_SAMPLING_RATE,
    ECG_BASELINE_WINDOW,
    ECG_SMOOTHING_WINDOW,
    ECG_MIN_VALID_SAMPLES,
    ECG_MIN_RR_SEC,
    ECG_MAX_RR_SEC,
    ECG_REFRACTORY_PERIOD_SEC,
)
from models import ChestData, ECGAnalysisResult
from analyzer.filters import BaselineRemovalFilter, MovingAverageFilter, MedianFilter


class ECGAnalyzer:
    def __init__(self):
        self.baseline_filter = BaselineRemovalFilter()
        self.smoothing_filter = MovingAverageFilter()
        self.median_filter = MedianFilter()

    def analyze(self, chest_data: ChestData) -> ECGAnalysisResult:
        """
        Runs the full ECG analysis pipeline on a ChestData batch.

        Returns ECGAnalysisResult with quality="too_short" if the batch
        has fewer than ECG_MIN_VALID_SAMPLES samples.

        Args:
            chest_data: Validated ECG batch from PatientService

        Returns:
            ECGAnalysisResult with filtered signal, peaks, HR, confidence, and quality
        """
        sampling_rate = chest_data.sampling_rate or DEFAULT_ECG_SAMPLING_RATE
        signal = chest_data.ecg_batch[:]

        if len(signal) < ECG_MIN_VALID_SAMPLES:
            return ECGAnalysisResult(
                filtered_signal=signal,
                peaks=[],
                verified_hr=None,
                confidence=0.0,
                timestamp=chest_data.timestamp,
                quality="too_short",
                source_type=chest_data.source_type,
                sampling_rate=sampling_rate,
                missing_samples=chest_data.missing_samples,
            )

        # Filter pipeline
        signal = self._normalize(signal)
        signal = self.median_filter.apply(signal, window=3)
        signal = self.baseline_filter.apply(signal, window=ECG_BASELINE_WINDOW)
        signal = self.smoothing_filter.apply(signal, window=ECG_SMOOTHING_WINDOW)

        # QRS enhancement and peak detection
        enhanced = self._enhance_qrs(signal, sampling_rate)
        peaks = self._detect_r_peaks(enhanced, sampling_rate)
        verified_hr = self._calculate_hr_from_peaks(peaks, sampling_rate)
        confidence = self._calculate_confidence(
            peaks=peaks,
            hr=verified_hr,
            signal_len=len(signal),
            missing_samples=chest_data.missing_samples,
            expected_batch_size=chest_data.expected_batch_size,
            sampling_rate=sampling_rate,
        )

        quality = "good" if confidence >= 0.75 else "fair" if confidence >= 0.45 else "poor"

        return ECGAnalysisResult(
            filtered_signal=signal,
            peaks=peaks,
            verified_hr=verified_hr,
            confidence=confidence,
            timestamp=chest_data.timestamp,
            quality=quality,
            source_type=chest_data.source_type,
            sampling_rate=sampling_rate,
            missing_samples=chest_data.missing_samples,
        )

    def _normalize(self, signal: List[float]) -> List[float]:
        """
        Z-score normalization: subtracts mean and divides by standard deviation.
        Ensures the signal has zero mean and unit variance regardless of ADC scale.
        """
        if not signal:
            return []
        mean_val = sum(signal) / len(signal)
        variance = sum((x - mean_val) ** 2 for x in signal) / len(signal)
        std_val = max(variance ** 0.5, 1e-6)
        return [(x - mean_val) / std_val for x in signal]

    def _enhance_qrs(self, signal: List[float], sampling_rate: float) -> List[float]:
        """
        Pan-Tompkins-inspired QRS enhancement:
          1. Differentiate  — emphasizes steep slopes (R-wave upstroke)
          2. Square         — amplifies large values, suppresses small ones
          3. Integrate      — smooths the result over a ~80ms window

        The output is not the ECG signal — it's an envelope used only for
        peak detection. The original filtered signal is what gets returned
        in the ECGAnalysisResult.
        """
        if len(signal) < 2:
            return signal[:]

        diff = [0.0]
        for i in range(1, len(signal)):
            diff.append(signal[i] - signal[i - 1])

        squared = [x * x for x in diff]

        window = max(1, int(0.08 * sampling_rate))  # ~80ms integration window
        integrated = []
        for i in range(len(squared)):
            start = max(0, i - window + 1)
            chunk = squared[start:i + 1]
            integrated.append(sum(chunk) / len(chunk))

        return integrated

    def _detect_r_peaks(self, signal: List[float], sampling_rate: float) -> List[int]:
        """
        Detects R-peaks in the QRS-enhanced signal using adaptive thresholding.

        Threshold = mean + 0.8 * std_dev of the enhanced signal.
        A refractory period (ECG_REFRACTORY_PERIOD_SEC) prevents double-detection
        within a single QRS complex. If a higher peak is found within the
        refractory period, it replaces the previous one.

        Returns:
            List of sample indices where R-peaks were detected
        """
        if len(signal) < 3:
            return []

        mean_val = sum(signal) / len(signal)
        variance = sum((x - mean_val) ** 2 for x in signal) / len(signal)
        std_val = variance ** 0.5

        threshold = mean_val + 0.8 * std_val
        refractory_samples = int(ECG_REFRACTORY_PERIOD_SEC * sampling_rate)

        peaks = []
        last_peak = -refractory_samples

        for i in range(1, len(signal) - 1):
            is_peak = (
                signal[i] > threshold and
                signal[i] > signal[i - 1] and
                signal[i] >= signal[i + 1]
            )
            if not is_peak:
                continue

            if i - last_peak >= refractory_samples:
                peaks.append(i)
                last_peak = i
            elif peaks and signal[i] > signal[peaks[-1]]:
                # Replace with higher peak within the same QRS complex
                peaks[-1] = i
                last_peak = i

        return peaks

    def _calculate_hr_from_peaks(self, peaks: List[int], sampling_rate: float) -> float | None:
        """
        Calculates heart rate from the average RR interval between detected peaks.
        Only intervals within the physiologically valid range are used
        (ECG_MIN_RR_SEC to ECG_MAX_RR_SEC, corresponding to ~30–200 BPM).

        Returns:
            Heart rate in BPM, or None if fewer than 2 valid peaks were found
        """
        if len(peaks) < 2:
            return None

        rr_intervals = []
        for i in range(1, len(peaks)):
            rr_sec = (peaks[i] - peaks[i - 1]) / sampling_rate
            if ECG_MIN_RR_SEC <= rr_sec <= ECG_MAX_RR_SEC:
                rr_intervals.append(rr_sec)

        if not rr_intervals:
            return None

        avg_rr = sum(rr_intervals) / len(rr_intervals)
        return 60.0 / avg_rr

    def _calculate_confidence(
        self,
        peaks: List[int],
        hr: float | None,
        signal_len: int,
        missing_samples: int,
        expected_batch_size: int | None,
        sampling_rate: float,
    ) -> float:
        """
        Calculates a confidence score (0.0 – 1.0) for the ECG analysis result.

        Weighted components:
          0.40 — RR interval consistency (low variance = regular heartbeat)
          0.25 — Signal duration (longer batches give more reliable HR estimates)
          0.20 — Data completeness (fewer missing samples = better signal)
          0.15 — HR plausibility (40–180 BPM is the expected physiological range)

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if hr is None or len(peaks) < 2:
            return 0.0

        rr = [(peaks[i] - peaks[i - 1]) / sampling_rate for i in range(1, len(peaks))]
        rr = [x for x in rr if ECG_MIN_RR_SEC <= x <= ECG_MAX_RR_SEC]
        if not rr:
            return 0.0

        avg_rr = sum(rr) / len(rr)
        rr_std = (sum((x - avg_rr) ** 2 for x in rr) / len(rr)) ** 0.5
        consistency = max(0.0, 1.0 - rr_std / max(avg_rr, 1e-6))

        duration_sec = signal_len / sampling_rate
        duration_score = min(1.0, duration_sec / 5.0)

        missing_ratio = 0.0
        if expected_batch_size and expected_batch_size > 0:
            missing_ratio = missing_samples / expected_batch_size
        missing_score = max(0.0, 1.0 - missing_ratio)

        hr_score = 1.0 if 40 <= hr <= 180 else 0.4

        confidence = (
            0.4 * consistency +
            0.25 * duration_score +
            0.2 * missing_score +
            0.15 * hr_score
        )
        return max(0.0, min(1.0, confidence))