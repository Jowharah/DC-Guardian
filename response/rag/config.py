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
        "mode": "control_ranges",
        "controls": ["PE-2", "PE-3", "PE-6"],
        "reason": (
            "DC-GUARDIAN v1 physical-security retrieval is scoped to "
            "authorization, access control, and physical-access monitoring."
        ),
    },
}


# Local embedding baseline v1. Model ID and revision are persisted in the
# index-build manifest. Retrieval uses normalized embeddings + cosine score.
LOCAL_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LOCAL_EMBEDDING_REVISION = "main"
LOCAL_EMBEDDING_BATCH_SIZE = 32


# Calibrated on evaluation/abstention_calibration_cases.json v1.0 only.
# Do not retune from the frozen 18-case retrieval evaluation.
ABSTENTION_THRESHOLD = 0.5922
