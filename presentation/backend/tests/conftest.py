"""Legacy endpoint-contract tests run under an explicit test-only principal.

Authentication-specific tests do not receive this override.
"""
import pytest
from presentation.backend.app.main import app
from presentation.backend.app.authentication import current_principal
from presentation.backend.app.authorization import Principal

@pytest.fixture(autouse=True)
def isolated_presentation_storage(tmp_path, monkeypatch):
    """No test may write to the operator's real SQLite store or image folders.

    Every store (incidents, Evidence, images, audit, history) derives from
    DCG_PRESENTATION_DB; tests that set their own path still override this.
    """
    monkeypatch.setenv("DCG_PRESENTATION_DB", str(tmp_path / "presentation.sqlite3"))
    # The Face authorization check keeps one shared Neo4j driver; never let a
    # test's fake (or a real connection) carry over into another test.
    from presentation.backend.app import face_zone_authorization
    monkeypatch.setattr(face_zone_authorization, "_driver", None)

@pytest.fixture(autouse=True)
def authorized_legacy_test(request):
    if request.node.path.name not in {
        "test_api_contract.py", "test_custom_scenarios.py", "test_incident_flow.py"
    }:
        yield
        return
    app.dependency_overrides[current_principal] = lambda: Principal(
        "contract-test", frozenset({"administrator"}),
        frozenset({"ZONE-A", "ZONE-B", "ZONE-C"}),
    )
    try:
        yield
    finally:
        app.dependency_overrides.pop(current_principal, None)
