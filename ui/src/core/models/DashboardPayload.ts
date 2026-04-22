// src/core/models/DashboardPayload.ts
//
// Defines the shape of the data written by the Python processor to Firebase
// at: /patients/{patientId}/dashboard/current
//
// This interface is shared by all patient pages (VirtualPatient, RealPatient)
// and by the overview page (App.ts / PatientCard).
//
// Fields populated by Python services:
//   - alert_service.py  → status, message
//   - dashboard_service.py → all fields below
//   - ecg_analyzer.py   → ecg_filtered, ecg_peaks, confidence, quality, sampling_rate

export interface DashboardPayload {
  // Alert status determined by alert_service.py based on vital thresholds
  status: "STABLE" | "WARNING" | "CRITICAL";

  // Human-readable alert description (e.g. "Critical oxygen saturation")
  message: string;

  // Vital signs from the wrist sensor (MAX30100 + DHT11 / simulated)
  heart_rate: number | null;   // BPM from wrist sensor
  spo2: number | null;         // Oxygen saturation percentage
  temp: number | null;         // Body temperature in °C
  timestamp: number;           // Unix timestamp in milliseconds

  // Heart rate verified independently by ECG peak detection (ecg_analyzer.py)
  // More reliable than the wrist sensor HR when signal quality is good
  verified_hr: number | null;

  // ECG data from the chest sensor (AD8232 / simulated)
  // Optional — only present when a valid ECG batch was processed
  ecg_filtered?: number[];     // Filtered ECG signal (normalized, baseline-removed)
  ecg_peaks?: number[];        // Indices of detected R-peaks in ecg_filtered
  confidence?: number;         // Analysis confidence score (0.0 – 1.0)
  quality?: string;            // Signal quality: "good" | "fair" | "poor" | "invalid"
  sampling_rate?: number | null; // ECG sampling rate in Hz (typically 200)
  missing_samples?: number;    // Number of samples dropped during transmission

  // Raw ECG batch before processing (not currently sent to dashboard)
  raw_ecg?: number[];
}