"""No fabricated companion events or replacement of the frozen detector assessment."""
from presentation.backend.app.ssh_graph_ingestion import prepare_mapped_ssh

def test_mapping_preserves_original_detector_evidence():
    assessment = {
        "source_ip":"192.0.2.10","window_start":"2000-12-10T07:10:00",
        "window_end":"2000-12-10T07:15:00","anomaly_detected":True,
        "detector_votes":2,"detector_combination":"RULE+AE",
        "confidence":"MEDIUM","evidence_state":"HIGH_CONFIDENCE_ANOMALY",
        "explicit_security_signal":False,"security_signals":[],
        "rule":{},"isolation_forest":{},"autoencoder":{},
        "evidence":{"failed_login_count":6},
    }
    mapped=prepare_mapped_ssh("SSH-EVT-"+"A"*32,assessment,"SRV-A1-01","ZONE-A")
    assert mapped["domain"]=="CYBERSECURITY"
    assert mapped["entities"]["source_ip"]=="192.0.2.10"
    assert mapped["entities"]["server_id"]=="SRV-A1-01"
    assert mapped["evidence"]["behavior"]["failed_login_count"]==6
    assert mapped["provenance"]["original_event_id"]=="SSH-EVT-"+"A"*32
    assert mapped["provenance"]["synthetic_mapping"] is True
    assert mapped["timestamp"].startswith("2000-12-10T07:10:00")
    assert assessment["window_start"]=="2000-12-10T07:10:00"

def test_mismatched_server_zone_rejected():
    assessment={}
    try:
        prepare_mapped_ssh("SSH-EVT-"+"A"*32,assessment,"SRV-B1-01","ZONE-A")
    except ValueError:
        pass
    else:
        raise AssertionError("Mismatched zone accepted")
