"""Earthed-oven study - bar chart of the FAR 3 m upper-end margins per bonding concept (RN 100 ohm), with and without the FPC ferrite."""
import json
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from e0_common import *
r = load_results()["emission_earthed"]["rows"]
cfgs = list(r)
fig, axs = plt.subplots(1, 3, figsize=(17, 7), sharey=True)
for ax, lab in zip(axs, ("PCLK", "typical UI", "worst pattern")):
    y = np.arange(len(cfgs))
    a = [r[c][f"{lab} | FAR 3 m | no ferrite"]["margin_upper_end_dB"] for c in cfgs]
    b = [r[c][f"{lab} | FAR 3 m | ferrite"]["margin_upper_end_dB"] for c in cfgs]
    ax.barh(y + 0.2, a, 0.4, label="no ferrite"); ax.barh(y - 0.2, b, 0.4, label="FPC ferrite 150 ohm")
    ax.axvline(0, color="k"); ax.axvline(6, color="k", ls=":", label="6 dB")
    ax.set_title(f"{lab}: margin at the upper end of the band (dB)"); ax.grid(alpha=.3); ax.set_xlim(-60, 30)
axs[0].set_yticks(np.arange(len(cfgs))); axs[0].set_yticklabels(cfgs, fontsize=7); axs[0].legend(fontsize=7)
fig.suptitle("EN 55014-1 Table 9 FAR 3 m (PDF p.38): earthed oven, RN1-RN7 100 ohm, 2 x 100 nF at J10, bonding concepts")
fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "emission_earthed_concepts.png"), dpi=150)
print("ok")
