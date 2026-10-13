"""
DC-Guardian Reasoning
Blind labelling pack for scenario set v2 (all 40 scenarios).

Scenario set v2 replaced the leak, smoke, airflow and cooling alerts (which
the environmental detector cannot produce) with temperature and humidity
readings, and its ground truth comes only from a full blind relabel: no v1
label is copied. This writes, with the same builder as the published v1 pack
(which stays byte-identical):

    pack_v2/            INSTRUCTIONS.md, scenarios_blind.md, labels.csv
                        (neutral IDs V01-V40, new shuffle, readings shown)
    pack_v2_key.json    neutral ID -> v2 ID (NOT for the labeller)

The operator's filled copy goes to results/operator-v2_labels.csv;
build_scenarios_v2.py turns its pair labels into incidents. The ChatGPT
comparison is redone by pasting this pack (results/llm-chatgpt-v2_labels.csv),
never by an API call from this repository.

Run from the repository root:
    python reasoning/uncertainty/labelling/build_pack_v2.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reasoning.uncertainty.labelling import build_labelling_pack as pack  # noqa: E402
from reasoning.uncertainty.scenarios.build_scenarios_v2 import PACK_V2_KEY, V2_PATH  # noqa: E402

PACK_DIR = Path(__file__).resolve().parent / "pack_v2"
KEY_PATH = PACK_V2_KEY
PREFIX = "V"
SEED = 20261014  # first seed after 2026-10-13 that puts no scenario in the same position as in the v1 pack
VISIBLE = (*pack.VISIBLE[:pack.VISIBLE.index("source_class") + 1], "measurements",
           *pack.VISIBLE[pack.VISIBLE.index("source_class") + 1:])
GLOSSARY = {**pack.GLOSSARY,
            "ENVIRONMENTAL": "Environmental sensor or hardware telemetry measuring temperature and humidity; the reading "
                             "is shown. States: HIGH_TEMPERATURE (above 35 °C), HIGH_HUMIDITY (above 80 %), LOW_HUMIDITY "
                             "(below 20 %). Source ENVIRONMENTAL_SENSOR is a dedicated room sensor; HARDWARE_TELEMETRY "
                             "comes from a server's own sensors."}


def build() -> dict:
    scenarios = json.loads(V2_PATH.read_text(encoding="utf-8"))["scenarios"]
    return pack.build(scenarios, pack_dir=PACK_DIR, key_path=KEY_PATH, prefix=PREFIX, seed=SEED,
                      visible=VISIBLE, glossary=GLOSSARY)


if __name__ == "__main__":
    summary = build()
    print(f"v2 pack written to {PACK_DIR.relative_to(PROJECT_ROOT)}: "
          f"{summary['scenarios']} scenarios, {summary['pairs']} pairs.")
    print(f"Key (keep away from the labeller): {KEY_PATH.relative_to(PROJECT_ROOT)}")
