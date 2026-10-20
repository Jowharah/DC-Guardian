"""Inference workers kept alive between uploads.

Each upload used to start a fresh worker process in the component's own
environment, which reloaded the model every time (Face about 10 s, PPE and SSH
about 4 s per upload, almost all start-up). A persistent worker loads its model
once and then answers requests over a pipe (see worker_protocol); the
component environments stay isolated exactly as before.

- One worker per (executable, module, environment), so changing
  DCG_PPE_DETECTOR starts a separate worker with the other model.
- Requests to one worker run one at a time.
- A request that times out, or a worker that dies, is killed and restarted on
  the next request; the caller gets the same 504/503 as before.
- A worker idle for DCG_WORKER_IDLE_SECONDS (default 900) is stopped, freeing
  GPU memory; the next upload pays the start-up once again.
- DCG_PERSISTENT_WORKERS=0 restores one process per upload (tests use this).
"""
from __future__ import annotations

import json
import logging
import os
import queue
import subprocess  # nosec B404: fixed interpreter and module paths only, never user input
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from presentation.backend.app.worker_protocol import ERROR, READY

logger = logging.getLogger("dcg.workers")
PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOG_DIR = PROJECT_ROOT / "logs" / "workers"
STARTUP_TIMEOUT = 300  # first model load (GPU initialisation) can be slow


def component_python(venv: str) -> Path:
    """Interpreter of a component environment (e.g. ``.venv-ppe``), or the backend's own.

    The dedicated environments (GPU PyTorch for PPE, TensorFlow for Face) are
    optional: the main environment also contains YOLO and DeepFace, so a fresh
    installation with only ``.venv-dc-guardian`` still runs every upload (PPE on
    the CPU when no CUDA build is present).
    """
    for candidate in (PROJECT_ROOT / venv / "Scripts" / "python.exe", PROJECT_ROOT / venv / "bin" / "python"):
        if candidate.is_file():
            return candidate
    return Path(sys.executable)


class WorkerTimeout(Exception):
    pass


@dataclass
class WorkerResult:
    returncode: int
    stdout: str


def persistent_enabled() -> bool:
    return os.environ.get("DCG_PERSISTENT_WORKERS", "1").strip() != "0"


def idle_seconds() -> float:
    try:
        return float(os.environ.get("DCG_WORKER_IDLE_SECONDS", "900"))
    except ValueError:
        return 900.0


class PersistentWorker:
    def __init__(self, command: list[str], env: dict[str, str], name: str):
        self.command, self.env, self.name = command, env, name
        self.process: subprocess.Popen | None = None
        self.log = None
        self.lines: queue.Queue[str | None] = queue.Queue()
        self.lock = threading.Lock()
        self.last_used = time.monotonic()

    def _reader(self, process: subprocess.Popen) -> None:
        for line in process.stdout:
            self.lines.put(line.rstrip("\r\n"))
        self.lines.put(None)  # end of output: the worker has exited

    def _next_line(self, deadline: float) -> str:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise WorkerTimeout()
            try:
                line = self.lines.get(timeout=remaining)
            except queue.Empty:
                raise WorkerTimeout() from None
            if line is None:
                raise RuntimeError("worker exited")
            if line == READY or line.startswith(("DCG_", )):
                return line
            # Anything else is library chatter on stdout; ignore it.

    def _start(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.log = open(LOG_DIR / f"{self.name}.log", "a", encoding="utf-8")  # noqa: SIM115 - closed in stop()
        self.lines = queue.Queue()
        self.process = subprocess.Popen(  # nosec B603: fixed argv, no shell
            [*self.command, "--serve"], cwd=str(PROJECT_ROOT), env=self.env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=self.log, text=True, encoding="utf-8", errors="replace", bufsize=1)
        threading.Thread(target=self._reader, args=(self.process,), daemon=True).start()
        started = time.monotonic()
        if self._next_line(started + STARTUP_TIMEOUT) != READY:
            raise RuntimeError("worker did not become ready")
        logger.info("Worker %s ready in %.1f s", self.name, time.monotonic() - started)

    def stop(self) -> None:
        process, self.process = self.process, None
        if process and process.poll() is None:
            try:
                process.stdin.close()
                process.wait(timeout=5)
            except Exception:  # noqa: BLE001 - make sure it is gone
                process.kill()
        if self.log:
            self.log.close()
            self.log = None

    def request(self, path: Path, timeout: float) -> WorkerResult:
        with self.lock:
            self.last_used = time.monotonic()
            try:
                if self.process is None or self.process.poll() is not None:
                    self._start()
                self.process.stdin.write(json.dumps({"path": str(path)}) + "\n")
                self.process.stdin.flush()
                line = self._next_line(time.monotonic() + timeout)
            except WorkerTimeout:
                logger.warning("Worker %s timed out; restarting on next request", self.name)
                if self.process:
                    self.process.kill()
                self.stop()
                raise
            except Exception:  # noqa: BLE001 - broken pipe, start failure, unexpected exit
                logger.exception("Worker %s failed; restarting on next request", self.name)
                self.stop()
                return WorkerResult(1, "")
            finally:
                self.last_used = time.monotonic()
            return WorkerResult(1 if line.startswith(ERROR) else 0, line + "\n")


_workers: dict[tuple, PersistentWorker] = {}
_registry_lock = threading.Lock()
_reaper_started = False


def _reap_idle() -> None:
    while True:
        time.sleep(30)
        limit = idle_seconds()
        with _registry_lock:
            workers = list(_workers.values())
        for worker in workers:
            if worker.process is not None and time.monotonic() - worker.last_used > limit and worker.lock.acquire(False):
                try:
                    logger.info("Stopping idle worker %s", worker.name)
                    worker.stop()
                finally:
                    worker.lock.release()


def run_worker(python: Path, module: str, input_path: Path, env: dict[str, str], timeout: float,
               name: str) -> WorkerResult:
    """Run one inference; raises subprocess.TimeoutExpired on timeout, as subprocess.run did."""
    command = [str(python), "-m", module]
    if not persistent_enabled():
        completed = subprocess.run(  # nosec B603: fixed argv, no shell
            [*command, str(input_path)], cwd=str(PROJECT_ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, check=False, env=env)
        return WorkerResult(completed.returncode, completed.stdout)
    global _reaper_started
    key = (tuple(command), tuple(sorted(env.items())))
    with _registry_lock:
        worker = _workers.get(key)
        if worker is None:
            worker = _workers[key] = PersistentWorker(command, env, name)
        if not _reaper_started:
            threading.Thread(target=_reap_idle, daemon=True, name="dcg-worker-reaper").start()
            _reaper_started = True
    try:
        return worker.request(input_path, timeout)
    except WorkerTimeout as exc:
        raise subprocess.TimeoutExpired(command, timeout) from exc


def shutdown_all() -> None:
    with _registry_lock:
        workers = list(_workers.values())
        _workers.clear()
    for worker in workers:
        worker.stop()
