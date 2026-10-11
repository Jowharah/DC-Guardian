from presentation.backend.app.unified_specialists import specialist_task

EDGES=[{"type":"FACE_SSH_CONTEXT","source_id":"C1"}]

def test_cyber_acknowledges_context_without_attribution():
    task=specialist_task("cybersecurity",{"ssh":{},"face":{}},EDGES)
    assert "controlled contextual" in task
    assert "Do not attribute SSH activity" in task
    assert "no contextual candidate" in task

def test_face_ssh_does_not_prompt_for_missing_ppe():
    task=specialist_task("physical_security",{"face":{},"ssh":{}},EDGES)
    assert "do not discuss" in task
    assert "missing PPE" in task
    assert "zone authorization" in task

def test_ppe_present_keeps_detector_caveats():
    task=specialist_task("physical_security",{"face":{},"ppe":{}},[])
    assert "detector outcomes" in task
    assert "physical absence" in task
