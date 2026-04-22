import { EventBus } from "@app/EventBus";
import { DashboardController } from "@app/DashboardController";
import { FirebaseService } from "@core/services/FirebaseService";
import { PatientStreamService } from "@core/services/PatientStreamService";
import "@ui/styles/style.css";

const eventBus = new EventBus();
const firebaseService = new FirebaseService();
const dashboardController = new DashboardController(eventBus);
const patientStreamService = new PatientStreamService(
  firebaseService,
  eventBus,
  "Patient_01"
);

dashboardController.bind();
patientStreamService.start();

const themeToggle = document.getElementById("theme-toggle");

if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    const html = document.documentElement;
    const currentTheme = html.getAttribute("data-theme") ?? "dark";
    const nextTheme = currentTheme === "dark" ? "light" : "dark";

    html.setAttribute("data-theme", nextTheme);
    themeToggle.textContent = nextTheme === "dark" ? "🌙" : "☀️";
  });
}