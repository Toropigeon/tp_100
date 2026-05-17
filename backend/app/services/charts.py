from pathlib import Path
import os
import re

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from app.services.thresholds import find_rule


def safe_filename(value: str) -> str:
    value = re.sub(r"[^a-zA-Zа-яА-Я0-9_-]+", "_", value).strip("_")
    return value[:80] or "chart"


def build_charts(dataframe: pd.DataFrame, time_column: str | None, numeric_columns: list[str], output_dir: Path) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    x_values = dataframe[time_column] if time_column else dataframe.index
    charts: list[dict] = []

    for column in numeric_columns:
        rule = find_rule(column)
        fig, ax = plt.subplots(figsize=(10, 4.8), dpi=130)
        ax.plot(x_values, dataframe[column], color="#2563eb", linewidth=2)
        if rule:
            ax.axhline(
                y=rule.nominal,
                color="#dc2626",
                linestyle="--",
                linewidth=1.5,
                label=f"Эталон: {rule.nominal:g} {rule.unit}",
            )
            ax.legend(loc="best")
        ax.set_title(column)
        ax.set_xlabel("Время" if time_column else "Номер измерения")
        ax.set_ylabel("Значение")
        ax.grid(True, alpha=0.28)
        fig.autofmt_xdate()
        fig.tight_layout()

        filename = f"{safe_filename(column)}.png"
        path = output_dir / filename
        fig.savefig(path)
        plt.close(fig)
        charts.append({"name": filename, "parameter": column})

    return charts
