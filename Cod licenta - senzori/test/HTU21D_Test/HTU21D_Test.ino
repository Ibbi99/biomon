// ============================================================
//  VARIANTA 2: ESP32 – MAX30100 + HTU21D → Firebase (Dual Core)
//  Patient: Patient_02
// ============================================================

#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "MAX30100_PulseOximeter.h"

// ── WiFi ─────────────────────────────────────────────────────
const char* WIFI_SSID     = "iPhone-Cristina";
const char* WIFI_PASSWORD = "12345678";

// ── Firebase ─────────────────────────────────────────────────
const char* FB_HOST = "https://bachelordegree-6ed5c-default-rtdb.europe-west1.firebasedatabase.app";
const char* PATIENT = "Patient_02";

// ── MAX30100 ─────────────────────────────────────────────────
#define BPM_MIN  30
#define BPM_MAX  200
#define SPO2_MIN 70
#define SPO2_MAX 100
#define REINIT_TIMEOUT_MS 10000

PulseOximeter pox;
volatile uint32_t lastBeat = 0; // volatile for FreeRTOS sharing
volatile bool     fingerOn = false;

// ── HTU21D (manual, fără librărie) ───────────────────────────
TwoWire I2C_2 = TwoWire(1);
#define HTU21D_ADDR 0x40

float readHTUTemperature() {
  I2C_2.beginTransmission(HTU21D_ADDR);
  I2C_2.write(0xE3); // trigger temperatura
  I2C_2.endTransmission();

  // Folosim vTaskDelay in loc de delay() pentru a nu bloca procesorul
  // In codul vechi, acest delay(50) bloca senzorul MAX30100!
  vTaskDelay(50 / portTICK_PERIOD_MS);

  I2C_2.requestFrom(HTU21D_ADDR, 2);
  if (I2C_2.available() < 2) return -999;

  uint16_t raw = (I2C_2.read() << 8) | I2C_2.read();
  raw &= 0xFFFC;

  return -46.85 + 175.72 * raw / 65536.0;
}

// ── FreeRTOS Task ────────────────────────────────────────────
TaskHandle_t FirebaseTask;

// ─────────────────────────────────────────────────────────────

void onBeatDetected() {
  lastBeat = millis();
  fingerOn = true;
}

bool fbPutJson(const String& path, const String& body) {
  if (WiFi.status() != WL_CONNECTED) return false;
  HTTPClient http;
  http.begin(String(FB_HOST) + path + ".json");
  http.addHeader("Content-Type", "application/json");
  int code = http.PUT(body);
  http.end();
  return (code == 200 || code == 204);
}

void sendToFirebase(float bpm, int spo2, bool bpmSpo2Valid, float temp, bool tempValid) {
  unsigned long ts = millis();

  String liveJson = "{";
  liveJson += "\"bpm\":"         + String(bpmSpo2Valid ? bpm : 0, 1) + ",";
  liveJson += "\"spo2\":"        + String(bpmSpo2Valid ? spo2 : 0)   + ",";
  liveJson += "\"finger_on\":"   + String(fingerOn ? "true" : "false") + ",";
  liveJson += "\"temperature\":" + String(tempValid ? temp : 0, 1)   + ",";
  liveJson += "\"temp_valid\":"  + String(tempValid ? "true" : "false") + ",";
  liveJson += "\"temp_source\":\"HTU21D\","; // Added source for debug visibility
  liveJson += "\"timestamp\":"   + String(ts);
  liveJson += "}";

  String livePath = String("/patients/") + PATIENT + "/live/vitals";
  String histPath = String("/patients/") + PATIENT + "/history/vitals/" + String(ts);

  bool okLive = fbPutJson(livePath, liveJson);
  bool okHist = fbPutJson(histPath, liveJson);

  Serial.printf("[FB] BPM: %.1f | SpO2: %d%% | Temp: %.1f°C (HTU21D) | live=%s | hist=%s\n",
                bpm, spo2, temp,
                okLive ? "OK" : "ERR",
                okHist ? "OK" : "ERR");
}

// ── TASK: Ruleaza pe Core 0 pentru retea si HTU21D ───────────
void firebaseTaskCode(void * pvParameters) {
  for (;;) {
    // Asteapta 2 secunde
    vTaskDelay(2000 / portTICK_PERIOD_MS);

    if (WiFi.status() == WL_CONNECTED) {
      float bpm  = pox.getHeartRate();
      int   spo2 = pox.getSpO2();

      bool bpmSpo2Valid = (bpm >= BPM_MIN && bpm <= BPM_MAX &&
                           spo2 >= SPO2_MIN && spo2 <= SPO2_MAX);

      float temp = readHTUTemperature();
      bool  tempValid = (temp > -40 && temp < 125);

      sendToFirebase(bpm, spo2, bpmSpo2Valid, temp, tempValid);
    }
  }
}

// ─────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(115200);
  delay(1000);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi OK!");

  // MAX30100 → bus 1
  Wire.begin(21, 22);

  // HTU21D → bus 2
  I2C_2.begin(18, 19);

  if (!pox.begin()) {
    Serial.println("EROARE MAX30100");
    while (1) delay(1000);
  }

  // MODIFICARE AICI: Setat la 50MA
  pox.setIRLedCurrent(MAX30100_LED_CURR_50MA);
  pox.setOnBeatDetectedCallback(onBeatDetected);

  lastBeat = millis();

  // Cream task-ul pentru Firebase pe Core 0
  xTaskCreatePinnedToCore(
    firebaseTaskCode,   // Functia task-ului
    "FirebaseTask",     // Numele task-ului
    10000,              // Dimensiunea stivei
    NULL,               // Parametri
    1,                  // Prioritate
    &FirebaseTask,      // Handle
    0);                 // Rulat pe Core 0
}

void loop() {
  // Core 1 se ocupa EXCLUSIV de senzorul MAX30100
  pox.update();

  if (millis() - lastBeat > REINIT_TIMEOUT_MS) {
    Serial.println("[WATCHDOG] Reinitializare MAX30100...");
    fingerOn = false;
    pox.begin();
    pox.setIRLedCurrent(MAX30100_LED_CURR_50MA); // Setat la 50MA si la reinitializare
    pox.setOnBeatDetectedCallback(onBeatDetected);
    lastBeat = millis();
  }
}
