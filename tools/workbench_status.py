#!/usr/bin/env python3
"""Show recent workbench automation run status."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = WORKBENCH_ROOT / "logs" / "script-runs.jsonl"


def configure_console() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show recent workbench script run status.")
    parser.add_argument("--limit", type=int, default=10, help="Number of records to show.")
    parser.add_argument("--project", help="Filter by project id.")
    parser.add_argument("--script", help="Filter by script name.")
    parser.add_argument("--log", default=str(LOG_PATH), help="Run log JSONL path.")
    return parser.parse_args()


def load_records(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []

    records: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                records.append(json.loads(text))
            except json.JSONDecodeError:
                records.append(
                    {
                        "status": "invalid",
                        "project": "-",
                        "script": "-",
                        "started_at": "-",
                        "message": f"第 {line_number} 行日志不是合法 JSON",
                    }
                )
    return records


def main() -> int:
    configure_console()
    args = parse_args()
    records = load_records(Path(args.log))

    if args.project:
        records = [record for record in records if record.get("project") == args.project]
    if args.script:
        records = [record for record in records if record.get("script") == args.script]

    records = records[-args.limit :]
    if not records:
        print(f"暂无脚本运行记录。日志位置：{Path(args.log)}")
        return 0

    print(f"最近 {len(records)} 条脚本运行记录：")
    print("")
    print("| 时间 | 状态 | 项目 | 脚本 | 耗时 | 说明 |")
    print("| --- | --- | --- | --- | ---: | --- |")
    for record in reversed(records):
        started_at = str(record.get("started_at", "-")).replace("T", " ")[:19]
        status = str(record.get("status", "-"))
        status_label = {"success": "成功", "failed": "失败", "invalid": "异常日志"}.get(status, status)
        project = record.get("project", "-")
        script = record.get("script", "-")
        duration = record.get("duration_seconds", "-")
        message = str(record.get("message", "-")).replace("|", "/")
        print(f"| {started_at} | {status_label} | {project} | {script} | {duration}s | {message} |")

    print("")
    print(f"日志位置：{Path(args.log)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

