// ============================================================
//  ESP32 – AD8232 ECG  →  Firebase Realtime Database  v2
//  Patient: Patient_02
//  FIX: sampling non-blocant – HTTP trimis doar la batch complet
// ============================================================

#include <WiFi.h>
#include <HTTPClient.h>

// ── WiFi ─────────────────────────────────────────────────────
const char* WIFI_SSID     = "TP-Link_004C";
const char* WIFI_PASSWORD = "caramida";

// ── Firebase ─────────────────────────────────────────────────
const char* FB_HOST = "https://bachelordegree-6ed5c-default-rtdb.europe-west1.firebasedatabase.app";
const char* PATIENT = "Patient_02";

// ── Pini AD8232 ──────────────────────────────────────────────
const int ECG_PIN  = 34;
const int LO_MINUS = 25;
const int LO_PLUS  = 26;

// ── Parametri sampling ───────────────────────────────────────
const int SAMPLING_RATE   = 200;
const int SAMPLE_DELAY_MS = 1000 / SAMPLING_RATE;  // 5ms
const int BATCH_SIZE      = 200;   // 1 secundă de date

// ── Buffer ───────────────────────────────────────────────────
int  ecgBatch[BATCH_SIZE];
int  batchIndex    = 0;
int  leadsOffCount = 0;

// ── Timing ───────────────────────────────────────────────────
unsigned long lastSampleTime = 0;

// ─────────────────────────────────────────────────────────────

bool fbPutJson(const String& path, const String& body) {
  if (WiFi.status() != WL_CONNECTED) return false;
  HTTPClient http;
  http.begin(String(FB_HOST) + path + ".json");
  http.addHeader("Content-Type", "application/json");
  int code = http.PUT(body);
  http.end();
  return (code == 200 || code == 204);
}

void sendBatch() {
  unsigned long ts = millis();

  // Construiește array ECG
  String arr = "[";
  for (int i = 0; i < BATCH_SIZE; i++) {
    arr += String(ecgBatch[i]);
    if (i < BATCH_SIZE - 1) arr += ",";
  }
  arr += "]";

  // Construiește JSON batch (history)
  String batchJson = "{";
  batchJson += "\"ecg_batch\":"           + arr + ",";
  batchJson += "\"expected_batch_size\":" + String(BATCH_SIZE) + ",";
  batchJson += "\"leads_off_samples\":"   + String(leadsOffCount) + ",";
  batchJson += "\"sampling_rate\":"       + String(SAMPLING_RATE) + ",";
  batchJson += "\"source_type\":\"esp32_ad8232\",";
  batchJson += "\"timestamp\":"           + String(ts);
  batchJson += "}";

  // Construiește JSON live (ultimul sample din batch)
  int lastEcg      = ecgBatch[BATCH_SIZE - 1];
  bool lastLeadsOff = (leadsOffCount == BATCH_SIZE);  // toți au fost leads_off
  String liveJson = "{";
  liveJson += "\"ecg\":"       + String(lastEcg) + ",";
  liveJson += "\"leads_off\":" + String(lastLeadsOff ? "true" : "false") + ",";
  liveJson += "\"timestamp\":" + String(ts);
  liveJson += "}";

  String histPath = String("/patients/") + PATIENT + "/history/ecg/" + String(ts);
  String livePath = String("/patients/") + PATIENT + "/live";

  bool okHist = fbPutJson(histPath, batchJson);
  bool okLive = fbPutJson(livePath, liveJson);

  Serial.printf("[BATCH] ts=%lu | leads_off_samples=%d | history=%s | live=%s\n",
                ts, leadsOffCount,
                okHist ? "OK" : "ERR",
                okLive ? "OK" : "ERR");

  batchIndex    = 0;
  leadsOffCount = 0;
}

// ─────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  pinMode(LO_MINUS, INPUT);
  pinMode(LO_PLUS,  INPUT);
  analogReadResolution(12);

  Serial.printf("Conectare WiFi: %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi OK! IP: " + WiFi.localIP().toString());
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

    // Log în Serial la fiecare 20 samples (nu la fiecare ca să nu încetinească)
    if (batchIndex % 20 == 0) {
      Serial.printf("Sample %d/%d | ECG: %4d | leads_off: %s\n",
                    batchIndex, BATCH_SIZE, ecgValue, leadsOff ? "DA" : "nu");
    }

    // Batch complet → trimite Firebase (blocking, dar sampling deja terminat)
    if (batchIndex >= BATCH_SIZE) {
      sendBatch();
    }
  }
}
