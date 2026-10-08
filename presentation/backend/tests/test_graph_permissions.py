"""Permission-aware graph projection tests; no Neo4j connection needed."""
from presentation.backend.app.authorization import Principal
from presentation.backend.app.graph_view import project_node

class Node(dict):
    def __init__(self, label, **properties):
        super().__init__(properties)
        self.labels = {label}
        self.element_id = "synthetic-node-1"

def actor(role, zone="ZONE-B"):
    return Principal("test-operator", frozenset({role}), frozenset({zone}))

def test_viewer_cannot_receive_source_ip():
    node = Node("SourceIP", address="203.0.113.77")
    result = project_node(node, actor("viewer"), "ZONE-B")
    assert result["restricted"] is True
    assert result["properties"] == {}
    assert "203.0.113.77" not in str(result)

def test_security_operator_sees_source_ip_only_in_assigned_zone():
    node = Node("SourceIP", address="203.0.113.77")
    assert project_node(node, actor("security_operator"), "ZONE-B")["properties"]["address"] == "203.0.113.77"
    assert project_node(node, actor("security_operator"), "ZONE-A")["properties"] == {}

def test_person_identity_role_boundaries():
    node = Node("Person", person_id="P001", secret_note="must-not-leak")
    assert project_node(node, actor("security_operator"), "ZONE-B")["properties"] == {}
    result = project_node(node, actor("safety_operator"), "ZONE-B")
    assert result["properties"] == {"person_id": "P001"}

def test_administrator_sees_allowlisted_fields_only():
    node = Node("SourceIP", address="203.0.113.77", internal_secret="never")
    result = project_node(node, actor("administrator"), "ZONE-B")
    assert result["properties"] == {"address": "203.0.113.77"}
    assert "never" not in str(result)

def test_unknown_role_restricted():
    node = Node("Person", person_id="P001")
    assert project_node(node, actor("unknown"), "ZONE-B")["restricted"]
