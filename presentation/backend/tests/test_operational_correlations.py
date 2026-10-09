from presentation.backend.app.operational_correlations import correlate

def sample(time="2026-10-09T08:00:00Z",zone="ZONE-B"):
    m={"event_id":"MAINT-1","zone_id":zone,
       "assessment":{"assessment":"AT_RISK","observation_timestamp":time}}
    e={"event_id":"ENV-1","zone_id":zone,
       "assessment":{"assessment":"HIGH_TEMPERATURE","anomaly_detected":True,
                     "observation_timestamp":"2026-10-09T08:05:00Z"},
       "history":[{"timestamp":"2026-10-09T08:05:00Z"}],
       "workflow":{"reading_states":["HIGH_TEMPERATURE"]}}
    return m,e

def test_same_zone_within_window_correlates():
    m,e=sample()
    result=correlate([m],[e])
    assert len(result)==1
    assert result[0]["time_difference_seconds"]==300
    assert result[0]["decision_severity"] is None

def test_different_zone_not_correlated():
    m,e=sample(zone="ZONE-A")
    assert correlate([m],[e])==[]

def test_old_observation_not_correlated():
    m,e=sample(time="2026-01-12T00:00:00Z")
    assert correlate([m],[e])==[]

def test_normal_environment_not_correlated():
    m,e=sample()
    e["workflow"]["reading_states"]=["NORMAL"]
    assert correlate([m],[e])==[]
