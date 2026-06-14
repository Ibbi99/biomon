// src/app/RealPatient.ts
//
// Entry point for the real patient detail page (patient_real.html).
// Connects Firebase to the DashboardController via EventBus.
//
// Data source: ESP32 sensors → Firebase → Python app.py processor
//   → /patients/Patient_02/dashboard/current → this page

import { EventBus } from "@app/EventBus";
import { DashboardController } from "@app/DashboardController";
import { FirebaseService } from "@core/services/FirebaseService";
import { HistoryChart } from "@ui/components/HistoryChart";
import { setupThemeToggle } from "@ui/components/ThemeToggle";
import type { DashboardPayload } from "@core/models/DashboardPayload";

setupThemeToggle();

const eventBus = new EventBus();
const dashboardController = new DashboardController(eventBus);
dashboardController.bind();

const firebaseService = new FirebaseService();

firebaseService.subscribe<DashboardPayload>(
  "/patients/Patient_02/dashboard/current",
  (payload) => {
    if (!payload) return;
    eventBus.emit<DashboardPayload>("dashboard:update", payload);

    const lastUpdate = document.getElementById("last-update");
    if (lastUpdate) {
      lastUpdate.textContent = `Last update: ${new Date().toLocaleTimeString()}`;
    }
  },
);

// ── History ──────────────────────────────────────────────────
const historyChart = new HistoryChart("history-chart");
const btnLoad = document.getElementById(
  "btn-load-history",
) as HTMLButtonElement;
const inputStart = document.getElementById("hist-start") as HTMLInputElement;
const inputEnd = document.getElementById("hist-end") as HTMLInputElement;

// Default: last 1 hour
const now = new Date();
const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
inputStart.value = oneHourAgo.toISOString().slice(0, 16);
inputEnd.value = now.toISOString().slice(0, 16);

btnLoad.addEventListener("click", async () => {
  btnLoad.textContent = "Loading...";
  btnLoad.style.opacity = "0.5";
  btnLoad.disabled = true;

  const startTs = new Date(inputStart.value).getTime();
  const endTs = new Date(inputEnd.value).getTime();

  // Fetch vitals and ECG history in parallel
  const [vitalsData, ecgData] = await Promise.all([
    firebaseService.fetchHistory<any>(
      "/patients/Patient_02/history/vitals",
      startTs,
      endTs,
    ),
    firebaseService.fetchHistory<any>(
      "/patients/Patient_02/history/ecg_processed",
      startTs,
      endTs,
    ),
  ]);

  console.log(
    `Fetched ${vitalsData.length} vitals records, ${ecgData.length} ECG records.`,
  );
  historyChart.updateData(vitalsData, ecgData);

  btnLoad.textContent = "Load Data";
  btnLoad.style.opacity = "1";
  btnLoad.disabled = false;
});

// ── Patient name editing ────────────────────────────────────
const PATIENT_PATH = "/patients/Patient_02";
const nameDisplay = document.getElementById(
  "patient-name-display",
) as HTMLHeadingElement;
const editBtn = document.getElementById("edit-name-btn") as HTMLButtonElement;

async function loadPatientName(): Promise<void> {
  const name = await firebaseService.getValue<string>(
    `${PATIENT_PATH}/profile/name`,
  );
  nameDisplay.textContent = `Patient: ${name ?? "Real"}`;
}

editBtn.addEventListener("click", async () => {
  const current = nameDisplay.textContent?.replace("Patient: ", "") ?? "";
  const newName = prompt("Enter patient name:", current);
  if (newName === null || newName.trim() === "") return;

  await firebaseService.setValue(
    `${PATIENT_PATH}/profile/name`,
    newName.trim(),
  );
  nameDisplay.textContent = `Patient: ${newName.trim()}`;
});

loadPatientName();
