#!/usr/bin/env python3
"""Shared run logging for workbench automation scripts."""

from __future__ import annotations

import json
import shlex
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4


WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = WORKBENCH_ROOT / "logs" / "script-runs.jsonl"
LOCAL_TZ = timezone(timedelta(hours=8), "Asia/Shanghai")


def configure_console() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")


def now_local() -> datetime:
    return datetime.now(LOCAL_TZ)


def format_time(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S %Z")


def command_line() -> str:
    return " ".join(shlex.quote(part) for part in sys.argv)


def append_record(record: dict[str, object]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def run_logged(
    *,
    project: str,
    script: str,
    func: Callable[[], int | None],
) -> int:
    """Run func and write one success or failed record to the workbench log."""

    configure_console()
    started_at = now_local()
    run_id = uuid4().hex[:12]
    print(f"[运行中] {script} | 项目：{project} | 开始：{format_time(started_at)}")

    status = "success"
    exit_code = 0
    message = "运行成功"

    try:
        result = func()
        exit_code = int(result or 0)
        if exit_code != 0:
            status = "failed"
            message = f"脚本返回非 0 状态码：{exit_code}"
    except SystemExit as exc:
        exit_code = int(exc.code or 0) if isinstance(exc.code, int) else 1
        if exit_code != 0:
            status = "failed"
            message = f"脚本退出，状态码：{exit_code}"
        else:
            message = "运行成功"
    except Exception as exc:  # pragma: no cover - defensive runtime logger
        status = "failed"
        exit_code = 1
        message = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()

    finished_at = now_local()
    duration_seconds = round((finished_at - started_at).total_seconds(), 3)

    record = {
        "run_id": run_id,
        "project": project,
        "script": script,
        "status": status,
        "exit_code": exit_code,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": duration_seconds,
        "command": command_line(),
        "message": message,
    }
    append_record(record)

    status_label = "成功" if status == "success" else "失败"
    print(
        f"[{status_label}] {script} | 完成：{format_time(finished_at)} | "
        f"耗时：{duration_seconds:.2f}s | 记录：{LOG_PATH}"
    )
    return exit_code

