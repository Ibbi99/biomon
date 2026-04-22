// ============================================================
//  VARIANTA 1: ESP32 – MAX30100 + DHT11 → Firebase (Dual Core)
//  Patient: Patient_02
// ============================================================

#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "MAX30100_PulseOximeter.h"
#include "DHT.h"

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
volatile uint32_t lastBeat = 0; // volatile because it's shared between cores
volatile bool     fingerOn = false;

// ── DHT11 ────────────────────────────────────────────────────
#define DHT_PIN  4
#define DHT_TYPE DHT11
DHT dht(DHT_PIN, DHT_TYPE);

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
  liveJson += "\"temp_source\":\"DHT11\",";
  liveJson += "\"timestamp\":"   + String(ts);
  liveJson += "}";

  String livePath = String("/patients/") + PATIENT + "/live/vitals";
  String histPath = String("/patients/") + PATIENT + "/history/vitals/" + String(ts);

  bool okLive = fbPutJson(livePath, liveJson);
  bool okHist = fbPutJson(histPath, liveJson);

  Serial.printf("[FB] BPM: %.1f | SpO2: %d%% | Temp: %.1f°C (DHT11) | live=%s | hist=%s\n",
                bpm, spo2, temp,
                okLive ? "OK" : "ERR",
                okHist ? "OK" : "ERR");
}

// ── TASK: Ruleaza pe Core 0 pentru retea si DHT ──────────────
void firebaseTaskCode(void * pvParameters) {
  for (;;) {
    // Asteapta 2 secunde (inlocuieste millis() - lastReport)
    vTaskDelay(2000 / portTICK_PERIOD_MS);

    // Citeste senzorii si trimite doar daca avem WiFi
    if (WiFi.status() == WL_CONNECTED) {
      float bpm  = pox.getHeartRate();
      int   spo2 = pox.getSpO2();
      bool  bpmSpo2Valid = (bpm >= BPM_MIN && bpm <= BPM_MAX &&
                            spo2 >= SPO2_MIN && spo2 <= SPO2_MAX);

      float temp      = dht.readTemperature();
      bool  tempValid = !isnan(temp);

      Serial.printf("BPM: %.1f | SpO2: %d%% | Temp: %.1f°C\n", bpm, spo2, temp);
      sendToFirebase(bpm, spo2, bpmSpo2Valid, temp, tempValid);
    }
  }
}

// ─────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.printf("Conectare WiFi: %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi OK! IP: " + WiFi.localIP().toString());

  Wire.begin(21, 22);
  Serial.println("Initializare MAX30100...");
  if (!pox.begin()) {
    Serial.println("EROARE: MAX30100 nu raspunde!");
    while (1) delay(1000);
  }
  
  // MODIFICARE AICI: Setat la 50MA conform codului de test functional
  pox.setIRLedCurrent(MAX30100_LED_CURR_50MA);
  pox.setOnBeatDetectedCallback(onBeatDetected);
  Serial.println("MAX30100 OK!");

  dht.begin();
  Serial.println("DHT11 OK!");

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
  // Core 1 (Default) se ocupa EXCLUSIV de actualizarea senzorului cat mai rapid
  pox.update();

  // Watchdog pentru MAX30100
  if (millis() - lastBeat > REINIT_TIMEOUT_MS) {
    Serial.println("[WATCHDOG] Reinitializare MAX30100...");
    fingerOn = false;
    pox.begin();
    pox.setIRLedCurrent(MAX30100_LED_CURR_50MA);
    pox.setOnBeatDetectedCallback(onBeatDetected);
    lastBeat = millis();
  }
}
