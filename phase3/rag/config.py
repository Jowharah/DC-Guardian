"""Configuration for DC-GUARDIAN Phase 3.1 retrieval preparation."""

# Word-count bounds are an initial retrieval experiment, not a claim that one
# chunk size is universally optimal. Evaluation cases remain frozen while
# these values are tuned.
TARGET_CHUNK_WORDS = 850
MAX_CHUNK_WORDS = 1000
OVERLAP_WORDS = 100
MIN_CHUNK_WORDS = 80

# Explicit retrieval scope. Locked/clean sources remain complete; this only
# controls which material is eligible for the active retrieval corpus.
RETRIEVAL_SCOPE = {
    "NIST-SP-800-53R5-PE": {
        "mode": "text_markers",
        "markers": [
            "PE-2 PHYSICAL ACCESS AUTHORIZATIONS",
            "PE-3 PHYSICAL ACCESS CONTROL",
            "PE-6 MONITORING PHYSICAL ACCESS",
        ],
        "reason": (
            "DC-GUARDIAN v1 physical-security retrieval is scoped to "
            "authorization, access control, and physical-access monitoring."
        ),
    },
}
