"""
DC-Guardian Reasoning
Contract tests for the blind labelling pack and the label scorer.

Run from the repository root:
    python reasoning/uncertainty/labelling/test_labelling_pack.py
"""

from __future__ import annotations

import pytest  # noqa: E402

def test_labelling_pack_contract():
    """The original script checks, unchanged (converted 2026-10-12)."""

    import csv
    import json
    import sys
    import tempfile
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from reasoning.uncertainty.evaluate import load_scenarios  # noqa: E402
    from reasoning.uncertainty.labelling import build_labelling_pack as pack  # noqa: E402
    from reasoning.uncertainty.labelling import score_labels  # noqa: E402

    # Words that would reveal the author's answer or the dev/test split.
    LEAKS = ("ground_truth", "unrelated", "coincid", "narrative", "incident i", '"split"', "dev split", "test split")


    def _text(path):
        # Git checks text files out with CRLF on Windows and LF on Linux.
        return path.read_bytes().replace(b"\r\n", b"\n")


    def committed_pack_is_current():
        before = {p.name: _text(p) for p in pack.PACK_DIR.iterdir()}
        key_before = _text(pack.KEY_PATH)
        pack.build()
        after = {p.name: _text(p) for p in pack.PACK_DIR.iterdir()}
        assert before == after and key_before == _text(pack.KEY_PATH), \
            "Pack changed on rebuild; run build_labelling_pack.py and commit the result."


    def pack_reveals_no_answers():
        scenarios = load_scenarios()
        text = "\n".join(p.read_text(encoding="utf-8").lower() for p in pack.PACK_DIR.iterdir())
        for word in LEAKS:
            assert word not in text, f"Pack leaks '{word}'"
        for scenario in scenarios:
            assert scenario["title"].lower() not in text, f"Pack leaks title of {scenario['scenario_id']}"
            assert scenario["scenario_id"].lower() + "-" not in text, "Pack leaks original event IDs"


    def pack_covers_every_candidate_pair_once():
        rows = list(csv.DictReader(open(pack.PACK_DIR / "labels.csv", encoding="utf-8-sig")))
        pairs = [(r["event_a"], r["event_b"]) for r in rows]
        assert len(pairs) == len(set(pairs)) == 85
        assert all(not r["related"] for r in rows), "Pack must ship with empty labels"
        # Each row is self-contained: both events are described in the sheet itself.
        assert all(r["a_domain"] and r["b_domain"] and r["a_time"] and r["b_time"] for r in rows)


    def author_labels_reproduce_published_results():
        key = json.loads(pack.KEY_PATH.read_text(encoding="utf-8"))
        events = {e["event_id"]: e for s in load_scenarios() for e in s["events"]}
        rows = list(csv.DictReader(open(pack.PACK_DIR / "labels.csv", encoding="utf-8-sig")))
        for r in rows:
            a, b = events[key["events"][r["event_a"]]], events[key["events"][r["event_b"]]]
            same = a["ground_truth_incident"] is not None and a["ground_truth_incident"] == b["ground_truth_incident"]
            r["related"] = "Y" if same else "N"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "labels.csv"
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            result = score_labels.score(path)
        test = result["test"]
        assert test["agreement"] == 1.0 and test["cohens_kappa"] == 1.0 and not result["disagreements"]
        assert test["independent_labels"]["crisp"]["f1"] == 0.593
        assert test["independent_labels"]["bayesian"]["f1"] == 0.731


    def blank_labels_are_rejected():
        try:
            score_labels.score(pack.PACK_DIR / "labels.csv")
        except SystemExit as exc:
            assert "related must be Y or N" in str(exc)
        else:
            raise AssertionError("Blank labels.csv was accepted")


    TESTS = [committed_pack_is_current, pack_reveals_no_answers, pack_covers_every_candidate_pair_once,
             author_labels_reproduce_published_results, blank_labels_are_rejected]

    if True:  # the script's former __main__ block: runs under pytest and as a script
        for test in TESTS:
            test()
            print(f"PASS  {test.__name__}")
        print(f"\nLabelling pack contracts: {len(TESTS)} / {len(TESTS)} passing")


if __name__ == "__main__":
    test_labelling_pack_contract()
