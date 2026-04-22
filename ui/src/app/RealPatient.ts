// src/app/RealPatient.ts
//
// Entry point for the real patient detail page (patient_real.html).
// Connects Firebase to the DashboardController via EventBus.
//
// Data source: ESP32 sensors (AD8232 ECG + MAX30100 + DHT11) → Firebase
//   → Python app.py processor → /patients/Patient_02/dashboard/current → this page
//
// Patient_02 is the physical ESP32 device. Data arrives when the device
// is powered on and connected to WiFi. When the device is offline,
// the last known values remain in Firebase.

import { EventBus } from "@app/EventBus";
import { DashboardController } from "@app/DashboardController";
import { FirebaseService } from "@core/services/FirebaseService";
import type { DashboardPayload } from "@core/models/DashboardPayload";
import { setupThemeToggle } from "@ui/components/ThemeToggle";
import { HistoryChart } from "@ui/components/HistoryChart";

// Initialize theme toggle (reads saved preference from localStorage)
setupThemeToggle();

const eventBus = new EventBus();
const dashboardController = new DashboardController(eventBus);
dashboardController.bind();

const firebaseService = new FirebaseService();

// Subscribe to the processed dashboard data written by the Python processor.
// NOTE: Firebase paths are case-sensitive — "dashboard" must be lowercase.
firebaseService.subscribe<DashboardPayload>(
  "/patients/Patient_02/dashboard/current",
  (payload) => {
    if (!payload) return;

    // Forward the payload to all UI components via EventBus
    eventBus.emit<DashboardPayload>("dashboard:update", payload);

    // Update the last-update timestamp in the footer
    const lastUpdate = document.getElementById("last-update");
    if (lastUpdate) {
      lastUpdate.textContent = `Last update: ${
        payload.timestamp ? new Date(payload.timestamp).toLocaleTimeString() : "--"
      }`;
    }
  }
);

// ==========================================
// HISTORY LOGIC
// ==========================================
const historyChart = new HistoryChart("history-chart");
const btnLoad = document.getElementById("btn-load-history") as HTMLButtonElement;
const inputStart = document.getElementById("hist-start") as HTMLInputElement;
const inputEnd = document.getElementById("hist-end") as HTMLInputElement;

// Set default times in the inputs (Last 1 hour)
const now = new Date();
const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
// format for datetime-local input (YYYY-MM-DDThh:mm)
inputStart.value = oneHourAgo.toISOString().slice(0, 16); 
inputEnd.value = now.toISOString().slice(0, 16);

btnLoad.addEventListener("click", async () => {
  btnLoad.textContent = "Loading...";
  btnLoad.style.opacity = "0.5";
  btnLoad.disabled = true;

  // Convert inputs back to Unix milliseconds
  const startTs = new Date(inputStart.value).getTime();
  const endTs = new Date(inputEnd.value).getTime();

  // Fetch the data
  const historyData = await firebaseService.fetchHistory<any>(
    "/patients/Patient_02/history/vitals", 
    startTs, 
    endTs
  );

  console.log(`Fetched ${historyData.length} historical records.`);
  historyChart.updateData(historyData);

  btnLoad.textContent = "Load Data";
  btnLoad.style.opacity = "1";
  btnLoad.disabled = false;
});

