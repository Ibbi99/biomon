# analyzer/filters.py
#
# Signal processing filters used by ECGAnalyzer to clean the raw ECG signal
# before R-peak detection.
#
# Applied in this order inside ECGAnalyzer.analyze():
#   1. MedianFilter        — removes short spikes and impulse noise
#   2. BaselineRemovalFilter — removes slow drift (breathing artifacts, electrode movement)
#   3. MovingAverageFilter — smooths high-frequency noise

from typing import List


class MovingAverageFilter:
    """
    Smooths the signal by replacing each sample with the average
    of itself and the preceding (window-1) samples.

    Effect: reduces high-frequency noise at the cost of slight signal blurring.
    Used after baseline removal to smooth the filtered signal.
    """

    def apply(self, signal: List[float], window: int = 5) -> List[float]:
        """
        Args:
            signal: Input ECG samples
            window: Number of samples to average (default 5, set by ECG_SMOOTHING_WINDOW)

        Returns:
            Smoothed signal of the same length
        """
        if not signal or window <= 1:
            return signal[:]

        result = []
        for i in range(len(signal)):
            start = max(0, i - window + 1)
            chunk = signal[start : i + 1]
            result.append(sum(chunk) / len(chunk))
        return result


class MedianFilter:
    """
    Replaces each sample with the median of its surrounding window.

    Effect: removes impulse noise and short spikes without blurring edges.
    Applied first, before baseline removal.
    """

    def apply(self, signal: List[float], window: int = 3) -> List[float]:
        """
        Args:
            signal: Input ECG samples
            window: Odd number of samples to take the median over (default 3)

        Returns:
            Filtered signal of the same length
        """
        if not signal or window <= 1:
            return signal[:]

        result = []
        half = window // 2

        for i in range(len(signal)):
            start = max(0, i - half)
            end = min(len(signal), i + half + 1)
            chunk = sorted(signal[start:end])
            result.append(chunk[len(chunk) // 2])
        return result


class BaselineRemovalFilter:
    """
    Removes slow baseline drift by subtracting a local moving average (the baseline).

    Effect: centers the signal around zero, eliminating low-frequency artifacts
    caused by breathing, patient movement, or electrode contact changes.
    Applied after MedianFilter, before MovingAverageFilter.
    """

    def apply(self, signal: List[float], window: int = 15) -> List[float]:
        """
        Args:
            signal: Input ECG samples
            window: Window size for baseline estimation (default 15, set by ECG_BASELINE_WINDOW)
                    Should be larger than one cardiac cycle to avoid distorting the ECG shape.

        Returns:
            Baseline-corrected signal of the same length
        """
        if not signal:
            return []

        result = []
        for i in range(len(signal)):
            start = max(0, i - window + 1)
            chunk = signal[start : i + 1]
            baseline = sum(chunk) / len(chunk)
            result.append(signal[i] - baseline)
        return result
