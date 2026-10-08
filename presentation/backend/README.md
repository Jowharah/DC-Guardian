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
