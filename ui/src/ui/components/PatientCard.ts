/**
 * Renders a summary card for a single patient on the main overview page
 * Each card shows the patient name, current status, and basic vitals.
 * @author Cristina Vedinas
 */

export interface PatientCardProps {
  id: string;
  name: string;
  status: "STABLE" | "WARNING" | "CRITICAL";
  heartRate?: number;
  spo2?: number;
  temp?: number;
  link: string; // URL to navigate to on click (e.g. "patient_virtual.html")
}

export class PatientCard {
  private root: HTMLDivElement;

  /**
   * Creates the card DOM element and attaches a click handler for navigation.
   * @param props - Card configuration including patient name, status, and detail page link
   */
  constructor(private props: PatientCardProps) {
    this.root = document.createElement("div");
    this.root.className = `card patient-card ${props.status.toLowerCase()}`;
    this.root.innerHTML = `
      <h3>${props.name}</h3>
      <div class="vital">HR: <span>${props.heartRate ?? "--"}</span> BPM</div>
      <div class="vital">SpO2: <span>${props.spo2 ?? "--"}</span> %</div>
      <div class="vital">Temp: <span>${props.temp ?? "--"}</span> °C</div>
    `;

    // Navigate to the patient detail page on click
    this.root.addEventListener("click", () => {
      window.location.href = props.link;
    });
  }

  /**
   * Appends the card to a parent container element.
   * @param parent - The DOM element to append this card into
   */
  public render(parent: HTMLElement) {
    parent.appendChild(this.root);
  }

  /**
   * Updates the card's CSS class to reflect the new alert status.
   * This changes the card's border/background color (stable=green, warning=yellow, critical=red).
   *
   * @param status - New status from the dashboard payload
   */
  public updateStatus(status: "STABLE" | "WARNING" | "CRITICAL") {
    this.root.className = `card patient-card ${status.toLowerCase()}`;
  }

  /**
   * Updates the vital sign values displayed on the card.
   * Shows "--" for any value that is undefined.
   *
   * @param heartRate - BPM from the wrist sensor
   * @param spo2      - Oxygen saturation percentage
   * @param temp      - Body temperature in °C
   */
  public updateVitals(heartRate?: number, spo2?: number, temp?: number) {
    const spans = this.root.querySelectorAll("span");
    if (spans[0]) spans[0].textContent = heartRate?.toString() ?? "--";
    if (spans[1]) spans[1].textContent = spo2?.toString() ?? "--";
    if (spans[2]) spans[2].textContent = temp?.toString() ?? "--";
  }
}
