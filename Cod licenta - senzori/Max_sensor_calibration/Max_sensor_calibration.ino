// ============================================================
//  MAX30100 LED Current Calibration
//  Tests 8 current levels, 15s each
//  Prints summary table at the end
// ============================================================

#include <Wire.h>
#include "MAX30100_PulseOximeter.h"

PulseOximeter pox;

struct CalibResult {
  float current;
  int beatsDetected;
  float hrMin;
  float hrMax;
  int spo2Min;
  int spo2Max;
  String notes;
};

CalibResult results[6];

LEDCurrent levels[] = {
  MAX30100_LED_CURR_7_6MA,
  MAX30100_LED_CURR_14_2MA,
  MAX30100_LED_CURR_17_4MA,
  MAX30100_LED_CURR_20_8MA,
  MAX30100_LED_CURR_27_1MA,
  MAX30100_LED_CURR_50MA,
};

float levelValues[] = {7.6, 14.2, 17.4, 20.8, 27.1, 50.0};

volatile int beatCount = 0;
void onBeat() { beatCount++; }

void setup() {
  Serial.begin(115200);
  delay(1000);
  Wire.begin(27, 32);
  Serial.println("\n=== MAX30100 LED Current Calibration ===");
  Serial.println("Keep finger firmly on sensor during entire test.");
  Serial.println("Starting in 5 seconds...");
  delay(5000);
}

void loop() {
for (int i = 0; i < 6; i++) {
    Serial.printf("\n--- Testing %.1f mA ---\n", levelValues[i]);

    pox.begin();
    pox.setIRLedCurrent(levels[i]);
    pox.setOnBeatDetectedCallback(onBeat);

    beatCount = 0;
    float hrMin = 999, hrMax = 0;
    int spo2Min = 100, spo2Max = 0;

    uint32_t start = millis();
    while (millis() - start < 15000) {
      pox.update();

      float hr   = pox.getHeartRate();
      int   spo2 = pox.getSpO2();

      if (hr > 40 && hr < 200) {
        if (hr < hrMin) hrMin = hr;
        if (hr > hrMax) hrMax = hr;
      }
      if (spo2 > 50 && spo2 <= 100) {
        if (spo2 < spo2Min) spo2Min = spo2;
        if (spo2 > spo2Max) spo2Max = spo2;
      }

      if (millis() % 1000 < 5) {
        Serial.printf("  HR: %.1f | SpO2: %d | Beats: %d\n", hr, spo2, beatCount);
      }
    }

    results[i].current      = levelValues[i];
    results[i].beatsDetected = beatCount;
    results[i].hrMin        = hrMin == 999 ? 0 : hrMin;
    results[i].hrMax        = hrMax;
    results[i].spo2Min      = spo2Min == 100 ? 0 : spo2Min;
    results[i].spo2Max      = spo2Max;
  }

  // Print summary table
  Serial.println("\n\n=== CALIBRATION SUMMARY ===");
  Serial.println("Current | Beats | HR Min | HR Max | SpO2 Min | SpO2 Max");
  Serial.println("---------------------------------------------------------");
  for (int i = 0; i < 8; i++) {
    Serial.printf("%.1f mA  |  %2d   |  %.1f  |  %.1f  |   %d     |   %d\n",
      results[i].current,
      results[i].beatsDetected,
      results[i].hrMin,
      results[i].hrMax,
      results[i].spo2Min,
      results[i].spo2Max
    );
  }
  Serial.println("=== END ===");

  while(1) delay(1000);  // stop after one full run
}