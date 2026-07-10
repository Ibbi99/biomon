import { PatientCard } from "@ui/components/PatientCard";
import { FirebaseService } from "@core/services/FirebaseService";
import { setupThemeToggle } from "@ui/components/ThemeToggle";
import type { DashboardPayload } from "@core/models/DashboardPayload";

/**
 * Entry point for the main overview page (index.html).
 * Displays a summary card for each patient and subscribes to their live dashboard data to keep the cards up to date.
 * Clicking a patient card navigates to their detail page (patient_virtual.html or patient_real.html).
 * Patients:
 *   Patient_01 — virtual (simulated by Python patient_simulator.py)
 *   Patient_02 — real    (ESP32 physical device)
 * @author Cristina Vedinas
 */

setupThemeToggle();

const container = document.getElementById("patients-container");
if (!container) throw new Error("Patients container not found");

const lastUpdate = document.getElementById("last-update");

// Patient definitions — each entry creates a card and a Firebase subscription.
// NOTE: Firebase paths are case-sensitive — "dashboard" must be lowercase.
const patients = [
  {
    id: "real",
    name: "Patient Real",
    path: "/patients/Patient_02/dashboard/current",
    link: "patient_real.html",
  },
  {
    id: "virtual",
    name: "Patient Virtual",
    path: "/patients/Patient_01/dashboard/current",
    link: "patient_virtual.html",
  },
];

// Create and render a PatientCard for each patient
const cards: Record<string, PatientCard> = {};
patients.forEach((p) => {
  const card = new PatientCard({
    id: p.id,
    name: p.name,
    status: "STABLE",
    link: p.link,
  });
  card.render(container);
  cards[p.id] = card;
});

// Subscribe to Firebase for each patient and update their card on every change
const firebaseService = new FirebaseService();

patients.forEach((p) => {
  firebaseService.subscribe<DashboardPayload>(p.path, (payload) => {
    if (!payload) return;

    const card = cards[p.id];
    if (!card) return;

    card.updateStatus(payload.status);
    card.updateVitals(
      payload.heart_rate ?? undefined,
      payload.spo2 ?? undefined,
      payload.temp ?? undefined,
    );

    // Update the last-update timestamp whenever any patient sends new data
    if (lastUpdate && payload.timestamp) {
      lastUpdate.textContent = `Last update: ${new Date(payload.timestamp).toLocaleTimeString()}`;
    }
  });
});
