#!/usr/bin/env python3
"""Unified launcher for existing workbench automation projects."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from workbench_log import append_record, configure_console, format_time, now_local


WORKBENCH_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Task:
    id: str
    name: str
    project: str
    workdir: str
    command: str
    writes_external_system: bool
    detached: bool = False
    description: str = ""


TASKS: dict[str, Task] = {
    "status": Task(
        id="status",
        name="工作台外部项目状态",
        project="workbench",
        workdir=str(WORKBENCH_ROOT),
        command=r"python tools\workbench_external_status.py",
        writes_external_system=False,
        description="只读查看四个现有项目状态。",
    ),
    "pdd-ads-catchup": Task(
        id="pdd-ads-catchup",
        name="拼多多广告补漏检查",
        project="pdd-ads-to-notion",
        workdir=r"D:\desktop\codex\guanggao",
        command="python catchup_daily.py --store all",
        writes_external_system=True,
        description="检查昨天一到七店 Notion 广告数据，缺少时从 ERP 补写。",
    ),
    "pdd-ads-sync-all": Task(
        id="pdd-ads-sync-all",
        name="拼多多广告同步一到七店",
        project="pdd-ads-to-notion",
        workdir=r"D:\desktop\codex\guanggao",
        command="python main.py --store all",
        writes_external_system=True,
        description="从 ERP 同步默认日期的一到七店广告数据到 Notion。",
    ),
    "pdd-weekly-report": Task(
        id="pdd-weekly-report",
        name="Notion 拼多多周报生成",
        project="pdd-weekly-report-existing",
        workdir=r"D:\desktop\codex\notion拼多多周报\pdd_weekly_report",
        command="python main.py",
        writes_external_system=True,
        description="读取 Notion 7 店广告库并生成上周拼多多周报。",
    ),
    "pdd-publisher": Task(
        id="pdd-publisher",
        name="拼多多自动上架工作台",
        project="pdd-auto-listing-existing",
        workdir=r"D:\desktop\codex\拼多多自动上架",
        command=r".\start_pdd_publisher.bat",
        writes_external_system=False,
        detached=True,
        description="启动本地拼多多自动上架网页工作台。",
    ),
    "erp-miniapp-upload": Task(
        id="erp-miniapp-upload",
        name="小程序 ERP 自动上架桌面软件",
        project="erp-miniapp-auto-upload",
        workdir=r"D:\desktop\codex\小程序自动上架\erp_auto_upload",
        command=r".\启动桌面软件.bat",
        writes_external_system=False,
        detached=True,
        description="启动 ERP 自研后台自动上架桌面软件。",
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="工作台统一启动入口。")
    parser.add_argument("task", nargs="?", help="任务 ID。用 --list 查看。")
    parser.add_argument("--list", action="store_true", help="列出所有可启动任务。")
    parser.add_argument("--json", action="store_true", help="配合 --list 输出 JSON。")
    parser.add_argument("--dry-run", action="store_true", help="只显示将要执行的命令，不启动。")
    parser.add_argument("--execute", action="store_true", help="确认执行任务。除 status 外都需要显式提供。")
    parser.add_argument("--date", help="广告同步单日日期，格式 YYYY-MM-DD。")
    parser.add_argument("--range", dest="date_range", help="广告同步日期范围，格式 YYYY-MM-DD~YYYY-MM-DD。")
    parser.add_argument("--store", help="广告同步店铺，支持 all 或逗号分隔店铺 ID。")
    parser.add_argument("--relogin", action="store_true", help="广告同步时强制重新登录 ERP。")
    parser.add_argument("--check-only", action="store_true", help="广告同步只抓取检查，不写入 Notion。")
    return parser.parse_args()


def print_tasks(json_output: bool = False) -> None:
    tasks = [asdict(task) for task in TASKS.values()]
    if json_output:
        print(json.dumps(tasks, ensure_ascii=False, indent=2))
        return

    print("可用工作台任务")
    print("")
    print("| 任务 ID | 名称 | 写外部系统 | 启动方式 |")
    print("| --- | --- | --- | --- |")
    for task in TASKS.values():
        writes = "是" if task.writes_external_system else "否"
        mode = "后台启动" if task.detached else "等待完成"
        print(f"| {task.id} | {task.name} | {writes} | {mode} |")
    print("")
    print(r"预览命令：python tools\workbench_run.py <任务ID> --dry-run")
    print(r"真实执行：python tools\workbench_run.py <任务ID> --execute")


def validate_ads_args(args: argparse.Namespace) -> None:
    date_pattern = r"20\d{2}-\d{2}-\d{2}"
    if args.date and not re.fullmatch(date_pattern, args.date):
        raise SystemExit("--date 格式必须是 YYYY-MM-DD")
    if args.date_range and not re.fullmatch(fr"{date_pattern}~{date_pattern}", args.date_range):
        raise SystemExit("--range 格式必须是 YYYY-MM-DD~YYYY-MM-DD")
    if args.store and not re.fullmatch(r"all|\d+(,\d+)*", args.store):
        raise SystemExit("--store 只能是 all 或逗号分隔的店铺 ID")


def build_task_command(task: Task, args: argparse.Namespace) -> str:
    if task.id not in {"pdd-ads-sync-all", "pdd-ads-catchup"}:
        return task.command

    validate_ads_args(args)
    store = args.store or "all"
    if task.id == "pdd-ads-catchup":
        parts = ["python", "catchup_daily.py", "--store", store]
        if args.date:
            parts.extend(["--date", args.date])
        if args.check_only:
            parts.append("--dry-run")
        return subprocess.list2cmdline(parts)

    parts = ["python", "main.py", "--store", store]
    if args.date_range:
        parts.extend(["--range", args.date_range])
    elif args.date:
        parts.extend(["--date", args.date])
    if args.relogin:
        parts.append("--relogin")
    if args.check_only:
        parts.append("--dry-run")
    return subprocess.list2cmdline(parts)


def record_run(task: Task, command: str, status: str, exit_code: int, started_at, finished_at, message: str) -> None:
    append_record(
        {
            "project": task.project,
            "script": task.id,
            "status": status,
            "exit_code": exit_code,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
            "command": command,
            "workdir": task.workdir,
            "message": message,
        }
    )


def run_task(task: Task, command: str) -> int:
    workdir = Path(task.workdir)
    if not workdir.exists():
        print(f"工作目录不存在：{workdir}", file=sys.stderr)
        return 2

    started_at = now_local()
    print(f"[运行中] {task.name} | 项目：{task.project} | 开始：{format_time(started_at)}", flush=True)
    print(f"工作目录：{task.workdir}", flush=True)
    print(f"命令：{command}", flush=True)

    if task.detached:
        creationflags = subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
        subprocess.Popen(command, cwd=workdir, shell=True, creationflags=creationflags)
        finished_at = now_local()
        record_run(task, command, "success", 0, started_at, finished_at, "已启动后台进程")
        print(f"[成功] {task.name} 已启动后台进程 | 完成：{format_time(finished_at)}", flush=True)
        return 0

    completed = subprocess.run(command, cwd=workdir, shell=True)
    finished_at = now_local()
    status = "success" if completed.returncode == 0 else "failed"
    message = "运行成功" if completed.returncode == 0 else f"退出码：{completed.returncode}"
    record_run(task, command, status, completed.returncode, started_at, finished_at, message)
    label = "成功" if completed.returncode == 0 else "失败"
    print(f"[{label}] {task.name} | 完成：{format_time(finished_at)} | 退出码：{completed.returncode}", flush=True)
    return completed.returncode


def main() -> int:
    configure_console()
    args = parse_args()

    if args.list or not args.task:
        print_tasks(args.json)
        return 0

    task = TASKS.get(args.task)
    if task is None:
        print(f"未知任务：{args.task}", file=sys.stderr)
        print("")
        print_tasks(False)
        return 2

    print(f"任务：{task.name}")
    print(f"说明：{task.description}")
    print(f"工作目录：{task.workdir}")
    command = build_task_command(task, args)
    print(f"命令：{command}")
    print(f"写外部系统：{'是' if task.writes_external_system else '否'}")
    print(f"后台启动：{'是' if task.detached else '否'}")

    if args.dry_run:
        print("dry-run：未执行。")
        return 0

    if args.task != "status" and not args.execute:
        print("")
        print("未执行：除 status 外，所有任务都必须显式添加 --execute。")
        return 2

    return run_task(task, command)


if __name__ == "__main__":
    raise SystemExit(main())
