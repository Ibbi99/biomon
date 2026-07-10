# BioMon – Medical Monitoring System

BioMon is a medical monitoring application that collects physiological data from an ESP32-based device equipped with a MAX30100 pulse oximeter sensor. The system processes the data, stores it in Firebase, and displays it through a web interface.

## Project Structure

```
biomon/
│
├── app.py
├── start.bat
├── requirements.txt
├── simulators/
├── ui/
│   ├── package.json
│   └── ...
└── arduino/
    └── ...
```

---

## Requirements

Before running the project, install the following software:

- Python 3.11 or newer
- Node.js (LTS version, includes npm)
- Arduino IDE 2.x
- Git (optional)

---

## Python Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Example `requirements.txt`:

```text
firebase_admin==7.2.0
matplotlib==3.11.0
numpy==2.5.1
wfdb==4.3.1
```

---

## Frontend Setup

Navigate to the UI folder and install the dependencies:

```bash
cd ui
npm install
```

---

## Arduino Setup

Open the Arduino project in Arduino IDE and install the required library:

- MAX30100 Pulse Oximeter Library

The following libraries are included with the ESP32 Arduino framework and do not need to be installed separately:

- WiFi
- HTTPClient
- Wire
- time

After installing the required library, upload the sketch to the ESP32 board.

---

## Running the Application

After completing the installation steps:

1. Connect the ESP32 device.
2. Run:

```bash
start.bat
```

This script starts:

- the patient simulator;
- the Python backend;
- the web interface;
- opens the application in the browser.

---

## Technologies Used

- Python
- Firebase Firestore
- NumPy
- Matplotlib
- WFDB
- React + TypeScript
- Vite
- ESP32
- MAX30100 Pulse Oximeter

---

## Notes

If the frontend is started for the first time, execute:

```bash
cd ui
npm install
```

before running `start.bat`.
