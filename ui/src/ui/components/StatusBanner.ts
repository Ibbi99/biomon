/**
 * Manages the footer status bar shown at the bottom of each patient page.
 * Displays the clinical alert message (e.g. "Critical oxygen saturation") and the timestamp of the last data update.
 * @author Cristina Vedinas
 */

export class StatusBanner {
  private readonly messageElement: HTMLElement;
  private readonly lastUpdateElement: HTMLElement;

  constructor() {
    const message = document.getElementById("clinical-message");
    const lastUpdate = document.getElementById("last-update");

    if (!message || !lastUpdate) {
      throw new Error("Status banner elements are missing from the DOM");
    }

    this.messageElement = message;
    this.lastUpdateElement = lastUpdate;
  }

  /**
   * Updates the status banner with new data from the dashboard payload.
   *
   * @param status    - "STABLE" | "WARNING" | "CRITICAL" — used as a CSS class
   * @param message   - Human-readable alert message from the Python processor
   * @param timestamp - Unix timestamp in milliseconds of the last processed update
   */
  public update(status: string, message: string, timestamp: number): void {
    this.messageElement.textContent = message || "No message";

    // Apply status as CSS class so the message can be styled by severity
    // e.g. .clinical-message.critical { color: red }
    this.messageElement.className = `clinical-message ${status.toLowerCase()}`;

    this.lastUpdateElement.textContent = `Last update: ${
      timestamp ? new Date(timestamp).toLocaleString() : "--"
    }`;
  }
}
