/**
 *  ESP32 – AD8232 ECG  →  Firebase Realtime Database
 *  Patient: Patient_02
 *
 *  Hardware:
 *    - AD8232 ECG sensor: OUTPUT=GPIO33, LO-=GPIO25, LO+=GPIO26
 *
 *  Firebase paths:
 *    - /patients/Patient_02/live/ecg          ← current batch (read by Python)
 *
 *  Sampling: 200Hz, 200 samples per batch (1s of data)
 *  Timestamp: Unix ms via NTP (required for Python stale detection)
 *  History: written exclusively by Python backend (server-side timestamps)
 *  @author Cristina Vedinas
 */
```



#include <WiFi.h>
#include <HTTPClient.h>
#include <time.h>

// ── WiFi ─────────────────────────────────────────────────────
const char* WIFI_SSID     = "Name";
const char* WIFI_PASSWORD = "Password";

// ── Firebase ─────────────────────────────────────────────────
const char* FB_HOST = "https://bachelordegree-6ed5c-default-rtdb.europe-west1.firebasedatabase.app";
const char* PATIENT = "Patient_02";

// ── NTP ──────────────────────────────────────────────────────
const char* NTP1 = "pool.ntp.org";
const char* NTP2 = "time.google.com";
const char* NTP3 = "time.cloudflare.com";

// Returns Unix timestamp in milliseconds (required for Python stale detection)
uint64_t getNtpTimestampMs() {
  struct timeval tv;
  gettimeofday(&tv, NULL);
  return (uint64_t)tv.tv_sec * 1000ULL + tv.tv_usec / 1000;
}

// ── AD8232 pins ──────────────────────────────────────────────
const int ECG_PIN  = 33;   // analog output
const int LO_MINUS = 25;   // lead-off detection -
const int LO_PLUS  = 26;   // lead-off detection +

// ── Sampling parameters ──────────────────────────────────────
const int SAMPLING_RATE   = 200;
const int SAMPLE_DELAY_MS = 1000 / SAMPLING_RATE;  // 5ms per sample
const int BATCH_SIZE      = 200;                    // 1s of data per batch

// ── Buffer ───────────────────────────────────────────────────
int  ecgBatch[BATCH_SIZE];
int  batchIndex    = 0;
int  leadsOffCount = 0;

unsigned long lastSampleTime = 0;

// ── Firebase ─────────────────────────────────────────────────
bool fbPutJson(const String& path, const String& body) {
  if (WiFi.status() != WL_CONNECTED) return false;
  HTTPClient http;
  http.begin(String(FB_HOST) + path + ".json");
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(6000);
  int code = http.PUT(body);
  http.end();
  return (code == 200 || code == 204);
}

void sendBatch() {
 uint64_t ts = getNtpTimestampMs(); 

  String arr = "[";
  for (int i = 0; i < BATCH_SIZE; i++) {
    arr += String(ecgBatch[i]);
    if (i < BATCH_SIZE - 1) arr += ",";
  }
  arr += "]";

  String batchJson = "{";
  batchJson += "\"ecg_batch\":"           + arr + ",";
  batchJson += "\"expected_batch_size\":" + String(BATCH_SIZE) + ",";
  batchJson += "\"missing_samples\":" + String(leadsOffCount) + ",";
  batchJson += "\"sampling_rate\":"       + String(SAMPLING_RATE) + ",";
  batchJson += "\"source_type\":\"esp32_ad8232\",";
char tsStr[21];
sprintf(tsStr, "%llu", ts);
batchJson += "\"timestamp\":" + String(tsStr);
  batchJson += "}";

  // live/ecg — overwritten every batch, read by Python
  String livePath = String("/patients/") + PATIENT + "/live/ecg";
  bool okLive = fbPutJson(livePath, batchJson);

Serial.printf("[BATCH] ts=%llu | leads_off=%d/%d | live=%s\n",
                ts, leadsOffCount, BATCH_SIZE,
                okLive ? "OK" : "ERR");

  batchIndex    = 0;
  leadsOffCount = 0;
}

// ─────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n=== ESP32 ECG Patient_02 v4 ===");

  pinMode(LO_MINUS, INPUT);
  pinMode(LO_PLUS,  INPUT);
  analogReadResolution(12);  // 12-bit ADC resolution (0–4095)

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("WiFi");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println(" OK — IP: " + WiFi.localIP().toString());

  configTime(0, 0, NTP1, NTP2, NTP3);
  Serial.print("NTP");
  struct tm timeinfo;
  int retries = 0;
  while (!getLocalTime(&timeinfo) && retries < 20) { delay(500); Serial.print("."); retries++; }
  if (retries < 20)
    Serial.printf(" OK — %04d-%02d-%02d %02d:%02d:%02d UTC\n",
      timeinfo.tm_year+1900, timeinfo.tm_mon+1, timeinfo.tm_mday,
      timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);
  else
    Serial.println(" FAILED");

  Serial.println("System ready — attach electrodes and start.");
}

// ─────────────────────────────────────────────────────────────
void loop() {
  unsigned long now = millis();

  if (now - lastSampleTime >= SAMPLE_DELAY_MS) {
    lastSampleTime = now;

    bool leadsOff = (digitalRead(LO_MINUS) == HIGH || digitalRead(LO_PLUS) == HIGH);
    int  ecgValue = leadsOff ? 0 : analogRead(ECG_PIN);

    ecgBatch[batchIndex] = ecgValue;
    if (leadsOff) leadsOffCount++;
    batchIndex++;

    if (batchIndex >= BATCH_SIZE) {
      sendBatch();
    }
  }
}