/**
 *  ESP32 – MAX30100 (7.6mA) + HTU21D → Firebase
 *   Patient: Patient_02
 * 
 *  Hardware:
 *     - MAX30100 (SpO2/HR): I2C bus 0 — SDA=GPIO27, SCL=GPIO32
 *     - HTU21D (Temperature): I2C bus 1 — SDA=GPIO25, SCL=GPIO26
 *     - GPIO12 tied to GND (strapping pin)

 *  Architecture:
 *     - Core 1 (loop): MAX30100 updates + HTU21D reads every 4s
 *     - Core 0 (task): Firebase writes every 3s
 *    - Mutex protects shared temperature variable between cores
 * @author Cristina Vedinas
 */

#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <time.h>
#include "MAX30100_PulseOximeter.h"

// ── WiFi ─────────────────────────────────────────────────────
const char* WIFI_SSID     = "iPhone-Cristina";
const char* WIFI_PASSWORD = "12345678";

// ── Firebase ─────────────────────────────────────────────────
const char* FB_HOST = "https://bachelordegree-6ed5c-default-rtdb.europe-west1.firebasedatabase.app";
const char* PATIENT = "Patient_02";

// ── NTP ──────────────────────────────────────────────────────
const char* NTP1 = "pool.ntp.org";
const char* NTP2 = "time.google.com";
const char* NTP3 = "time.cloudflare.com";

// Returns Unix timestamp in milliseconds (requires NTP sync)
unsigned long getNtpTimestampMs() {
  struct timeval tv;
  gettimeofday(&tv, NULL);
  return (unsigned long)(tv.tv_sec * 1000UL + tv.tv_usec / 1000);
}

// ── MAX30100 ─────────────────────────────────────────────────
// HR filter: rejects readings outside [40, 150] BPM
// and spikes > 35 BPM from rolling mean
#define BPM_MIN            40
#define BPM_MAX            150
#define SPO2_MIN           85
#define SPO2_MAX           100
#define FINGER_TIMEOUT_MS  8000 // ms without beat → finger lifted
#define REINIT_TIMEOUT_MS  30000 // ms without beat → reinit sensor

PulseOximeter pox;
volatile uint32_t lastBeat = 0;
volatile uint32_t prevBeat = 0;

void onBeatDetected() {
  prevBeat = lastBeat;
  lastBeat = millis();
}

// ── HR rolling filter ─────────────────────────────────────────────────
#define HR_HISTORY_N  4
#define HR_MAX_JUMP   35.0f

float hrBuf[HR_HISTORY_N];
int   hrBufCount = 0;

void hrReset() {
  hrBufCount = 0;
}

float hrMean() {
  if (hrBufCount == 0) return 0.0f;
  int n = min(hrBufCount, HR_HISTORY_N);
  float s = 0;
  for (int i = 0; i < n; i++) s += hrBuf[i];
  return s / n;
}

bool hrAccept(float bpm) {
  if (bpm < BPM_MIN || bpm >= BPM_MAX) return false;
  
  float mean = hrMean();
  if (hrBufCount > 0 && fabsf(bpm - mean) > HR_MAX_JUMP) return false;

  hrBuf[hrBufCount % HR_HISTORY_N] = bpm;
  hrBufCount++;
  return true;
}

// ── HTU21D — I2C bus 1, SDA=GPIO25, SCL=GPIO26 ───────────────
// Reads ambient temperature every 4s using No-Hold Master mode.
// Mutex protects g_temperature from concurrent access by Core 0.
// Watchdog: if value unchanged for 60s → soft reset sensor.
TwoWire I2C_HTU = TwoWire(1);
#define HTU21D_ADDR 0x40
#define HTU_READ_INTERVAL_MS  4000
#define HTU_STUCK_DELTA       0.05f // °C — below this = considered stuck
#define HTU_STUCK_TIMEOUT_MS  60000 // ms stuck before soft reset

SemaphoreHandle_t tempMutex;
float    g_temperature = -999.0f;
bool     g_tempValid   = false;

float    htuLastPrintedTemp  = -999.0f;
uint32_t htuLastChangeTime   = 0;
bool     htuStuckWarned      = false;

enum HTUState { HTU_IDLE, HTU_TRIGGERED };
HTUState htuState      = HTU_IDLE;
uint32_t htuTrigTime   = 0;
uint32_t htuNextTrig   = 0;

void htuSoftReset() {
  Serial.println("[HTU21D] Sensor stuck ");
  I2C_HTU.beginTransmission(HTU21D_ADDR);
  I2C_HTU.write(0xFE);  // reset command per datasheet
  I2C_HTU.endTransmission();
  delay(15);  // 15ms reset time per datasheet
  htuState          = HTU_IDLE;
  htuNextTrig       = millis() + 500;
  htuLastChangeTime = millis();
  htuStuckWarned    = false;
}

void htuUpdate() {
  uint32_t now = millis();

  if (htuState == HTU_IDLE) {
    if (now < htuNextTrig) return;

    I2C_HTU.beginTransmission(HTU21D_ADDR);
    I2C_HTU.write(0xF3); // trigger temp measurement, no-hold master mode
    if (I2C_HTU.endTransmission() == 0) {
      htuState    = HTU_TRIGGERED;
      htuTrigTime = now;
    } else {
      htuNextTrig = now + 2000;
      Serial.println("[HTU21D] No response");
    }
    return;
  }

  if (now - htuTrigTime < 60) return; // wait 60ms for measurement

  htuState    = HTU_IDLE;
  htuNextTrig = now + HTU_READ_INTERVAL_MS;

  uint8_t n = I2C_HTU.requestFrom((uint8_t)HTU21D_ADDR, (uint8_t)3);
  if (n < 2) {
    Serial.println("[HTU21D] Read failed");
    return;
  }

  uint8_t msb = I2C_HTU.read();
  uint8_t lsb = I2C_HTU.read();
  if (I2C_HTU.available()) I2C_HTU.read(); // discard CRC

  uint16_t raw = ((uint16_t)msb << 8) | lsb;
  raw &= 0xFFFC; // clear status bits
  float temp = -46.85f + 175.72f * (float)raw / 65536.0f;

 // HTU21D valid range: -40 to +125°C
  if (temp < -10.0f || temp > 85.0f) {
    Serial.printf("[HTU21D] Valoare invalida: %.2f\n", temp);
    return;
  }

  // Watchdog: detect stuck sensor
  if (fabsf(temp - htuLastPrintedTemp) > HTU_STUCK_DELTA) {
    htuLastChangeTime  = now;
    htuStuckWarned     = false;
    Serial.printf("[HTU21D] %.2f°C\n", temp);
    htuLastPrintedTemp = temp;
  } else if (!htuStuckWarned && (now - htuLastChangeTime > HTU_STUCK_TIMEOUT_MS)) {
    htuStuckWarned = true;
    htuSoftReset();
    return;
  }

  if (xSemaphoreTake(tempMutex, 5) == pdTRUE) {
    g_temperature = temp;
    g_tempValid   = true;
    xSemaphoreGive(tempMutex);
  }
}

// ── I2C bus scan — runs once at boot for wiring verification ─
void scanI2C() {
  Serial.println("=== I²C Scan GPIO 27/32 (MAX30100) ===");
  int found = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.printf(" Found: 0x%02X\n", addr);
      found++;
    }
  }
  if (!found) Serial.println(" NOTHING - check GPIO27/32 wiring ");
  Serial.println("==========================");

  Serial.println("=== I2C Scan GPIO25/26 (HTU21D bus) ===");
  found = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    I2C_HTU.beginTransmission(addr);
    if (I2C_HTU.endTransmission() == 0) {
      Serial.printf(" Found:  0x%02X\n", addr);
      found++;
    }
  }
  if (!found) Serial.println("NOTHING - check GPIO25/26 wiring");
  Serial.println("==========================");
}

// ── Firebase ─────────────────────────────────────────────────
bool fbPutJson(const String& path, const String& body) {
  if (WiFi.status() != WL_CONNECTED) return false;
  HTTPClient http;
  http.begin(String(FB_HOST) + path + ".json");
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(5000);
  int code = http.PUT(body);
  http.end();
  return (code == 200 || code == 204);
}

void sendToFirebase(float bpm, int spo2, bool valid) {
  unsigned long ts = getNtpTimestampMs();
  bool fingerPresent = (millis() - lastBeat) < FINGER_TIMEOUT_MS;

  float tempVal = -999.0f;
  bool  tempOk  = false;
  if (xSemaphoreTake(tempMutex, 10) == pdTRUE) {
    tempVal = g_temperature;
    tempOk  = g_tempValid;
    xSemaphoreGive(tempMutex);
  }

  String json = "{";
  if (valid) {
    json += "\"heartRate\":"  + String(bpm, 1) + ",";
    json += "\"spo2\":"       + String(spo2)   + ",";
  } else {
    json += "\"heartRate\":null,\"spo2\":null,";
  }
  json += "\"finger_on\":"   + String(fingerPresent ? "true" : "false") + ",";
  if (tempOk && tempVal > -10.0f) {
    json += "\"temperature\":" + String(tempVal, 1) + ",";
  } else {
    json += "\"temperature\":null,";
  }
  json += "\"temp_source\":\"HTU21D\",";
  json += "\"timestamp\":"   + String(ts);
  json += "}";

  String livePath = String("/patients/") + PATIENT + "/live/vitals";

  bool okL = fbPutJson(livePath, json);

  Serial.printf("[FB] HR:%s SpO2:%s Temp:%s finger:%s live:%s\n",
    valid  ? String(bpm,1).c_str()   : "null",
    valid  ? String(spo2).c_str()    : "null",
    tempOk ? String(tempVal,1).c_str() : "null",
    fingerPresent ? "ON" : "off",
    okL ? "OK" : "ERR");
}

// ── Firebase task — runs on Core 0 ───────────────────────────
TaskHandle_t FirebaseTask;

void firebaseTaskCode(void* pvParameters) {
  uint32_t lastSend     = 0;
  uint32_t lastBeatSnap = 0;

  for (;;) {
    vTaskDelay(100 / portTICK_PERIOD_MS);
    uint32_t now = millis();
    if (now - lastSend < 3000) continue;
    lastSend = now;

    if (WiFi.status() != WL_CONNECTED) continue;

// Reset HR filter if finger lifted for too long
    uint32_t beatSnap = lastBeat;
    if (beatSnap == lastBeatSnap && now - beatSnap > FINGER_TIMEOUT_MS) {
      if (hrBufCount > 0) hrReset();
    }
    lastBeatSnap = beatSnap;

    float bpm  = pox.getHeartRate();
    int   spo2 = pox.getSpO2();
    bool  fingerPresent = (now - lastBeat) < FINGER_TIMEOUT_MS;

    bool valid = false;
    if (fingerPresent && spo2 >= SPO2_MIN && spo2 <= SPO2_MAX) {
      valid = hrAccept(bpm);
    }

    sendToFirebase(bpm, spo2, valid);
  }
}

// ─────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== ESP32 Patient_02 ===");

  tempMutex = xSemaphoreCreateMutex();

 // MAX30100 on bus 0, HTU21D on bus 1
  Wire.begin(27, 32);
  I2C_HTU.begin(25, 26);
  I2C_HTU.setClock(50000);

  scanI2C();

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("WiFi");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println(" OK! IP: " + WiFi.localIP().toString());

  configTime(0, 0, NTP1, NTP2, NTP3);
  Serial.print("NTP");
  struct tm timeinfo;
  int retries = 0;
  while (!getLocalTime(&timeinfo) && retries < 20) { delay(500); Serial.print("."); retries++; }
  if (retries < 20)
    Serial.printf("\nNTP OK — %04d-%02d-%02d %02d:%02d:%02d UTC\n",
      timeinfo.tm_year+1900, timeinfo.tm_mon+1, timeinfo.tm_mday,
      timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);
  else
    Serial.println("FAILED!");

 // LED current 14.2mA
  if (!pox.begin()) {
    Serial.println("[ERROR] MAX30100 not responding");
    while (1) delay(1000);
  }
  pox.setIRLedCurrent(MAX30100_LED_CURR_14_2MA);
  pox.setOnBeatDetectedCallback(onBeatDetected);
  Serial.println("MAX30100 OK!");

  lastBeat          = millis();
  htuNextTrig       = millis() + 500;
  htuLastChangeTime = millis();

  xTaskCreatePinnedToCore(firebaseTaskCode, "FirebaseTask", 12000, NULL, 1, &FirebaseTask, 0);

  Serial.println("System ready.");
}

void loop() {
  pox.update();
  htuUpdate();

 // Watchdog: reinit MAX30100 if no beat detected for 30s
  if (millis() - lastBeat > REINIT_TIMEOUT_MS) {
    Serial.println("[WATCHDOG] Reinit MAX30100...");
    pox.begin();
    pox.setIRLedCurrent(MAX30100_LED_CURR_14_2MA);
    pox.setOnBeatDetectedCallback(onBeatDetected);
    hrReset();
    lastBeat = millis();
  }
}