"""Turn pip-audit JSON into GitHub annotations and fail on any known vulnerability.

Job logs are only visible to repository admins; annotations are visible on the
run page, so every finding names its package, version, advisory and fix.
"""
import json
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "pip-audit.json")
if not path.is_file():
    print("::error title=pip-audit::pip-audit produced no report (it failed before auditing).")
    sys.exit(1)
report = json.loads(path.read_text(encoding="utf-8"))
findings = [(dep["name"], dep.get("version"), vuln["id"], vuln.get("fix_versions") or [])
            for dep in report.get("dependencies", []) for vuln in dep.get("vulns", [])]
skipped = [(dep["name"], dep.get("skip_reason", "")) for dep in report.get("dependencies", []) if dep.get("skip_reason")]
for name, version, advisory, fixes in findings:
    print(f"::error title=Vulnerable dependency {name} {version}::{advisory}; fixed in {', '.join(fixes) or 'no fixed release yet'}")
for name, reason in skipped:
    print(f"::notice title=pip-audit skipped {name}::{reason}")
print(f"pip-audit: {len(findings)} known vulnerabilities, {len(skipped)} packages not auditable")
sys.exit(1 if findings else 0)
