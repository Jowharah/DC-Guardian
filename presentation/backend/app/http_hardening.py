"""HTTP hardening that applies locally and in production (docs/PRODUCTION_READINESS.md, section 5).

- Security headers on every response: no MIME sniffing, no framing, no referrer,
  and API responses are never cached (they carry Evidence).
- A per-user rate limit on endpoints that call OpenAI (Investigator questions and
  specialist evaluations), to bound cost and abuse: DCG_OPENAI_CALLS_PER_MINUTE
  (default 10). In-memory and per process: a production deployment adds a
  shared limiter at the reverse proxy.
"""
import base64
import os
import re
import threading
import time
from collections import defaultdict, deque

from fastapi.responses import JSONResponse

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
OPENAI_ROUTES = re.compile(r"^/api/v1/(investigator/.+/ask|evidence/[^/]+/[^/]+/specialist|"
                           r"correlations/unified/[^/]+/specialists|cyber/face-ssh/candidates/[^/]+/specialists|"
                           r"physical/image-correlations/[^/]+/specialist|ssh/published/[^/]+/specialist-response|"
                           r"operations/correlations/[^/]+/decision)$")
WINDOW_SECONDS = 60
_calls = defaultdict(deque)
_lock = threading.Lock()


def limit_per_minute():
    try:
        return max(1, int(os.environ.get("DCG_OPENAI_CALLS_PER_MINUTE", "10")))
    except ValueError:
        return 10


def caller(request):
    """Username from the Basic header (rate-limit key only; authentication happens in the endpoint)."""
    header = request.headers.get("authorization", "")
    if header.lower().startswith("basic "):
        try:
            return base64.b64decode(header[6:]).decode("utf-8", "replace").split(":", 1)[0]
        except ValueError:
            pass
    return request.client.host if request.client else "unknown"


def allow(key, now=None, record=True):
    """(allowed, retry_after). With record=False only checks; record_call() counts later."""
    now = time.monotonic() if now is None else now
    with _lock:
        calls = _calls[key]
        while calls and now - calls[0] >= WINDOW_SECONDS:
            calls.popleft()
        if len(calls) >= limit_per_minute():
            return False, int(WINDOW_SECONDS - (now - calls[0])) + 1
        if record:
            calls.append(now)
        return True, 0


def record_call(key, now=None):
    with _lock:
        _calls[key].append(time.monotonic() if now is None else now)


def reset():
    with _lock:
        _calls.clear()


async def hardening_middleware(request, call_next):
    limited = request.method == "POST" and OPENAI_ROUTES.match(request.url.path)
    if limited:
        ok, retry = allow(caller(request), record=False)
        if not ok:
            response = JSONResponse({"detail": f"Too many OpenAI-backed requests; retry in {retry} s"}, status_code=429,
                                    headers={"Retry-After": str(retry)})
            response.headers.update(SECURITY_HEADERS)
            return response
    response = await call_next(request)
    # Only calls that passed authentication and authorization count, so nobody can
    # use up another user's quota by sending requests under their name.
    if limited and response.status_code not in (401, 403):
        record_call(caller(request))
    response.headers.update(SECURITY_HEADERS)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response
