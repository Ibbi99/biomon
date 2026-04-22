// src/ui/components/VitalCard.ts
//
// Manages a single vital sign card in the patient dashboard (HR, SpO2, Temp, AI HR).
// Each card has a value display element and an optional wrapper for danger styling.
//
// Usage:
//   const hrCard = new VitalCard("hr");   // looks for <div id="val-hr">
//   hrCard.setValue(72, 0);               // displays "72"
//   hrCard.setDanger(true);              // adds "danger" CSS class (red highlight)

export class VitalCard {
  private readonly valueElement: HTMLElement;
  private readonly cardElement: HTMLElement | null;

  /**
   * @param id - The vital sign identifier. Looks for an element with id="val-{id}".
   *             Expected ids: "hr", "spo2", "temp", "ai"
   */
  constructor(private readonly id: string) {
    const value = document.getElementById(`val-${id}`);

    if (!value) {
      throw new Error(`VitalCard value element missing for id: val-${id}`);
    }

    this.valueElement = value;

    // Walk up the DOM to find the parent .card wrapper for danger styling
    this.cardElement = value.closest(".card");
  }

  /**
   * Updates the displayed value.
   * Shows "--" if the value is null, undefined, or NaN.
   *
   * @param value    - The numeric value to display (e.g. 72.5)
   * @param decimals - Number of decimal places to show (0 for HR, 1 for Temp)
   */
  public setValue(value: number | null | undefined, decimals = 0): void {
    if (value === null || value === undefined || Number.isNaN(value)) {
      this.valueElement.textContent = "--";
      return;
    }

    this.valueElement.textContent = value.toFixed(decimals);
  }

  /**
   * Toggles the danger visual state on the card wrapper.
   * When enabled, adds the "danger" CSS class which turns the card red.
   *
   * @param enabled - true to show danger state, false to remove it
   */
  public setDanger(enabled: boolean): void {
    this.cardElement?.classList.toggle("danger", enabled);
  }
}