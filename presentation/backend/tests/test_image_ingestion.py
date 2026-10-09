import asyncio
import json
from pathlib import Path
import pytest
from presentation.backend.app import continuous_ingestion as worker
from presentation.backend.app.authorization import Principal

OP=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-B"}))

def test_image_sources_require_explicit_retention(tmp_path):
    folder=tmp_path/"face";folder.mkdir()
    config=tmp_path/"ingestion.json"
    config.write_text(json.dumps({"sources":[{"kind":"face","directory":str(folder),
        "zone_id":"ZONE-B"}]}))
    with pytest.raises(ValueError,match="retain_approved_images"):
        worker.load_config(config)

def test_image_sources_accept_explicit_retention(tmp_path):
    folder=tmp_path/"ppe";folder.mkdir()
    config=tmp_path/"ingestion.json"
    config.write_text(json.dumps({"sources":[{"kind":"ppe","directory":str(folder),
        "zone_id":"ZONE-B","retain_approved_images":True}]}))
    result=worker.load_config(config)
    assert result[0]["kind"]=="ppe"

def test_ppe_dispatch_preserves_protected_observation(monkeypatch):
    from presentation.backend.app import ppe_image_validation as module
    async def fake(image,retain,zone,principal):
        assert image.content_type=="image/png"
        assert retain is True and zone=="ZONE-B"
        return {"observation":{"observation_id":"PPE-TEST"},"image_stored":True,
                "pipeline_status":"PPE_ONLY_NOT_INTEGRATED"}
    monkeypatch.setattr(module,"validate_ppe_image",fake)
    result=asyncio.run(worker.dispatch({"kind":"ppe","zone_id":"ZONE-B"},
                                       b"approved-test-image","test.png",OP))
    assert result["observation_id"]=="PPE-TEST"
    assert result["events"]==1

def test_face_dispatch_preserves_protected_observation(monkeypatch):
    from presentation.backend.app import face_image_validation as module
    async def fake(image,retain,zone,principal):
        assert image.content_type=="image/jpeg"
        assert retain is True and zone=="ZONE-B"
        return {"observation":{"observation_id":"FACE-TEST"},"image_stored":True,
                "pipeline_status":"FACE_ONLY_NOT_INTEGRATED"}
    monkeypatch.setattr(module,"validate_face",fake)
    result=asyncio.run(worker.dispatch({"kind":"face","zone_id":"ZONE-B"},
                                       b"approved-test-image","test.jpg",OP))
    assert result["observation_id"]=="FACE-TEST"
