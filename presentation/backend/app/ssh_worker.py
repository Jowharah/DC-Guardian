"""Bounded local OpenSSH log validation using the frozen SSH detector."""
import json
import sys
from evidence.ssh_anomaly.src.ssh_pipeline import SSHPipeline

def main():
    result = SSHPipeline(year=2000).process_log_file(sys.argv[1])
    assessments = SSHPipeline.security_relevant(result["assessments"])
    parsed = result["parsed_events"]
    summaries = []
    for item in assessments[:100]:
        source_ip = item.get("source_ip")
        matches = parsed.loc[parsed["source_ip"] == source_ip] if not parsed.empty and "source_ip" in parsed else None
        usernames = []
        if matches is not None and not matches.empty:
            usernames = sorted({str(v)[:80] for v in matches["username"].dropna().unique()})[:20]
        summaries.append({
            "source_ip": source_ip, "window_start": item.get("window_start"),
            "window_end": item.get("window_end"), "evidence_state": item["evidence_state"],
            "detector_votes": item.get("detector_votes"), "detector_combination": item.get("detector_combination"),
            "explicit_security_signal": item.get("explicit_security_signal"),
            "usernames": usernames,
            "evidence": item.get("evidence", {}),
        })
    print("DCG_SSH_RESULT=" + json.dumps({
        "parsed_count": len(parsed), "assessment_count": len(result["assessments"]),
        "security_relevant_count": len(assessments), "returned_count": len(summaries),
        "assessments": summaries, "truncated": len(assessments) > 100,
        "source_type": "OPERATOR_UPLOADED_OPENSSH_LOG",
        "pipeline_status": "SSH_ONLY_NOT_CORRELATED",
    }, allow_nan=False))

if __name__ == "__main__":
    main()
