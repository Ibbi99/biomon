import json
import matplotlib.pyplot as plt
import numpy as np

# @author Cristina Vedinas

with open("ecg_sample.json") as f:
    data = json.load(f)

raw = data["raw"]
filtered = data["filtered"]
t = np.linspace(0, 1, len(raw))

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
ax1.plot(t, raw, color="gray", linewidth=0.8)
ax1.set_ylabel("ADC Value (0–4095)")
ax1.set_title("Raw ECG Signal")
ax1.grid(True, alpha=0.3)

ax2.plot(t, filtered, color="green", linewidth=0.8)
ax2.set_ylabel("Amplitude (normalised)")
ax2.set_xlabel("Time (s)")
ax2.set_title("Filtered ECG Signal")
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("raw_vs_filtered_ecg.png", dpi=150)
print("Saved raw_vs_filtered_ecg.png")
