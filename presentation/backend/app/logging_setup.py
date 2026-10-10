"""Local file logging for the Presentation API.

Writes to <repo>/logs (override with DCG_LOG_DIR):
  api_access.log  one line per request: method, path, status, duration
  backend.log     application and server messages (INFO and above)
  errors.log      warnings and errors with full tracebacks

Never logs request bodies, headers, credentials or query strings: those can
carry Evidence content, operator rationale or secrets. Paths may contain
Evidence IDs, which are needed to diagnose a failing request.
"""
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
FORMAT="%(asctime)s %(levelname)s %(name)s: %(message)s"
access_log=logging.getLogger("dcg.access")
_configured=False

def log_dir():
    return Path(os.environ.get("DCG_LOG_DIR") or ROOT/"logs")

def _file(name,level):
    handler=RotatingFileHandler(log_dir()/name,maxBytes=5_000_000,backupCount=5,encoding="utf-8")
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(FORMAT))
    return handler

def configure():
    """Attach file handlers once per process. Skipped under pytest so test
    runs never write to the operator's log folder."""
    global _configured
    if _configured or "pytest" in sys.modules:
        return
    log_dir().mkdir(parents=True,exist_ok=True)
    root=logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(_file("backend.log",logging.INFO))
    root.addHandler(_file("errors.log",logging.WARNING))
    access_log.setLevel(logging.INFO)
    access_log.addHandler(_file("api_access.log",logging.INFO))
    access_log.propagate=False
    # Uvicorn's own access log duplicates ours (and includes query strings).
    logging.getLogger("uvicorn.access").propagate=False
    # HTTP client libraries (used by the OpenAI SDK) log full outgoing URLs.
    for name in ("httpx","httpcore","openai"):
        logging.getLogger(name).setLevel(logging.WARNING)
    _configured=True

async def request_logging(request,call_next):
    """Middleware: log every request; record unhandled errors with traceback."""
    start=time.perf_counter()
    try:
        response=await call_next(request)
    except Exception:
        logging.getLogger("dcg.api").exception("Unhandled error: %s %s",request.method,request.url.path)
        access_log.info("%s %s 500 %.0fms",request.method,request.url.path,(time.perf_counter()-start)*1000)
        raise
    elapsed=(time.perf_counter()-start)*1000
    access_log.info("%s %s %s %.0fms",request.method,request.url.path,response.status_code,elapsed)
    if response.status_code>=500:
        logging.getLogger("dcg.api").warning("Server error %s: %s %s",response.status_code,request.method,request.url.path)
    elif elapsed>3000:
        logging.getLogger("dcg.api").warning("Slow request %.0fms: %s %s",elapsed,request.method,request.url.path)
    return response
