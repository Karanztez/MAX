"""
src/core/background_runner.py — Asynchronous Background Test & Task Runner for MAX.
Runs test suites (unittest, pytest, or custom validation scripts) in a dedicated
background thread without blocking the GUI or agent execution.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional


@dataclass
class TestRunResult:
    """Represents the execution state and output of a test run."""
    task_id: str
    command: list[str]
    status: str = "IDLE"  # IDLE, RUNNING, PASSED, FAILED, ERROR, CANCELLED
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    duration_sec: float = 0.0
    start_time: str = ""
    end_time: str = ""
    summary: str = ""
    target_path: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BackgroundTestRunner:
    """
    Manages background test and command executions.
    Ensures safe, non-blocking subprocess execution with timeout and output capturing.
    """

    _instance: Optional[BackgroundTestRunner] = None
    _lock = threading.Lock()

    def __init__(self, workspace_path: Optional[str | Path] = None) -> None:
        self.workspace_path = Path(workspace_path).resolve() if workspace_path else Path.cwd()
        self._runs: dict[str, TestRunResult] = {}
        self._active_processes: dict[str, subprocess.Popen[str]] = {}
        self._active_task_id: Optional[str] = None

    @classmethod
    def get_instance(cls, workspace_path: Optional[str | Path] = None) -> BackgroundTestRunner:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(workspace_path=workspace_path)
            return cls._instance

    def get_status(self, task_id: Optional[str] = None) -> Optional[TestRunResult]:
        tid = task_id or self._active_task_id
        if not tid:
            return None
        return self._runs.get(tid)

    def list_runs(self) -> list[TestRunResult]:
        return list(self._runs.values())

    def cancel_run(self, task_id: Optional[str] = None) -> bool:
        tid = task_id or self._active_task_id
        if not tid or tid not in self._active_processes:
            return False

        proc = self._active_processes[tid]
        try:
            proc.terminate()
            time.sleep(0.2)
            if proc.poll() is None:
                proc.kill()
        except Exception:
            pass

        if tid in self._runs:
            run = self._runs[tid]
            run.status = "CANCELLED"
            run.summary = "การทดสอบถูกยกเลิกโดยผู้ใช้"

        self._active_processes.pop(tid, None)
        if self._active_task_id == tid:
            self._active_task_id = None
        return True

    def start_test_run(
        self,
        target_path: Optional[str | Path] = None,
        custom_command: Optional[str | list[str]] = None,
        cwd: Optional[str | Path] = None,
        timeout_sec: int = 120,
        on_update: Optional[Callable[[TestRunResult], None]] = None,
        on_finish: Optional[Callable[[TestRunResult], None]] = None,
    ) -> str:
        """
        Start an asynchronous test execution in a background thread.
        Returns the unique task_id.
        """
        task_id = f"test_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        work_dir = Path(cwd).resolve() if cwd else self.workspace_path

        # Resolve command
        cmd: list[str] = []
        if custom_command:
            if isinstance(custom_command, list):
                cmd = custom_command
            else:
                cmd = shlex.split(custom_command, posix=(sys.platform != "win32"))
        elif target_path:
            target = Path(target_path).resolve()
            if target.is_file():
                # Check if it's a pytest or unittest file
                cmd = [sys.executable, "-m", "unittest", str(target)]
            elif target.is_dir():
                cmd = [sys.executable, "-m", "unittest", "discover", "-s", str(target)]
            else:
                cmd = [sys.executable, "-m", "unittest", str(target_path)]
        else:
            # Default: discover tests in workspace
            tests_dir = work_dir / "tests"
            if tests_dir.is_dir():
                cmd = [sys.executable, "-m", "unittest", "discover", "-s", str(tests_dir)]
            else:
                cmd = [sys.executable, "-m", "unittest", "discover", "-s", str(work_dir)]

        start_str = time.strftime("%Y-%m-%d %H:%M:%S")
        run_record = TestRunResult(
            task_id=task_id,
            command=cmd,
            status="RUNNING",
            start_time=start_str,
            target_path=str(target_path) if target_path else None,
            summary="กำลังรันการทดสอบในเบื้องหลัง...",
        )

        self._runs[task_id] = run_record
        self._active_task_id = task_id

        if on_update:
            try:
                on_update(run_record)
            except Exception:
                pass

        worker_thread = threading.Thread(
            target=self._run_worker,
            args=(task_id, cmd, work_dir, timeout_sec, on_update, on_finish),
            daemon=True,
            name=f"BGTestRunner-{task_id}",
        )
        worker_thread.start()

        return task_id

    def _run_worker(
        self,
        task_id: str,
        cmd: list[str],
        cwd: Path,
        timeout_sec: int,
        on_update: Optional[Callable[[TestRunResult], None]],
        on_finish: Optional[Callable[[TestRunResult], None]],
    ) -> None:
        run = self._runs[task_id]
        start_ts = time.time()
        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []

        try:
            # Ensure environment has utf-8 and project root in PYTHONPATH
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            existing_pp = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{str(cwd)}{os.pathsep}{existing_pp}" if existing_pp else str(cwd)

            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            self._active_processes[task_id] = proc

            def _read_stdout():
                assert proc.stdout is not None
                for line in iter(proc.stdout.readline, ""):
                    stdout_chunks.append(line)
                    run.stdout = "".join(stdout_chunks)
                    if on_update:
                        try:
                            on_update(run)
                        except Exception:
                            pass
                proc.stdout.close()

            def _read_stderr():
                assert proc.stderr is not None
                for line in iter(proc.stderr.readline, ""):
                    stderr_chunks.append(line)
                    run.stderr = "".join(stderr_chunks)
                    if on_update:
                        try:
                            on_update(run)
                        except Exception:
                            pass
                proc.stderr.close()

            t_out = threading.Thread(target=_read_stdout, daemon=True)
            t_err = threading.Thread(target=_read_stderr, daemon=True)
            t_out.start()
            t_err.start()

            # Wait with timeout
            try:
                exit_code = proc.wait(timeout=timeout_sec)
                t_out.join(timeout=2)
                t_err.join(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                t_out.join(timeout=1)
                t_err.join(timeout=1)
                run.status = "FAILED"
                run.summary = f"⏱️ หมดเวลาการรันทดสอบ (Timeout {timeout_sec}s)"
                run.exit_code = -1
                run.duration_sec = round(time.time() - start_ts, 2)
                run.end_time = time.strftime("%Y-%m-%d %H:%M:%S")
                if on_finish:
                    on_finish(run)
                return

            run.duration_sec = round(time.time() - start_ts, 2)
            run.exit_code = exit_code
            run.end_time = time.strftime("%Y-%m-%d %H:%M:%S")
            run.stdout = "".join(stdout_chunks)
            run.stderr = "".join(stderr_chunks)

            # Analyze output summary
            combined_output = run.stdout + "\n" + run.stderr
            if exit_code == 0:
                run.status = "PASSED"
                summary_line = "ผ่านการทดสอบทั้งหมด (Tests Passed)"
                for line in combined_output.splitlines():
                    if "Ran " in line or "OK" in line or "passed" in line:
                        summary_line = line.strip()
                run.summary = f"🟢 {summary_line} ({run.duration_sec}s)"
            else:
                run.status = "FAILED"
                fail_summary = f"การทดสอบล้มเหลว (Exit code: {exit_code})"
                for line in combined_output.splitlines():
                    if "FAILED" in line or "Error" in line or "failures=" in line:
                        fail_summary = line.strip()
                run.summary = f"🔴 {fail_summary} ({run.duration_sec}s)"

        except Exception as ex:
            run.status = "ERROR"
            run.exit_code = -1
            run.duration_sec = round(time.time() - start_ts, 2)
            run.end_time = time.strftime("%Y-%m-%d %H:%M:%S")
            run.summary = f"❌ เกิดข้อผิดพลาดในการรัน: {ex}"
        finally:
            self._active_processes.pop(task_id, None)
            if self._active_task_id == task_id:
                self._active_task_id = None
            if on_finish:
                try:
                    on_finish(run)
                except Exception:
                    pass
