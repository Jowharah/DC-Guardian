"""Log parsing of the latency benchmark (the timed stages need local models and Neo4j)."""
from presentation.backend.validation import latency_benchmark as lb


def test_observed_latency_groups_requests_by_route_template(tmp_path, monkeypatch):
    (tmp_path / "api_access.log").write_text(
        "2026-10-13 09:00:00,000 INFO dcg.access: GET /api/v1/correlations/unified 200 100ms\n"
        "2026-10-13 09:00:01,000 INFO dcg.access: GET /api/v1/correlations/unified 200 300ms\n"
        "2026-10-13 09:00:02,000 INFO dcg.access: GET /api/v1/correlations/unified/DCG-UNIFIED-ABC/graph 200 40ms\n"
        "2026-10-13 09:00:03,000 INFO dcg.access: GET /api/v1/correlations/unified 401 2ms\n"
        "2026-10-13 09:00:04,000 INFO dcg.other: unrelated line\n", encoding="utf-8")
    monkeypatch.setattr(lb, "LOGS", tmp_path)
    observed = lb.observed_stage()
    assert observed["requests"] == 3  # the 401 and the unrelated line are not counted
    assert observed["routes"]["GET /api/v1/correlations/unified"]["median_ms"] == 200.0
    assert observed["routes"]["GET /api/v1/correlations/unified/{group_id}/graph"]["n"] == 1


def test_summary_reports_median_and_p95():
    s = lb.summary([float(x) for x in range(1, 21)])
    assert s["median_ms"] == 10.5 and s["p95_ms"] == 19.0 and s["n"] == 20
