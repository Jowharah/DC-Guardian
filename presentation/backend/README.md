# Presentation backend — controlled prototype

This FastAPI foundation wraps the existing allowlisted integration scenario registry.
It does not expose raw model evidence, biometric data, source IPs, RAG text, or arbitrary Neo4j queries.

**Do not expose this service to a network or production users yet.** Authentication, authorization, rate limiting, persistence, audit logging and tool approval are required before deployment. The scenario execution endpoint runs controlled synthetic workflows and may require a running Neo4j instance.

Install FastAPI, Uvicorn, and compatible Pydantic in your development environment, then run from the repository root:

```powershell
python -m uvicorn presentation.backend.app.main:app --host 127.0.0.1 --port 8000
```

Endpoints: GET /api/v1/health, GET /api/v1/scenarios, POST /api/v1/scenarios/{name}/run.

The next milestone is an authenticated read-only incident repository and agent investigation tool registry. Do not use this prototype endpoint as an authenticated production API.

## Local operator authentication (development only)

The API now requires a server-configured local account. In the PowerShell terminal
used to launch FastAPI, set the following variables **without committing their values**:

```powershell
$env:DCG_LOCAL_USER = "dcg-local-operator"
$env:DCG_LOCAL_PASSWORD = Read-Host "Local operator password"
$env:DCG_LOCAL_ROLE = "administrator"
$env:DCG_LOCAL_ZONES = "ZONE-A,ZONE-B,ZONE-C"
python -m uvicorn presentation.backend.app.main:app --host 127.0.0.1 --port 8000
```

Open the React frontend and sign in with that username/password. For the
synthetic event generator, configure the same environment variables in its
terminal before starting it.

**Security limits:** HTTP Basic sends reusable credentials on every request.
This is strictly a loopback development mechanism, not a secure production
login/session solution. No credentials are saved to browser storage or Git.
The current graph API still masks Person and SourceIP nodes regardless of role.
Do not enable external network binding, deploy publicly, or use real employee
credentials. Production requires TLS, proper account management, password
hashing or institutional SSO, secure sessions, rate limits, audit logging,
and comprehensive API security tests.
