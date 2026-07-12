# BioMon – Medical Monitoring System

BioMon is a two-node IoT remote patient monitoring system built as a bachelor's thesis project (UPT, 2026). It supports two patients simultaneously:

- **Patient_01** – fully simulated in Python (no physical hardware required)
- **Patient_02** – real physical hardware, made up of two ESP32-based nodes:
  - a **wrist node** with a MAX30100 pulse oximeter and an HTU21D ambient temperature/humidity sensor
  - an **ECG node** with an AD8232 ECG sensor

The ESP32 nodes handle sensing and transmission only. All processing, analysis, and history logging is done by the Python backend, which stores data in Firebase Realtime Database and serves it to a web dashboard.

---

## Project Structure

```
biomon/
│
├── app.py
├── firebase_client.py
├── patient_service.py
├── wrist_analyzer.py
├── ecg_analyzer.py
├── models.py
├── start.bat
├── requirements.txt
├── simulators/
├── ui/
│   ├── package.json
│   └── ...
└── arduino/
    ├── wrist_node/
    └── ecg_node/
```

---

## Requirements

Before running the project, install the following software:
- Python 3.11 or newer
- Node.js (LTS version, includes npm)
- Arduino IDE 2.x
- Git (optional)

---

## Hardware

Only needed if you want to run **Patient_02** (real hardware) rather than the fully simulated Patient_01.

### Components

| Component | Used for | Notes |
|---|---|---|
| ESP32 (x2) | Main microcontroller, one per node | Wrist node + ECG node |
| AD8232 | ECG signal acquisition | Signal output on `GPIO33` |
| MAX30100 | Heart rate / pulse oximetry | Wrist node, I2C — SDA `GPIO27`, SCL `GPIO32` |
| HTU21D | Ambient temperature & humidity | Wrist node, I2C — SDA `GPIO25`, SCL `GPIO26`. Ambient only, **not** body temperature |
| Buck converter | Power regulation | Steps down 5V/7V input to 3.3V for the ESP32 |
| Breadboard / custom test board | Prototyping / final assembly | A dedicated test board is recommended — parasitic capacitance on breadboards noticeably degrades ECG signal quality |

### Wiring notes

- `GPIO12` on the ECG node is tied to GND (required for stable AD8232 readings on ESP32).
- The wrist node and ECG node are independent — each connects to WiFi and talks to the Python backend on its own; there's no direct connection between the two.

### Reproducing this project

1. Wire the sensors as described above (wrist node and ECG node are separate builds).
2. Flash the corresponding sketch from `arduino/wrist_node` or `arduino/ecg_node` onto each ESP32.
3. Set up the Python backend and point it at your own Firebase Realtime Database instance.
4. Update WiFi and Firebase credentials in both the firmware and the backend config before flashing/running.

**Note:** This is a working prototype from a bachelor's thesis, not a certified medical device. ECG signal quality is limited by the consumer-grade AD8232 module and electrodes; see the thesis for details and suggested hardware improvements (e.g. ADS1292R + Ag/AgCl electrodes).

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

Open the relevant sketch (`arduino/wrist_node` or `arduino/ecg_node`) in Arduino IDE and install the required library:
- MAX30100 Pulse Oximeter Library (wrist node only)

The following libraries are included with the ESP32 Arduino framework and do not need to be installed separately:
- WiFi
- HTTPClient
- Wire
- time

After installing the required library, upload the sketch to the corresponding ESP32 board.

---

## Running the Application

After completing the installation steps:
1. Connect the ESP32 device(s), if using Patient_02 (real hardware).
2. Run:
```bash
start.bat
```
This script starts:
- the patient simulator (for Patient_01);
- the Python backend;
- the web interface;
- opens the application in the browser.

---

## Technologies Used

- Python
- Firebase Realtime Database
- NumPy
- Matplotlib
- WFDB
- React + TypeScript
- Vite
- PixiJS
- ESP32
- MAX30100 Pulse Oximeter
- HTU21D
- AD8232

---

## Notes

If the frontend is started for the first time, execute:
```bash
cd ui
npm install
```
before running `start.bat`.

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
