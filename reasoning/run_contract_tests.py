"""
DC-Guardian Reasoning
Consolidated Contract Test Runner

Runs Reasoning contracts in dependency order and stops
immediately on the first failure.

The same Python interpreter used to launch this script is
used for every child test.
"""

from pathlib import Path
import os
import subprocess
import sys
import time


# ============================================================
# Project root
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)


# ============================================================
# Contract suite
# ============================================================

CONTRACTS = [

    # --------------------------------------------------------
    # Common schema
    # --------------------------------------------------------

    (
        "COMMON SCHEMA",
        "Common Event Schema",
        [
            "reasoning/validate_event_schema.py"
        ],
    ),

    # --------------------------------------------------------
    # Adapters
    # --------------------------------------------------------

    (
        "ADAPTERS",
        "SSH Adapter",
        [
            "reasoning/test_ssh_event_adapter.py"
        ],
    ),

    (
        "ADAPTERS",
        "Maintenance Adapter",
        [
            "reasoning/test_maintenance_event_adapter.py"
        ],
    ),

    (
        "ADAPTERS",
        "Environmental Adapter",
        [
            "reasoning/test_environmental_event_adapter.py"
        ],
    ),

    (
        "ADAPTERS",
        "Face Adapter",
        [
            "reasoning/test_face_event_adapter.py"
        ],
    ),

    (
        "ADAPTERS",
        "PPE Adapter",
        [
            "reasoning/test_ppe_event_adapter.py"
        ],
    ),

    # --------------------------------------------------------
    # Topology
    # --------------------------------------------------------

    (
        "TOPOLOGY",
        "SSH Topology",
        [
            "reasoning/topology/test_topology_mapper.py"
        ],
    ),

    (
        "TOPOLOGY",
        "Maintenance Topology",
        [
            "reasoning/topology/test_maintenance_topology_mapper.py"
        ],
    ),

    (
        "TOPOLOGY",
        "Environmental Topology",
        [
            "reasoning/topology/test_environmental_topology_mapper.py"
        ],
    ),

    (
        "TOPOLOGY",
        "Face Topology",
        [
            "reasoning/topology/test_face_topology_mapper.py"
        ],
    ),

    (
        "TOPOLOGY",
        "PPE Topology",
        [
            "reasoning/topology/test_ppe_topology_mapper.py"
        ],
    ),

    # --------------------------------------------------------
    # Graph ingestion
    # --------------------------------------------------------

    (
        "GRAPH",
        "SSH Event Ingestion",
        [
            "reasoning/graph/test_event_ingestion.py"
        ],
    ),

    (
        "GRAPH",
        "Maintenance Event Ingestion",
        [
            "reasoning/graph/test_maintenance_event_ingestion.py"
        ],
    ),

    (
        "GRAPH",
        "Environmental Event Ingestion",
        [
            "reasoning/graph/test_environmental_event_ingestion.py"
        ],
    ),

    (
        "GRAPH",
        "Face Event Ingestion",
        [
            "reasoning/graph/test_face_event_ingestion.py"
        ],
    ),

    (
        "GRAPH",
        "PPE Event Ingestion",
        [
            "reasoning/graph/test_ppe_event_ingestion.py"
        ],
    ),

    # --------------------------------------------------------
    # Correlation
    # --------------------------------------------------------

    (
        "CORRELATION",
        "Pairwise Correlation",
        [
            "reasoning/correlation/test_correlation_engine.py"
        ],
    ),

    (
        "CORRELATION",
        "Pairwise Persistence",
        [
            "reasoning/correlation/test_correlation_store.py"
        ],
    ),

    (
        "CORRELATION",
        "Three-Domain Correlation",
        [
            "reasoning/correlation/test_three_domain_correlation.py"
        ],
    ),

    (
        "CORRELATION",
        "Three-Domain Persistence",
        [
            "reasoning/correlation/test_three_domain_correlation_store.py"
        ],
    ),

    (
        "CORRELATION",
        "Face + Cyber Correlation",
        [
            "reasoning/correlation/test_face_cyber_correlation.py"
        ],
    ),

    (
        "CORRELATION",
        "Face + Cyber Persistence",
        [
            "reasoning/correlation/test_face_cyber_correlation_store.py"
        ],
    ),

    (
        "CORRELATION",
        "PPE + Face Correlation",
        [
            "reasoning/correlation/test_ppe_face_correlation.py"
        ],
    ),

    (
        "CORRELATION",
        "PPE + Face Persistence",
        [
            "reasoning/correlation/test_ppe_face_correlation_store.py"
        ],
    ),


]


# ============================================================
# Helpers
# ============================================================

def print_separator():

    print(
        "=" * 60
    )


def run_contract(
    index,
    total,
    section,
    name,
    command_parts,
):

    command = [
        sys.executable,
        *command_parts,
    ]


    print()
    print_separator()

    print(
        f"[{index:02d}/{total:02d}] "
        f"{section} :: {name}"
    )

    print_separator()

    print(
        "Command:",
        " ".join(
            command
        )
    )

    print()


    start = time.perf_counter()


    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(PROJECT_ROOT)
        if not existing_pythonpath
        else str(PROJECT_ROOT) + os.pathsep + existing_pythonpath
    )
    # Libraries such as DeepFace print emoji; without this, redirected output
    # on Windows falls back to cp1252 and the contract crashes on import.
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=env,
    )


    elapsed = (
        time.perf_counter()
        - start
    )


    if (
        result.returncode
        != 0
    ):

        print()

        print_separator()

        print(
            f"FAIL: {name}"
        )

        print(
            f"Exit code: "
            f"{result.returncode}"
        )

        print(
            f"Runtime: "
            f"{elapsed:.2f} seconds"
        )

        print_separator()


        return False, elapsed


    print()

    print(
        f"PASS: {name} "
        f"({elapsed:.2f}s)"
    )


    return True, elapsed


# ============================================================
# Main
# ============================================================

def main():

    total = len(
        CONTRACTS
    )


    print()
    print_separator()

    print(
        "DC-GUARDIAN REASONING CONTRACT SUITE"
    )

    print_separator()


    print(
        "Python:"
    )

    print(
        sys.executable
    )


    print(
        "\nProject root:"
    )

    print(
        PROJECT_ROOT
    )


    print(
        "\nContracts:",
        total
    )


    print(
        "\nIMPORTANT:"
    )

    print(
        "Neo4j must be running for graph and "
        "correlation contracts."
    )


    suite_start = (
        time.perf_counter()
    )


    passed = 0

    timings = []


    current_section = None


    for index, (
        section,
        name,
        command_parts,
    ) in enumerate(
        CONTRACTS,
        start=1,
    ):

        if (
            section
            != current_section
        ):

            current_section = (
                section
            )

            print()

            print(
                f"\n--- {section} ---"
            )


        success, elapsed = run_contract(
            index,
            total,
            section,
            name,
            command_parts,
        )


        timings.append(
            (
                name,
                success,
                elapsed,
            )
        )


        if not success:

            suite_elapsed = (
                time.perf_counter()
                - suite_start
            )


            print()
            print_separator()

            print(
                "REASONING CONTRACT SUITE FAILED"
            )

            print_separator()


            print(
                f"Passed before failure: "
                f"{passed}/{total}"
            )


            print(
                "Failed contract:",
                name
            )


            print(
                f"Total runtime: "
                f"{suite_elapsed:.2f} seconds"
            )


            print()
            print(
                "Fix the failing contract before "
                "continuing to later Reasoning layers."
            )


            return 1


        passed += 1


    # ========================================================
    # Final summary
    # ========================================================

    suite_elapsed = (
        time.perf_counter()
        - suite_start
    )


    print()
    print_separator()

    print(
        "REASONING CONTRACT TIMINGS"
    )

    print_separator()


    for index, (
        name,
        success,
        elapsed,
    ) in enumerate(
        timings,
        start=1,
    ):

        status = (
            "PASS"
            if success
            else "FAIL"
        )


        print(
            f"[{index:02d}/{total:02d}] "
            f"{name:<32} "
            f"{status:<4} "
            f"{elapsed:>8.2f}s"
        )


    print()
    print_separator()

    print(
        f"REASONING CONTRACTS PASSED: "
        f"{passed}/{total}"
    )

    print(
        f"Total runtime: "
        f"{suite_elapsed:.2f} seconds"
    )

    print_separator()


    print()
    print(
        "PASS: Common Event Schema."
    )

    print(
        "PASS: Cybersecurity integration."
    )

    print(
        "PASS: Predictive-maintenance integration."
    )

    print(
        "PASS: Environmental integration."
    )

    print(
        "PASS: Face-recognition integration."
    )

    print(
        "PASS: PPE safety integration."
    )

    print(
        "PASS: Neo4j graph integration."
    )

    print(
        "PASS: Pairwise correlation."
    )

    print(
        "PASS: Three-domain correlation."
    )

    print(
        "PASS: Correlation persistence."
    )

    print(
        "PASS: Physical-security cross-domain correlation."
    )

    print(
        "PASS: Safety + physical-security "
         "cross-domain correlation."
    )


    print()
    print_separator()

    print(
        "DC-GUARDIAN REASONING "
        "FOUNDATION + FACE + PPE "
        "CROSS-DOMAIN INTEGRATION PASSED"
    )

    print_separator()


    return 0


def remove_test_graph_artifacts():
    """Delete contract-test Events/Correlations from the shared graph.

    Contracts share the operator's Neo4j database, and *_store contracts reuse
    nodes left by the preceding contract, so cleanup runs once after the whole
    suite. Only nodes with the test-only SCENARIO- prefix are removed; topology
    (Server, Rack, Zone, Person, Camera) and DCG-* dashboard data are untouched.
    Set DCG_KEEP_TEST_GRAPH=1 to keep them for debugging.
    """

    if os.environ.get("DCG_KEEP_TEST_GRAPH") == "1":
        print("Test graph artifacts kept (DCG_KEEP_TEST_GRAPH=1).")
        return

    sys.path.insert(0, str(PROJECT_ROOT))

    from reasoning.graph.ingest_event import (
        NEO4J_DATABASE,
        create_driver,
    )

    try:
        driver = create_driver()
        try:
            with driver.session(database=NEO4J_DATABASE) as session:
                deleted = session.run(
                    """
                    MATCH (n)
                    WHERE (n:Event OR n:Correlation)
                      AND n.scenario_id STARTS WITH 'SCENARIO-'
                    DETACH DELETE n
                    RETURN count(n) AS deleted
                    """
                ).single()["deleted"]
        finally:
            driver.close()
    except Exception as exc:
        print(f"WARNING: test graph cleanup failed: {type(exc).__name__}")
        return

    print(f"Removed {deleted} contract-test graph nodes.")


if __name__ == "__main__":

    try:
        exit_code = main()
    finally:
        remove_test_graph_artifacts()

    raise SystemExit(
        exit_code
    )
