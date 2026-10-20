"""Persistent inference workers, exercised with a fake worker (no models, no GPU)."""
import os
import subprocess
import sys
import time

import pytest

from presentation.backend.app import inference_workers as iw

FAKE_WORKER = '''
import sys, time
from presentation.backend.app.worker_protocol import run
loads = []
def load():
    loads.append(1)
    return {"pid": __import__("os").getpid()}
def handle(state, path):
    text = path.read_text()
    if text == "crash":
        raise SystemExit(3)
    if text == "slow":
        time.sleep(5)
    if text == "fail":
        raise ValueError("bad input")
    return {"pid": state["pid"], "loads": len(loads), "text": text}
sys.exit(run("DCG_FAKE_RESULT=", load, handle))
'''


@pytest.fixture
def fake(tmp_path, monkeypatch):
    package = tmp_path / "fakepkg"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "fake_worker.py").write_text(FAKE_WORKER)
    monkeypatch.setenv("DCG_PERSISTENT_WORKERS", "1")
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(tmp_path), str(iw.PROJECT_ROOT)])}

    def call(text, timeout=10):
        path = tmp_path / f"in-{time.monotonic_ns()}.txt"
        path.write_text(text)
        return iw.run_worker(sys.executable, "fakepkg.fake_worker", path, env=env, timeout=timeout, name="fake")
    yield call
    iw.shutdown_all()


def parse(result):
    import json
    assert result.returncode == 0, result
    return json.loads(result.stdout.strip().removeprefix("DCG_FAKE_RESULT="))


def test_the_model_loads_once_and_the_process_is_reused(fake):
    first, second = parse(fake("a")), parse(fake("b"))
    assert first["pid"] == second["pid"] and second["loads"] == 1 and second["text"] == "b"


def test_a_failed_request_keeps_the_worker_alive(fake):
    pid = parse(fake("a"))["pid"]
    failed = fake("fail")
    assert failed.returncode == 1 and failed.stdout.startswith("DCG_WORKER_ERROR=")
    assert parse(fake("b"))["pid"] == pid


def test_a_crashed_worker_is_restarted(fake):
    pid = parse(fake("a"))["pid"]
    assert fake("crash").returncode == 1
    assert parse(fake("b"))["pid"] != pid


def test_a_timeout_raises_like_subprocess_run_and_restarts(fake):
    pid = parse(fake("a"))["pid"]
    with pytest.raises(subprocess.TimeoutExpired):
        fake("slow", timeout=1)
    assert parse(fake("b"))["pid"] != pid


def test_one_shot_mode_is_used_when_disabled(fake, monkeypatch):
    monkeypatch.setenv("DCG_PERSISTENT_WORKERS", "0")
    first, second = parse(fake("a")), parse(fake("b"))
    assert first["pid"] != second["pid"] and not iw._workers


def test_component_python_falls_back_to_the_backend_interpreter(tmp_path, monkeypatch):
    monkeypatch.setattr(iw, "PROJECT_ROOT", tmp_path)
    assert iw.component_python(".venv-ppe") == __import__("pathlib").Path(sys.executable)
    venv = tmp_path / ".venv-ppe" / "Scripts"
    venv.mkdir(parents=True)
    (venv / "python.exe").write_text("")
    assert iw.component_python(".venv-ppe") == venv / "python.exe"
