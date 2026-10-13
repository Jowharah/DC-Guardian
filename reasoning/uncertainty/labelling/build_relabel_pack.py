"""
DC-Guardian Reasoning
Blind pack for relabelling the 8 scenarios rewritten in scenario set v2.

Scenario set v2 replaced leak, smoke, airflow and cooling alerts (which the
environmental detector cannot produce) with temperature and humidity readings.
The relatedness of those 8 scenarios must be judged again, blind: the old
labels are not reused. This writes, with the same builder as the main pack:

    relabel_v2/pack/            INSTRUCTIONS.md, scenarios_blind.md, labels.csv
                                (neutral IDs R01-R08, readings shown)
    relabel_v2/pack_key.json    neutral ID -> v2 ID (NOT for the labeller)

The operator labels first (returned file saved as relabel_v2/operator_labels.csv;
build_scenarios_v2.py then turns the pair labels into incident labels). The
ChatGPT comparison is redone by pasting the same pack, never by an API call
from this repository.

Run from the repository root:
    python reasoning/uncertainty/labelling/build_relabel_pack.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reasoning.uncertainty.labelling import build_labelling_pack as pack  # noqa: E402
from reasoning.uncertainty.scenarios.build_scenarios_v2 import PENDING, REWRITES, V2_PATH  # noqa: E402

RELABEL_DIR = Path(__file__).resolve().parent / "relabel_v2"
PACK_DIR = RELABEL_DIR / "pack"
KEY_PATH = RELABEL_DIR / "pack_key.json"
SEED = 1013
VISIBLE = (*pack.VISIBLE[:pack.VISIBLE.index("source_class") + 1], "measurements",
           *pack.VISIBLE[pack.VISIBLE.index("source_class") + 1:])
GLOSSARY = {**pack.GLOSSARY,
            "ENVIRONMENTAL": "Environmental sensor or hardware telemetry measuring temperature and humidity; the reading "
                             "is shown. States: HIGH_TEMPERATURE (above 35 °C), HIGH_HUMIDITY (above 80 %), LOW_HUMIDITY "
                             "(below 20 %). Source ENVIRONMENTAL_SENSOR is a dedicated room sensor; HARDWARE_TELEMETRY "
                             "comes from a server's own sensors."}


def scenarios_to_relabel() -> list[dict]:
    v2 = json.loads(V2_PATH.read_text(encoding="utf-8"))["scenarios"]
    chosen = [s for s in v2 if s["scenario_id"] in REWRITES]
    assert len(chosen) == len(REWRITES)
    return chosen


def build() -> dict:
    return pack.build(scenarios_to_relabel(), pack_dir=PACK_DIR, key_path=KEY_PATH, prefix="R", seed=SEED,
                      visible=VISIBLE, glossary=GLOSSARY, duration="10–15 minutes")


if __name__ == "__main__":
    summary = build()
    print(f"Relabel pack written to {PACK_DIR.relative_to(PROJECT_ROOT)}: "
          f"{summary['scenarios']} scenarios, {summary['pairs']} pairs (status {PENDING}).")
    print(f"Key (keep away from the labeller): {KEY_PATH.relative_to(PROJECT_ROOT)}")
