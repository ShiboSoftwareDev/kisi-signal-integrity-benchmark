"""Plot recomputed absolute-voltage eyes; keep invalid copper clearly labeled."""

import os
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".cache/matplotlib")
)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plot(summary, output_dir):
    output_dir = Path(output_dir)
    fig, axes = plt.subplots(3, 2, figsize=(12, 11), constrained_layout=True)
    for row, (level, result) in enumerate(summary["examples"].items()):
        with np.load(output_dir / level / "comparison.npz") as data:
            for col, tool in enumerate(("our", "kisi")):
                ax = axes[row, col]
                traces = data[tool + "_eye"]
                for lane, values in enumerate(traces):
                    ax.plot(
                        np.arange(values.shape[1]) / 256,
                        values.T,
                        color=("tab:blue", "tab:orange")[lane],
                        alpha=0.07,
                        lw=0.7,
                    )
                invalid = bool(result["kicad_shorts"])
                suffix = "\nINVALID PCB: net-label diagnostic only" if invalid else ""
                ax.set_title(
                    f'{level} — {"Pipeline" if tool == "our" else "Kisi"}{suffix}',
                    fontsize=10,
                    color="firebrick" if invalid else "black",
                )
                ax.set(xlabel="Time (UI)", ylabel="Received voltage (V)", xlim=(0, 2))
                ax.grid(alpha=0.2)
    fig.savefig(output_dir / "eyes.png", dpi=150)
    plt.close(fig)
