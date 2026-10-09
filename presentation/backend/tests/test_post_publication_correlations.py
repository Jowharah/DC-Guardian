from presentation.backend.app.post_publication_correlations import matches, CheckRequest
from pydantic import ValidationError
import pytest

GROUP={"evidence":[{"kind":"face","observation_id":"F-1"},
                   {"kind":"ssh","observation_id":"S-1"},
                   {"kind":"ppe","observation_id":"P-1"}]}

def test_matches_only_exact_new_source():
    assert matches(GROUP,"face",{"F-1"})
    assert matches(GROUP,"ssh",{"S-1"})
    assert not matches(GROUP,"face",{"F-2"})
    assert not matches(GROUP,"ppe",{"F-1"})

def test_reject_empty_source_batch():
    with pytest.raises(ValidationError):
        CheckRequest(kind="ssh",observation_ids=[])

def test_reject_large_source_batch():
    with pytest.raises(ValidationError):
        CheckRequest(kind="ssh",observation_ids=["S-"+str(i) for i in range(101)])
