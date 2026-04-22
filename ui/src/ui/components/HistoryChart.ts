import { Chart, registerables } from "chart.js";
Chart.register(...registerables);

export class HistoryChart {
  private chart: Chart;

  constructor(canvasId: string) {
    const canvas = document.getElementById(canvasId) as HTMLCanvasElement;
    if (!canvas) throw new Error(`Canvas ${canvasId} not found`);

    // Initialize an empty chart with dark-theme styling
    this.chart = new Chart(canvas, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          { label: "Heart Rate (BPM)", data: [], borderColor: "#ff4444", tension: 0.3, pointRadius: 2 },
          { label: "SpO2 (%)", data: [], borderColor: "#00ccff", tension: 0.3, pointRadius: 2 },
          { label: "Temperature (°C)", data: [], borderColor: "#ffaa00", tension: 0.3, pointRadius: 2 }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: { ticks: { color: "#888" }, grid: { color: "#222" } },
          y: { ticks: { color: "#888" }, grid: { color: "#222" } }
        },
        plugins: {
          legend: { labels: { color: "#fff" } }
        }
      }
    });
  }

  /**
   * Parses the Firebase array and updates the chart
   */
  public updateData(vitalsHistory: any[]) {
    // Extract timestamps to create the X-axis labels
    const labels = vitalsHistory.map(entry => {
      return new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    });

    // Extract the actual values for the Y-axis
    const hrData = vitalsHistory.map(entry => entry.heart_rate || entry.verified_hr || null);
    const spo2Data = vitalsHistory.map(entry => entry.spo2 || null);
    const tempData = vitalsHistory.map(entry => entry.temp || null);

    // Apply to chart and re-render
    this.chart.data.labels = labels;
    this.chart.data.datasets[0].data = hrData;
    this.chart.data.datasets[1].data = spo2Data;
    this.chart.data.datasets[2].data = tempData;
    
    this.chart.update();
  }
}