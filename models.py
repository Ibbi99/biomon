from dataclasses import dataclass, field
from typing import List, Optional

# Data models (dataclasses) shared across the entire Python backend.
# These represent the data structures passed between services,
# analyzers, and Firebase client.
# @author Cristina Vedinas


@dataclass
class WristData:
    """
    Sanitized data from the wrist sensor (MAX30100 + DHT11 or simulated).
    Produced by WristAnalyzer.sanitize() after validating raw Firebase values.
    Invalid or out-of-range values are set to None.
    """

    heart_rate: Optional[float]  # BPM (None if invalid or missing)
    spo2: Optional[float]  # Oxygen saturation % (None if invalid or missing)
    temperature: Optional[float]  # Body temperature °C (None if invalid or missing)
    timestamp: int  # Unix timestamp in milliseconds


@dataclass
class ChestData:
    """
    Raw ECG batch from the chest sensor (AD8232 or simulated).
    Produced by PatientService before passing to ECGAnalyzer.
    """

    ecg_batch: List[float]  # Raw ADC sample values
    timestamp: int  # Unix timestamp in milliseconds
    patient_id: str = ""
    source_type: str = "unknown"  # "simulated" | "firebase_real"
    sampling_rate: Optional[float] = None  # Hz (e.g. 200)
    expected_batch_size: Optional[int] = (
        None  # Expected number of samples (for missing sample detection)
    )
    missing_samples: int = 0  # Samples dropped during transmission


@dataclass
class ECGAnalysisResult:
    """
    Output of ECGAnalyzer.analyze().
    Contains the filtered signal, detected R-peaks, heart rate, and quality metrics.
    """

    filtered_signal: List[
        float
    ]  # Signal after normalization, filtering, and baseline removal
    peaks: List[int]  # Sample indices of detected R-peaks
    verified_hr: Optional[float]  # Heart rate calculated from RR intervals (BPM)
    confidence: float  # Analysis confidence score (0.0 – 1.0)
    timestamp: int  # Unix timestamp in milliseconds
    quality: str = "unknown"  # "good" | "fair" | "poor" | "too_short" | "invalid"
    source_type: str = "unknown"  # "simulated" | "firebase_real"
    sampling_rate: Optional[float] = None
    missing_samples: int = 0


@dataclass
class DashboardStatus:
    """
    Output of AlertService.evaluate().
    Summarizes the patient's current alert level and vital signs.
    Passed to DashboardService.build_payload() to produce the Firebase payload.
    """

    status: str  # "STABLE" | "WARNING" | "CRITICAL"
    message: str  # Human-readable alert description
    heart_rate: Optional[float]  # From wrist sensor
    spo2: Optional[float]  # From wrist sensor
    temperature: Optional[float]  # From wrist sensor
    verified_hr: Optional[float]  # From ECG analysis (more reliable than wrist HR)
    timestamp: int  # Most recent timestamp across wrist and ECG data


@dataclass
class PatientState:
    """
    Holds the most recent processed state for a single patient.
    Currently used within a single processing cycle — not persisted between cycles.
    """

    patient_id: str
    last_wrist: Optional[WristData] = None
    last_ecg_result: Optional[ECGAnalysisResult] = None
    last_status: Optional[DashboardStatus] = None
    wrist_history: List[WristData] = field(default_factory=list)
