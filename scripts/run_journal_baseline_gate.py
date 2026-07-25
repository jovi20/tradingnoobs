#!/usr/bin/env python3
"""Run the local and CI JRN-002 journal baseline gate."""
from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = REPO_ROOT / ".artifacts" / "jrn002"
SUMMARY_PATH = ARTIFACT_DIR / "gate-summary.json"


@dataclass
class CommandResult:
    name: str
    command: list[str]
    returncode: int
    duration_seconds: float


def _read_version(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _run_output(command: list[str]) -> str:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _assert_tool_versions() -> dict[str, str]:
    expected_python = _read_version(REPO_ROOT / ".python-version")
    expected_node = _read_version(REPO_ROOT / ".node-version")
    actual_python = platform.python_version()
    actual_node = _run_output(["node", "--version"]).removeprefix("v")
    actual_npm = _run_output(["npm", "--version"])

    if actual_python != expected_python:
        raise RuntimeError(
            f"Python {expected_python} is required, got {actual_python}"
        )
    if actual_node != expected_node:
        raise RuntimeError(f"Node {expected_node} is required, got {actual_node}")
    if actual_npm != "11.16.0":
        raise RuntimeError(f"npm 11.16.0 is required, got {actual_npm}")

    return {
        "python": actual_python,
        "python_executable": sys.executable,
        "node": actual_node,
        "npm": actual_npm,
    }


def _postgres_server_version(database_url: str) -> str:
    from sqlalchemy import create_engine, text

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return str(connection.execute(text("SHOW server_version")).scalar_one())
    finally:
        engine.dispose()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class EphemeralPostgres:
    def __init__(self) -> None:
        self.data_dir: Path | None = None
        self.url: str | None = None

    def start(self) -> str:
        for executable in ("initdb", "pg_ctl"):
            if shutil.which(executable) is None:
                raise RuntimeError(
                    f"{executable} is required when JRN002_POSTGRES_URL is unset"
                )

        self.data_dir = Path(
            tempfile.mkdtemp(prefix="jrn002-postgres-", dir="/private/tmp")
        )
        port = _free_port()
        subprocess.run(
            [
                "initdb",
                "-D",
                str(self.data_dir),
                "--auth=trust",
                "--encoding=UTF8",
                "--no-locale",
                "--username=postgres",
            ],
            cwd=REPO_ROOT,
            check=True,
        )
        subprocess.run(
            [
                "pg_ctl",
                "-D",
                str(self.data_dir),
                "-o",
                f"-F -p {port} -h 127.0.0.1",
                "-w",
                "start",
            ],
            cwd=REPO_ROOT,
            check=True,
        )
        self.url = f"postgresql+psycopg2://postgres@127.0.0.1:{port}/postgres"
        return self.url

    def stop(self) -> None:
        if self.data_dir is None:
            return
        subprocess.run(
            ["pg_ctl", "-D", str(self.data_dir), "-m", "fast", "-w", "stop"],
            cwd=REPO_ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        shutil.rmtree(self.data_dir, ignore_errors=True)
        self.data_dir = None


def _gate_commands() -> list[tuple[str, list[str]]]:
    secret_scan_base = os.getenv("JRN002_SECRET_SCAN_BASE")
    secret_scan_head = os.getenv("JRN002_SECRET_SCAN_HEAD", "HEAD")
    if not secret_scan_base:
        secret_scan_base = _run_output(["git", "rev-parse", "HEAD^"])

    return [
        (
            "added_secret_boundary",
            [
                sys.executable,
                "scripts/check_added_secrets.py",
                "--base",
                secret_scan_base,
                "--head",
                secret_scan_head,
            ],
        ),
        (
            "dependency_locks",
            [
                sys.executable,
                "backend/scripts/check_dependency_locks.py",
            ],
        ),
        (
            "backend",
            [sys.executable, "-m", "pytest", "backend/tests"],
        ),
        (
            "openapi_snapshot",
            [
                sys.executable,
                "backend/scripts/generate_openapi_snapshot.py",
                "--check",
            ],
        ),
        (
            "frontend_release_contract",
            ["npm", "run", "check:release-contract"],
        ),
        ("frontend_test", ["npm", "test"]),
        ("frontend_typecheck", ["npm", "run", "typecheck"]),
        ("frontend_lint", ["npm", "run", "lint"]),
        ("frontend_build", ["npm", "run", "build"]),
    ]


def _clean_frontend_generated_cache() -> CommandResult:
    started_at = time.monotonic()
    relative_path = Path("frontend") / ".next"
    shutil.rmtree(REPO_ROOT / relative_path, ignore_errors=True)
    return CommandResult(
        name="frontend_generated_cache_cleanup",
        command=["internal", "remove_generated_cache", str(relative_path)],
        returncode=0,
        duration_seconds=round(time.monotonic() - started_at, 3),
    )


def main() -> int:
    started_at = time.time()
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[CommandResult] = []
    postgres = EphemeralPostgres()
    status = "FAILED"
    failure: str | None = None

    try:
        tools = _assert_tool_versions()
        postgres_url = os.getenv("JRN002_POSTGRES_URL") or postgres.start()
        tools["postgresql"] = _postgres_server_version(postgres_url)
        env = os.environ.copy()
        env["JRN001_POSTGRES_URL"] = postgres_url
        env["JRN002_POSTGRES_URL"] = postgres_url
        env["PYTHONPATH"] = str(REPO_ROOT / "backend")
        env["NEXT_TELEMETRY_DISABLED"] = "1"
        results.append(_clean_frontend_generated_cache())

        for name, command in _gate_commands():
            command_started = time.monotonic()
            completed = subprocess.run(
                command,
                cwd=REPO_ROOT / "frontend" if command[0] == "npm" else REPO_ROOT,
                env=env,
                check=False,
            )
            result = CommandResult(
                name=name,
                command=command,
                returncode=completed.returncode,
                duration_seconds=round(time.monotonic() - command_started, 3),
            )
            results.append(result)
            if completed.returncode != 0:
                raise RuntimeError(
                    f"{name} failed with exit code {completed.returncode}"
                )
        status = "PASSED"
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        failure = str(exc)
        print(f"JRN-002 gate failed: {failure}", file=sys.stderr)
        return 1
    finally:
        postgres.stop()
        try:
            commit = _run_output(["git", "rev-parse", "HEAD"])
            worktree_status = _run_output(["git", "status", "--short"]).splitlines()
        except (OSError, subprocess.CalledProcessError):
            commit = "UNKNOWN"
            worktree_status = []
        if "tools" not in locals():
            tools = {}
        summary = {
            "gate": "JRN-002",
            "status": status,
            "commit": commit,
            "worktree_status": worktree_status,
            "tools": tools,
            "started_at_unix": started_at,
            "duration_seconds": round(time.time() - started_at, 3),
            "failure": failure,
            "commands": [asdict(result) for result in results],
        }
        SUMMARY_PATH.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Gate summary: {SUMMARY_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    raise SystemExit(main())
