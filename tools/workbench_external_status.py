#!/usr/bin/env python3
"""Read-only status panel for existing external automation projects."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable


PROJECTS = {
    "pdd_ads": {
        "name": "拼多多广告同步",
        "path": Path(r"D:\desktop\codex\guanggao"),
        "log_dir": Path(r"D:\desktop\codex\guanggao\debug"),
        "patterns": ["task_*.log", "*.log"],
    },
    "pdd_weekly": {
        "name": "拼多多周报",
        "path": Path(r"D:\desktop\codex\notion拼多多周报\pdd_weekly_report"),
        "log_dir": Path(r"D:\desktop\codex\notion拼多多周报\pdd_weekly_report\logs"),
        "patterns": ["weekly_report_*.log", "*.log"],
    },
    "pdd_publisher": {
        "name": "拼多多自动上架",
        "path": Path(r"D:\desktop\codex\拼多多自动上架"),
        "history_path": Path(r"D:\desktop\codex\拼多多自动上架\.tmp_tool\saved_draft_history.json"),
    },
    "erp_miniapp": {
        "name": "小程序 ERP 自动上架",
        "path": Path(r"D:\desktop\codex\小程序自动上架\erp_auto_upload"),
        "log_dir": Path(r"D:\desktop\codex\小程序自动上架\erp_auto_upload\logs"),
        "patterns": ["run_*.log", "*.log"],
    },
}


FAIL_PATTERNS = [
    " CRITICAL",
    " ERROR",
    "Traceback",
    "Exception",
    "失败",
    "NotionSyncError",
    "LoginRequiredError",
]
WARN_PATTERNS = [
    " WARNING",
    "Warning",
    "警告",
    "暂时失败",
    "缺失",
]
SUCCESS_PATTERNS = [
    "Exit code: 0",
    "周报生成完成",
    "补漏检查完成",
    "任务完成",
    "同步完成",
    "流程完成",
    "上传测试已完成",
    "已完成上架信息填写",
    "成功",
]


@dataclass
class ProjectStatus:
    id: str
    name: str
    status: str
    summary: str
    latest_time: str = "-"
    source: str = "-"
    details: list[str] = field(default_factory=list)
    next_action: str = "-"


def configure_console() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="查看现有四个自动化项目的最近状态。")
    parser.add_argument(
        "--project",
        choices=sorted(PROJECTS),
        help="只查看某个项目。",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON，方便后续桌面 UI 使用。")
    parser.add_argument("--tail-lines", type=int, default=160, help="每个日志读取的末尾行数。")
    return parser.parse_args()


def latest_file(directory: Path, patterns: Iterable[str]) -> Path | None:
    if not directory.exists():
        return None

    seen: set[Path] = set()
    files: list[Path] = []
    for pattern in patterns:
        for path in directory.glob(pattern):
            if path.is_file() and path not in seen:
                seen.add(path)
                files.append(path)

    if not files:
        return None
    return max(files, key=lambda item: item.stat().st_mtime)


def read_text_tail(path: Path, max_lines: int) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe"):
        text = raw.decode("utf-16-le", errors="replace")
        return "\n".join(text.splitlines()[-max_lines:])
    if raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16-be", errors="replace")
        return "\n".join(text.splitlines()[-max_lines:])
    if raw[:200].count(b"\x00") > 20:
        text = raw.decode("utf-16-le", errors="replace")
        return "\n".join(text.splitlines()[-max_lines:])

    for encoding in ("utf-8", "utf-8-sig", "gbk"):
        try:
            lines = raw.decode(encoding).splitlines()
            return "\n".join(lines[-max_lines:])
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def format_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")


def first_matches(text: str, patterns: Iterable[str], limit: int = 3) -> list[str]:
    matches: list[str] = []
    for line in text.splitlines():
        if any(pattern in line for pattern in patterns):
            matches.append(line.strip())
            if len(matches) >= limit:
                break
    return matches


def last_matches(text: str, patterns: Iterable[str], limit: int = 3) -> list[str]:
    matches: list[str] = []
    for line in reversed(text.splitlines()):
        if any(pattern in line for pattern in patterns):
            matches.append(line.strip())
            if len(matches) >= limit:
                break
    return list(reversed(matches))


def latest_erp_session(text: str) -> str:
    lines = text.splitlines()
    session_start = 0
    for index, line in enumerate(lines):
        if "启动浏览器：" in line:
            session_start = index
    return "\n".join(lines[session_start:])


def classify_log(project_id: str, text: str) -> tuple[str, str, list[str], str]:
    if project_id == "erp_miniapp":
        text = latest_erp_session(text)

    fail_lines = last_matches(text, FAIL_PATTERNS)
    warn_lines = last_matches(text, WARN_PATTERNS)
    success_lines = last_matches(text, SUCCESS_PATTERNS)

    if project_id == "pdd_ads":
        exit_match = re.search(r"Exit code:\s*(\d+)", text)
        if exit_match:
            if exit_match.group(1) == "0" and not fail_lines:
                return "成功", "最近定时/补漏任务退出码为 0。", success_lines[-3:], "无需处理。"
            if exit_match.group(1) != "0":
                return "失败", f"最近任务退出码为 {exit_match.group(1)}。", fail_lines, "优先查看广告同步 debug 日志和 Notion/ERP 登录状态。"
        if fail_lines:
            return "失败", "最近日志包含失败关键词。", fail_lines, "优先检查 Notion 网络、代理或 ERP 登录态。"

    if fail_lines:
        return "失败", "最近日志包含失败关键词。", fail_lines, "打开源项目日志定位错误。"
    if success_lines:
        if warn_lines:
            return "警告", "最近任务完成，但日志里有 warning。", warn_lines[-3:], "复核 warning 是否影响结果。"
        return "成功", "最近日志显示任务完成。", success_lines[-3:], "无需处理。"
    if warn_lines:
        return "警告", "最近日志只有 warning，未识别到完成标记。", warn_lines[-3:], "复核最新日志末尾。"
    return "未知", "未从最近日志识别到成功或失败。", [], "打开日志确认最后状态。"


def status_from_log(project_id: str, config: dict[str, object], tail_lines: int) -> ProjectStatus:
    log_dir = config["log_dir"]
    patterns = config["patterns"]
    assert isinstance(log_dir, Path)
    assert isinstance(patterns, list)

    if not log_dir.exists():
        return ProjectStatus(
            id=project_id,
            name=str(config["name"]),
            status="未运行",
            summary="日志目录不存在。",
            source=str(log_dir),
            next_action="确认项目是否安装或是否已有运行记录。",
        )

    path = latest_file(log_dir, patterns)
    if path is None:
        return ProjectStatus(
            id=project_id,
            name=str(config["name"]),
            status="未运行",
            summary="没有找到日志文件。",
            source=str(log_dir),
            next_action="先通过源项目入口运行一次。",
        )

    text = read_text_tail(path, tail_lines)
    status, summary, details, next_action = classify_log(project_id, text)
    return ProjectStatus(
        id=project_id,
        name=str(config["name"]),
        status=status,
        summary=summary,
        latest_time=format_mtime(path),
        source=str(path),
        details=details,
        next_action=next_action,
    )


def load_json(path: Path) -> object | None:
    if not path.exists():
        return None
    for encoding in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return json.loads(path.read_text(encoding=encoding))
        except UnicodeDecodeError:
            continue
        except json.JSONDecodeError:
            return None
    return None


def status_from_draft_history(project_id: str, config: dict[str, object]) -> ProjectStatus:
    path = config["history_path"]
    assert isinstance(path, Path)

    if not path.exists():
        return ProjectStatus(
            id=project_id,
            name=str(config["name"]),
            status="未运行",
            summary="未找到保存草稿历史。",
            source=str(path),
            next_action="启动拼多多自动上架工作台后保存草稿，或确认 .tmp_tool 路径。",
        )

    data = load_json(path)
    if not isinstance(data, dict):
        return ProjectStatus(
            id=project_id,
            name=str(config["name"]),
            status="未知",
            summary="保存草稿历史不是合法 JSON。",
            latest_time=format_mtime(path),
            source=str(path),
            next_action="检查 saved_draft_history.json 是否损坏。",
        )

    items = data.get("items") or []
    if not isinstance(items, list) or not items:
        return ProjectStatus(
            id=project_id,
            name=str(config["name"]),
            status="未运行",
            summary="保存草稿历史为空。",
            latest_time=format_mtime(path),
            source=str(path),
            next_action="保存一次草稿后再查看。",
        )

    recent = items[-5:]
    details = []
    for item in reversed(recent):
        if not isinstance(item, dict):
            continue
        saved_at = item.get("saved_at") or "-"
        mall = item.get("mall_name") or item.get("shop_name") or "未知店铺"
        title = item.get("title") or "未记录标题"
        details.append(f"{saved_at} | {mall} | {title}")

    total = data.get("total")
    if not isinstance(total, int):
        total = len(items)

    return ProjectStatus(
        id=project_id,
        name=str(config["name"]),
        status="成功",
        summary=f"累计保存草稿 {total} 条，最近 {len(details)} 条可查看。",
        latest_time=format_mtime(path),
        source=str(path),
        details=details,
        next_action="需要核对时打开拼多多自动上架工作台首页查看草稿历史。",
    )


def collect_statuses(project: str | None, tail_lines: int) -> list[ProjectStatus]:
    selected = PROJECTS.items()
    if project:
        selected = [(project, PROJECTS[project])]

    statuses: list[ProjectStatus] = []
    for project_id, config in selected:
        if "history_path" in config:
            statuses.append(status_from_draft_history(project_id, config))
        else:
            statuses.append(status_from_log(project_id, config, tail_lines))
    return statuses


def print_table(statuses: list[ProjectStatus]) -> None:
    print("工作台外部项目状态")
    print("")
    print("| 项目 | 状态 | 最近时间 | 摘要 |")
    print("| --- | --- | --- | --- |")
    for item in statuses:
        summary = item.summary.replace("|", "/")
        print(f"| {item.name} | {item.status} | {item.latest_time} | {summary} |")

    print("")
    for item in statuses:
        print(f"## {item.name}")
        print(f"- 状态：{item.status}")
        print(f"- 来源：{item.source}")
        print(f"- 建议：{item.next_action}")
        if item.details:
            print("- 关键记录：")
            for detail in item.details:
                print(f"  - {detail}")
        print("")


def main() -> int:
    configure_console()
    args = parse_args()
    statuses = collect_statuses(args.project, args.tail_lines)

    if args.json:
        print(json.dumps([asdict(item) for item in statuses], ensure_ascii=False, indent=2))
    else:
        print_table(statuses)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
