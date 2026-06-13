// src/app/DashboardController.ts
import type { DashboardPayload } from "@core/models/DashboardPayload";
import { EventBus } from "@app/EventBus";
import { VitalCard } from "@ui/components/VitalCard";
import { StatusBanner } from "@ui/components/StatusBanner";
import { ECGCanvas } from "@ui/components/ECGCanvas";

export class DashboardController {
  private readonly hrCard = new VitalCard("hr");
  private readonly spo2Card = new VitalCard("spo2");
  private readonly tempCard = new VitalCard("temp");
  private readonly aiCard = new VitalCard("ai");
  private readonly statusBanner = new StatusBanner();
  private readonly ecgCanvas = new ECGCanvas("ecg-canvas");

  constructor(private readonly eventBus: EventBus) {}

  public bind(): void {
    this.eventBus.on<DashboardPayload>("dashboard:update", (payload) => {
      this.render(payload);
    });
  }

  private render(payload: DashboardPayload): void {
    const hr = payload.heart_rate ?? null;
    const spo2 = payload.spo2 ?? null;
    const temp = payload.temp ?? null;
    const verifiedHr = payload.verified_hr ?? null;

    this.hrCard.setValue(hr, 0);
    this.spo2Card.setValue(spo2, 0);
    this.tempCard.setValue(temp, 1);
    this.aiCard.setValue(verifiedHr, 0);

    this.hrCard.setDanger(hr !== null && (hr < 50 || hr > 120));
    this.spo2Card.setDanger(spo2 !== null && spo2 < 92);
    this.tempCard.setDanger(temp !== null && temp >= 38);

    this.statusBanner.update(
      payload.status ?? "STABLE",
      payload.message ?? "No message",
      payload.timestamp ?? 0,
    );

    const hasEcg =
      Array.isArray(payload.ecg_filtered) && payload.ecg_filtered.length > 0;

    // Cardiac arrest real: HR null, VerifiedHR null, SI SpO2 critic (<50)
    // HR=null fara SpO2 critic = senzor vitals deconectat, nu cardiac arrest
    const isFlat =
      hr === null && verifiedHr === null && (spo2 === null || spo2 < 50);

    if (isFlat) {
      const flatSignal = hasEcg
        ? payload.ecg_filtered!
        : new Array(200).fill(0);
      this.ecgCanvas.renderSignal(flatSignal, [], true);
    } else if (hasEcg) {
      this.ecgCanvas.renderSignal(
        payload.ecg_filtered!,
        payload.ecg_peaks ?? [],
        false,
      );
    }
  }
}
