"""
DC-Guardian Reasoning
Deterministic Cross-Domain Correlation Rules

This module defines the frozen vocabulary used by the
deterministic Reasoning layer correlation engine.

Environmental states are reserved for future integration.
"""


# ============================================================
# Correlation type
# ============================================================

CORRELATION_TYPE = (
    "CORRELATED_INFRASTRUCTURE_RISK"
)


# ============================================================
# Supported event domains
# ============================================================

SUPPORTED_DOMAINS = {
    "CYBERSECURITY",
    "MAINTENANCE",
    "ENVIRONMENTAL",
    "PHYSICAL_SECURITY",
    "SAFETY",
}

# ============================================================
# Physical-security correlation eligibility
# ============================================================

PHYSICAL_SECURITY_ABNORMAL_STATES = {
    "UNKNOWN_PERSON",
    "PPE_NON_COMPLIANT",
}


PHYSICAL_SECURITY_ABNORMAL_AUTHORIZATION = {
    "UNAUTHORIZED",
}

# ============================================================
# States considered abnormal for correlation
# ============================================================

ABNORMAL_STATES = {

    # --------------------------------------------------------
    # Cybersecurity
    # --------------------------------------------------------

    "EXPLICIT_SECURITY_EVENT",
    "HIGH_CONFIDENCE_ANOMALY",
    "ANOMALY_CANDIDATE",

    # --------------------------------------------------------
    # Predictive maintenance
    # --------------------------------------------------------

    "AT_RISK",

    # --------------------------------------------------------
    # Environmental
    #
    # Reserved vocabulary only.
    # The environmental detector contract is NOT frozen yet.
    # --------------------------------------------------------

    # Environmental
    "ENVIRONMENTAL_ANOMALY",
    "HIGH_TEMPERATURE",
    "HIGH_HUMIDITY",
    "LOW_HUMIDITY",
    "AIRFLOW_ANOMALY",
    "SMOKE_DETECTED",
    "WATER_LEAK_DETECTED",
    "COOLING_ANOMALY",

     # Safety / PPE
    "PPE_NON_COMPLIANT",
}


# ============================================================
# Correlation scopes
# ============================================================

CORRELATION_SCOPE_SERVER = (
    "SERVER"
)

CORRELATION_SCOPE_RACK = (
    "RACK"
)

CORRELATION_SCOPE_ZONE = (
    "ZONE"
)


CORRELATION_SCOPES = {
    CORRELATION_SCOPE_SERVER,
    CORRELATION_SCOPE_RACK,
    CORRELATION_SCOPE_ZONE,
}


# ============================================================
# Temporal correlation
# ============================================================

DEFAULT_CORRELATION_WINDOW_MINUTES = 15