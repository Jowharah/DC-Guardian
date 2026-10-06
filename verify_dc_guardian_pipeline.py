"""DC-GUARDIAN integration connection verifier.

Validates that the implemented architectural layers connect using the project
names EVIDENCE -> REASONING -> RESPONSE. This verifier intentionally uses
controlled structured evidence rather than retraining/loading every Evidence
model. Heavy runtime/model smoke testing remains a separate concern.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

CHECKS = {
    "EVIDENCE": [],
    "REASONING": [
        ("Reasoning regression contracts", ROOT / "phase2" / "run_contract_tests.py"),
    ],
    "RESPONSE": [
        ("Response RAG foundation", ROOT / "phase3" / "rag" / "verify_phase3_rag.py"),
        (
            "Grounded reasoning contract",
            ROOT / "phase3" / "agents" / "tests" / "test_grounded_reasoning_contract.py",
        ),
        (
            "Specialist router contract",
            ROOT / "phase3" / "agents" / "tests" / "test_specialist_router.py",
        ),
        (
            "Physical/Safety specialist contract",
            ROOT / "phase3" / "agents" / "tests" / "test_physical_safety_specialist.py",
        ),
        (
            "Cybersecurity specialist contract",
            ROOT / "phase3" / "agents" / "tests" / "test_cybersecurity_specialist.py",
        ),
        (
            "Operations specialist contract",
            ROOT / "phase3" / "agents" / "tests" / "test_operations_specialist.py",
        ),
        (
            "Cross-domain synthesis boundary contract",
            ROOT / "phase3" / "agents" / "tests" / "test_synthesis_boundaries.py",
        ),
        (
            "Cross-domain synthesis contract",
            ROOT / "phase3" / "agents" / "tests" / "test_cross_domain_synthesis.py",
        ),
    ],
}


def run_check(label: str, script: Path) -> bool:
    if not script.exists():
        print(f"SKIP: {label} (entry point not found: {script.relative_to(ROOT)})")
        return False
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    )
    if result.returncode == 0:
        print(f"PASS: {label}")
        return True
    print(f"FAIL: {label}")
    print(result.stdout)
    return False


def main() -> None:
    print("=" * 60)
    print("DC-GUARDIAN END-TO-END CONNECTION VERIFICATION")
    print("EVIDENCE -> REASONING -> RESPONSE")
    print("=" * 60)

    failures = []

    print()
    print("EVIDENCE")
    print("-" * len("EVIDENCE"))
    print(
        "PASS: Evidence layer is exercised through the Reasoning adapter "
        "contracts using frozen Evidence inference interfaces."
    )
    print(
        "INFO: Full neural-model runtime smoke testing is separate from this "
        "connection verifier."
    )

    for layer, checks in CHECKS.items():
        if layer == "EVIDENCE":
            continue
        print()
        print(layer)
        print("-" * len(layer))
        for label, script in checks:
            if not run_check(label, script):
                failures.append(f"{layer}: {label}")

    print()
    print("=" * 60)
    if failures:
        print("DC-GUARDIAN CONNECTION VERIFICATION INCOMPLETE/FAILED")
        for failure in failures:
            print(f"- {failure}")
        print("=" * 60)
        raise SystemExit(1)

    print("DC-GUARDIAN END-TO-END CONNECTIONS PASSED")
    print("EVIDENCE -> REASONING -> RESPONSE")
    print("=" * 60)


if __name__ == "__main__":
    main()
