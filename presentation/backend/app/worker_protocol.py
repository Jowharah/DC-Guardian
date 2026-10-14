"""Line protocol shared by the inference workers (one-shot or persistent).

One-shot (original): ``python -m <worker> <input-path>`` prints one
``<MARKER><json>`` line and exits. Markers start with ``DCG_``; the backend ignores any other
stdout line (library chatter).

Persistent: ``python -m <worker> --serve`` loads its model once, prints
``DCG_WORKER_READY``, then for every request line ``{"path": "..."}`` on stdin
prints exactly one line: ``<MARKER><json>`` or ``DCG_WORKER_ERROR=<code>``.
A failed request never ends the worker; end of input does. Only a path to an
existing file is accepted (the backend writes a controlled temporary copy);
no command, shell or module name ever crosses the pipe.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable

READY = "DCG_WORKER_READY"
ERROR = "DCG_WORKER_ERROR="


def run(marker: str, load: Callable[[], object], handle: Callable[[object, Path], dict]) -> int:
    """Entry point for a worker module: dispatches to one-shot or serve mode."""
    if sys.argv[1:] == ["--serve"]:
        return serve(marker, load, handle)
    if len(sys.argv) != 2:
        return 2
    path = Path(sys.argv[1]).resolve()
    if not path.is_file():
        return 2
    print(marker + json.dumps(handle(load(), path), allow_nan=False), flush=True)
    return 0


def serve(marker: str, load: Callable[[], object], handle: Callable[[object, Path], dict]) -> int:
    pipeline = load()  # the expensive part, paid once per worker
    print(READY, flush=True)
    for line in sys.stdin:
        try:
            request = json.loads(line)
            path = Path(str(request["path"])).resolve()
            if not path.is_file():
                print(ERROR + "INPUT_MISSING", flush=True)
                continue
            print(marker + json.dumps(handle(pipeline, path), allow_nan=False), flush=True)
        except Exception:  # noqa: BLE001 - report and keep serving; details stay out of the pipe
            print(ERROR + "INFERENCE_FAILED", flush=True)
    return 0
