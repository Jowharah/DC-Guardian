import pytest
from fastapi import HTTPException
from presentation.backend.app.authorization import Principal
from presentation.backend.app.human_review_audit import audit_integrity

def test_non_admin_denied():
    principal=Principal("viewer",frozenset({"viewer"}),frozenset({"ZONE-A"}))
    with pytest.raises(HTTPException) as error:
        audit_integrity(principal)
    assert error.value.status_code==403

def test_non_admin_operator_denied():
    principal=Principal("operator",frozenset({"security_operator"}),frozenset({"ZONE-A"}))
    with pytest.raises(HTTPException) as error:
        audit_integrity(principal)
    assert error.value.status_code==403
