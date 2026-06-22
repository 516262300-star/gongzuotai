#!/usr/bin/env python3
"""Local web dashboard for the personal workbench."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from workbench_external_status import PROJECTS, classify_log, collect_statuses, read_text_tail
from workbench_log import LOG_PATH, configure_console
from workbench_run import TASKS


WORKBENCH_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class HistoryEntry:
    time: str
    status: str
    title: str
    summary: str
    source: str


INDEX_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>个人工作台</title>
  <style>
    :root {
      --app-bg: #f3f5f8;
      --nav-bg: #202936;
      --nav-muted: #a8b3c2;
      --surface: #ffffff;
      --surface-soft: #f8fafc;
      --line: #dbe1ea;
      --line-strong: #c7d0de;
      --text: #161f2e;
      --muted: #687386;
      --good: #087443;
      --bad: #b42318;
      --warn: #95610f;
      --idle: #566273;
      --accent: #2563eb;
      --accent-weak: #eef4ff;
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
      background: var(--app-bg);
      color: var(--text);
      font-size: 14px;
      letter-spacing: 0;
    }
    .app-shell {
      display: grid;
      grid-template-columns: 236px minmax(0, 1fr);
      min-height: 100vh;
    }
    aside {
      position: sticky;
      top: 0;
      height: 100vh;
      padding: 18px 14px;
      background: var(--nav-bg);
      color: #fff;
    }
    .brand {
      display: grid;
      gap: 5px;
      padding: 6px 8px 18px;
      border-bottom: 1px solid rgba(255,255,255,.12);
    }
    h1 { margin: 0; font-size: 18px; font-weight: 700; }
    .brand-sub { color: var(--nav-muted); font-size: 12px; line-height: 1.5; }
    nav { display: grid; gap: 6px; padding: 16px 0; }
    nav a {
      display: flex;
      align-items: center;
      gap: 9px;
      min-height: 36px;
      padding: 0 10px;
      border-radius: 6px;
      color: #e8edf5;
      text-decoration: none;
      font-weight: 600;
    }
    nav a:hover { background: rgba(255,255,255,.1); }
    .nav-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #8fb4ff;
      flex: 0 0 auto;
    }
    .nav-note {
      margin: 10px 8px 0;
      padding-top: 14px;
      border-top: 1px solid rgba(255,255,255,.12);
      color: var(--nav-muted);
      font-size: 12px;
      line-height: 1.6;
    }
    .content {
      min-width: 0;
      padding: 18px;
    }
    header {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 14px;
      align-items: center;
      margin-bottom: 14px;
    }
    .page-title {
      display: grid;
      gap: 4px;
      min-width: 0;
    }
    .page-title h2 {
      margin: 0;
      font-size: 22px;
      font-weight: 750;
    }
    .page-title p {
      margin: 0;
      color: var(--muted);
      line-height: 1.5;
    }
    .toolbar { display: flex; align-items: center; gap: 8px; }
    button, select, input {
      font: inherit;
      min-height: 34px;
      border-radius: 6px;
      border: 1px solid var(--line-strong);
      background: #fff;
      color: var(--text);
    }
    button {
      padding: 0 12px;
      cursor: pointer;
      white-space: nowrap;
    }
    button:hover { border-color: #9aa8ba; }
    button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
    button.danger { background: #fff7f5; border-color: #efaaa5; color: var(--bad); }
    button:disabled { opacity: .55; cursor: not-allowed; }
    select { padding: 0 10px; min-width: 210px; }
    .kpis {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }
    .kpi {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      align-items: center;
      gap: 10px;
      min-height: 78px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
    }
    .kpi strong { font-size: 26px; line-height: 1; }
    .kpi span { color: var(--muted); font-size: 12px; }
    .kpi-mark {
      width: 10px;
      height: 38px;
      border-radius: 999px;
      background: var(--idle);
    }
    .kpi-mark.success { background: var(--good); }
    .kpi-mark.failed { background: var(--bad); }
    .kpi-mark.warning { background: var(--warn); }
    .grid {
      display: grid;
      grid-template-columns: minmax(430px, 1.1fr) minmax(380px, .9fr);
      gap: 14px;
      align-items: start;
    }
    .span-all { grid-column: 1 / -1; }
    section {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      min-width: 0;
      box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
      overflow: hidden;
    }
    .section-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 13px 16px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfe;
    }
    .section-title {
      display: grid;
      gap: 2px;
      min-width: 0;
    }
    h3 { margin: 0; font-size: 15px; font-weight: 700; }
    .section-title span, .meta, .detail, .path {
      color: var(--muted);
      line-height: 1.5;
      overflow-wrap: anywhere;
    }
    .section-title span { font-size: 12px; }
    .status-list, .task-list, .history-list { display: grid; gap: 0; }
    .status-row, .task-row, .history-row {
      display: grid;
      gap: 8px;
      padding: 13px 16px;
      border-bottom: 1px solid var(--line);
    }
    .status-row:last-child, .task-row:last-child, .history-row:last-child { border-bottom: 0; }
    .status-row:hover, .task-row:hover, .history-row:hover { background: var(--surface-soft); }
    .row-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .name {
      font-weight: 700;
      min-width: 0;
      overflow-wrap: anywhere;
    }
    .summary {
      color: #39465a;
      line-height: 1.5;
      overflow-wrap: anywhere;
    }
    .path {
      font-family: Consolas, "Cascadia Mono", monospace;
      font-size: 12px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 54px;
      height: 25px;
      padding: 0 9px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      border: 1px solid transparent;
      flex: 0 0 auto;
    }
    .success { color: var(--good); background: #eaf7ef; border-color: #b9e4c6; }
    .failed { color: var(--bad); background: #fff1f0; border-color: #efaaa5; }
    .warning { color: var(--warn); background: #fff7e6; border-color: #ffd591; }
    .unknown, .idle { color: var(--idle); background: #f1f3f6; border-color: #d9dee7; }
    .kpi-mark.success { background: var(--good); border: 0; }
    .kpi-mark.failed { background: var(--bad); border: 0; }
    .kpi-mark.warning { background: var(--warn); border: 0; }
    .kpi-mark.unknown, .kpi-mark.idle { background: var(--idle); border: 0; }
    .task-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
      align-items: start;
    }
    .task-actions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; }
    .confirm {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 8px;
      padding: 12px 16px;
      border-top: 1px solid var(--line);
      background: var(--surface-soft);
    }
    .confirm input { padding: 0 10px; min-width: 0; }
    .output-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 16px;
      border-top: 1px solid var(--line);
      background: #111827;
      color: #d9e2ef;
      font-size: 12px;
      font-weight: 700;
    }
    pre {
      margin: 0;
      padding: 14px 16px;
      height: 300px;
      overflow: auto;
      background: #111827;
      color: #edf2f7;
      font-family: Consolas, "Cascadia Mono", monospace;
      font-size: 12px;
      line-height: 1.5;
      white-space: pre-wrap;
    }
    .empty {
      padding: 18px 16px;
      color: var(--muted);
      line-height: 1.6;
    }
    @media (max-width: 1180px) {
      .app-shell { grid-template-columns: 1fr; }
      aside {
        position: static;
        height: auto;
        padding: 12px 14px;
      }
      .brand { padding-bottom: 10px; }
      nav {
        grid-template-columns: repeat(3, minmax(0, 1fr));
        padding: 12px 0 0;
      }
      .nav-note { display: none; }
      .grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 760px) {
      .content { padding: 12px; }
      header { grid-template-columns: 1fr; }
      .toolbar { flex-wrap: wrap; }
      nav { grid-template-columns: 1fr; }
      .kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .task-grid, .confirm { grid-template-columns: 1fr; }
      .task-actions { justify-content: flex-start; }
      select { min-width: 0; width: 100%; }
      .section-head { align-items: stretch; flex-direction: column; }
    }
  </style>
</head>
<body>
  <div class="app-shell">
    <aside>
      <div class="brand">
        <h1>个人工作台</h1>
        <div class="brand-sub">ERP、Notion、拼多多、小程序自动化统一入口</div>
      </div>
      <nav aria-label="工作台导航">
        <a href="#overview"><span class="nav-dot"></span>状态总览</a>
        <a href="#history"><span class="nav-dot"></span>Agent 历史</a>
        <a href="#tasks"><span class="nav-dot"></span>任务执行</a>
      </nav>
      <div class="nav-note">真实任务需要输入 EXECUTE。状态检查和历史查看只读，不会写 Notion 或执行上架。</div>
    </aside>
    <div class="content">
      <header>
        <div class="page-title">
          <h2>自动化控制台</h2>
          <p>看每个项目现在的状态、按 agent 查历史记录、预览或手动确认执行脚本。</p>
        </div>
        <div class="toolbar">
          <button id="refreshBtn">刷新状态</button>
          <button id="statusBtn" class="primary">运行状态检查</button>
        </div>
      </header>
      <div class="kpis" id="kpis"></div>
      <main class="grid">
        <section id="overview" class="span-all">
          <div class="section-head">
            <div class="section-title">
              <h3>项目状态</h3>
              <span>读取四个现有项目的日志和草稿历史</span>
            </div>
            <span class="meta" id="statusMeta">读取中</span>
          </div>
          <div class="status-list" id="statusList"></div>
        </section>
        <section id="history">
          <div class="section-head">
            <div class="section-title">
              <h3>Agent 历史记录</h3>
              <span>选择 agent 后查看最近 20 条运行或保存记录</span>
            </div>
            <select id="agentSelect" aria-label="选择 Agent"></select>
          </div>
          <div class="history-list" id="historyList"></div>
        </section>
        <section id="tasks">
          <div class="section-head">
            <div class="section-title">
              <h3>任务入口</h3>
              <span>先预览命令，真实执行需要确认</span>
            </div>
            <span class="meta">受保护</span>
          </div>
          <div class="task-list" id="taskList"></div>
          <div class="confirm">
            <input id="confirmText" placeholder="执行真实任务前输入 EXECUTE" />
            <button id="clearOutputBtn">清空输出</button>
          </div>
          <div class="output-head">
            <span>运行输出</span>
            <span>本机 127.0.0.1</span>
          </div>
          <pre id="output">等待操作。</pre>
        </section>
      </main>
    </div>
  </div>
  <script>
    const statusList = document.getElementById("statusList");
    const statusMeta = document.getElementById("statusMeta");
    const taskList = document.getElementById("taskList");
    const historyList = document.getElementById("historyList");
    const agentSelect = document.getElementById("agentSelect");
    const kpis = document.getElementById("kpis");
    const output = document.getElementById("output");
    const confirmText = document.getElementById("confirmText");

    const badgeClass = (status) => {
      if (status === "成功") return "success";
      if (status === "失败") return "failed";
      if (status === "警告") return "warning";
      if (status === "未运行") return "idle";
      return "unknown";
    };
    const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));
    const writeOutput = (text) => { output.textContent = text || ""; };
    const statusOrder = ["成功", "失败", "警告", "未运行"];

    async function fetchJSON(url, options) {
      const response = await fetch(url, options);
      const text = await response.text();
      let data;
      try { data = JSON.parse(text); } catch { data = { ok: false, output: text }; }
      if (!response.ok) throw new Error(data.error || text || response.statusText);
      return data;
    }

    async function loadStatus() {
      statusMeta.textContent = "读取中";
      try {
        const data = await fetchJSON("/api/status");
        const counts = Object.fromEntries(statusOrder.map(key => [key, 0]));
        data.forEach(item => { counts[item.status] = (counts[item.status] || 0) + 1; });
        kpis.innerHTML = statusOrder.map(key => `
          <div class="kpi">
            <div>
              <strong>${counts[key] || 0}</strong>
              <span>${escapeHTML(key)}</span>
            </div>
            <i class="kpi-mark ${badgeClass(key)}"></i>
          </div>
        `).join("");
        statusList.innerHTML = data.map(item => `
          <div class="status-row">
            <div class="row-top">
              <div class="name">${escapeHTML(item.name)}</div>
              <span class="badge ${badgeClass(item.status)}">${escapeHTML(item.status)}</span>
            </div>
            <div class="summary">${escapeHTML(item.summary)}</div>
            <div class="meta">最近时间：${escapeHTML(item.latest_time)}</div>
            <div class="path">${escapeHTML(item.source)}</div>
            <div class="detail">${escapeHTML(item.next_action)}</div>
          </div>
        `).join("");
        statusMeta.textContent = `已更新 ${new Date().toLocaleTimeString()}`;
      } catch (error) {
        statusMeta.textContent = "读取失败";
        statusList.innerHTML = `<div class="status-row"><div class="summary">${escapeHTML(error.message)}</div></div>`;
      }
    }

    async function loadHistoryAgents() {
      const agents = await fetchJSON("/api/history-agents");
      agentSelect.innerHTML = agents.map(agent => `<option value="${escapeHTML(agent.id)}">${escapeHTML(agent.name)}</option>`).join("");
      agentSelect.value = "workbench";
      await loadHistory();
    }

    async function loadHistory() {
      const agent = agentSelect.value || "workbench";
      historyList.innerHTML = `<div class="empty">读取中。</div>`;
      try {
        const data = await fetchJSON(`/api/history?agent=${encodeURIComponent(agent)}&limit=20`);
        if (!data.length) {
          historyList.innerHTML = `<div class="empty">暂无历史记录。</div>`;
          return;
        }
        historyList.innerHTML = data.map(item => `
          <div class="history-row">
            <div class="row-top">
              <div class="name">${escapeHTML(item.title)}</div>
              <span class="badge ${badgeClass(item.status)}">${escapeHTML(item.status)}</span>
            </div>
            <div class="summary">${escapeHTML(item.summary)}</div>
            <div class="meta">${escapeHTML(item.time)}</div>
            <div class="path">${escapeHTML(item.source)}</div>
          </div>
        `).join("");
      } catch (error) {
        historyList.innerHTML = `<div class="empty">${escapeHTML(error.message)}</div>`;
      }
    }

    async function loadTasks() {
      const data = await fetchJSON("/api/tasks");
      taskList.innerHTML = data.map(task => `
        <div class="task-row">
          <div class="task-grid">
            <div>
              <div class="name">${escapeHTML(task.name)}</div>
              <div class="summary">${escapeHTML(task.description)}</div>
              <div class="meta">${escapeHTML(task.id)}｜写外部系统：${task.writes_external_system ? "是" : "否"}｜${task.detached ? "后台启动" : "等待完成"}</div>
              <div class="path">${escapeHTML(task.workdir)}</div>
            </div>
            <div class="task-actions">
              <button data-task="${escapeHTML(task.id)}" data-mode="dry-run">预览</button>
              <button class="${task.writes_external_system ? "danger" : ""}" data-task="${escapeHTML(task.id)}" data-mode="execute">执行</button>
            </div>
          </div>
        </div>
      `).join("");
    }

    async function runTask(task, mode) {
      writeOutput(`正在${mode === "execute" ? "执行" : "预览"}：${task}`);
      try {
        const payload = { task, mode, confirm: confirmText.value };
        const data = await fetchJSON("/api/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        writeOutput(data.output || JSON.stringify(data, null, 2));
        await loadStatus();
        await loadHistory();
      } catch (error) {
        writeOutput(error.message);
      }
    }

    document.getElementById("refreshBtn").addEventListener("click", loadStatus);
    document.getElementById("statusBtn").addEventListener("click", () => runTask("status", "execute"));
    document.getElementById("clearOutputBtn").addEventListener("click", () => writeOutput("等待操作。"));
    agentSelect.addEventListener("change", loadHistory);
    taskList.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-task]");
      if (!button) return;
      runTask(button.dataset.task, button.dataset.mode);
    });

    loadStatus();
    loadHistoryAgents();
    loadTasks();
  </script>
</body>
</html>
"""


class WorkbenchHandler(BaseHTTPRequestHandler):
    server_version = "WorkbenchApp/1.0"

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return

    def send_json(self, payload: object, status: int = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_html(self, html: str) -> None:
        data = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self.send_html(INDEX_HTML)
            return
        if path == "/api/status":
            self.send_json([asdict(item) for item in collect_statuses(None, 160)])
            return
        if path == "/api/tasks":
            self.send_json([asdict(task) for task in TASKS.values()])
            return
        if path == "/api/workbench-runs":
            self.send_json(read_workbench_runs())
            return
        if path == "/api/history-agents":
            self.send_json(history_agents())
            return
        if path == "/api/history":
            query = parse_qs(parsed.query)
            agent = str((query.get("agent") or ["workbench"])[0])
            try:
                limit = int((query.get("limit") or ["20"])[0])
            except ValueError:
                limit = 20
            self.send_json([asdict(item) for item in collect_history(agent, limit=max(1, min(limit, 100)))])
            return
        self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/run":
            self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(body or "{}")
        except (ValueError, json.JSONDecodeError):
            self.send_json({"error": "请求 JSON 无效"}, HTTPStatus.BAD_REQUEST)
            return

        task_id = str(payload.get("task") or "")
        mode = str(payload.get("mode") or "dry-run")
        confirm = str(payload.get("confirm") or "")
        if task_id not in TASKS:
            self.send_json({"error": f"未知任务：{task_id}"}, HTTPStatus.BAD_REQUEST)
            return
        if mode not in {"dry-run", "execute"}:
            self.send_json({"error": f"未知模式：{mode}"}, HTTPStatus.BAD_REQUEST)
            return
        if mode == "execute" and task_id != "status" and confirm != "EXECUTE":
            self.send_json({"error": "执行真实任务前需要输入 EXECUTE。"}, HTTPStatus.BAD_REQUEST)
            return

        command = [sys.executable, str(WORKBENCH_ROOT / "tools" / "workbench_run.py"), task_id]
        if mode == "dry-run":
            command.append("--dry-run")
        else:
            command.append("--execute")

        completed = subprocess.run(
            command,
            cwd=WORKBENCH_ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
        output = completed.stdout
        if completed.stderr:
            output = output + ("\n" if output else "") + completed.stderr
        self.send_json({"ok": completed.returncode == 0, "exit_code": completed.returncode, "output": output})


def read_workbench_runs(limit: int = 20) -> list[dict[str, object]]:
    if not LOG_PATH.exists():
        return []
    rows: list[dict[str, object]] = []
    with LOG_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows[-limit:]


def read_json_file(path: Path) -> object | None:
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


def history_agents() -> list[dict[str, str]]:
    return [
        {"id": "workbench", "name": "工作台运行记录"},
        {"id": "pdd_ads", "name": "拼多多广告同步"},
        {"id": "pdd_weekly", "name": "拼多多周报"},
        {"id": "pdd_publisher", "name": "拼多多自动上架"},
        {"id": "erp_miniapp", "name": "小程序 ERP 自动上架"},
    ]


def collect_history(agent: str, limit: int = 20) -> list[HistoryEntry]:
    if agent == "workbench":
        entries = []
        for row in reversed(read_workbench_runs(limit)):
            status = "成功" if row.get("status") == "success" else "失败"
            entries.append(
                HistoryEntry(
                    time=str(row.get("finished_at") or row.get("started_at") or "-")[:19].replace("T", " "),
                    status=status,
                    title=str(row.get("script") or "-"),
                    summary=str(row.get("message") or row.get("command") or "-"),
                    source=str(LOG_PATH),
                )
            )
        return entries

    if agent == "pdd_publisher":
        config = PROJECTS["pdd_publisher"]
        history_path = config["history_path"]
        assert isinstance(history_path, Path)
        data = read_json_file(history_path)
        items = data.get("items") if isinstance(data, dict) else []
        if not isinstance(items, list):
            return []
        entries = []
        for item in reversed(items[-limit:]):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "未记录标题")
            mall = str(item.get("mall_name") or item.get("shop_name") or "未知店铺")
            link = str(item.get("goods_url") or item.get("goods_id") or "")
            entries.append(
                HistoryEntry(
                    time=str(item.get("saved_at") or "-"),
                    status="成功",
                    title=title,
                    summary=f"{mall}" + (f" | {link}" if link else ""),
                    source=str(history_path),
                )
            )
        return entries

    if agent not in PROJECTS:
        return []

    config = PROJECTS[agent]
    log_dir = config.get("log_dir")
    patterns = config.get("patterns")
    if not isinstance(log_dir, Path) or not isinstance(patterns, list):
        return []

    files = []
    for pattern in patterns:
        files.extend(path for path in log_dir.glob(pattern) if path.is_file())
    files = sorted(set(files), key=lambda path: path.stat().st_mtime, reverse=True)[:limit]
    entries = []
    for path in files:
        text = read_text_tail(path, 220)
        status = classify_history_status(agent, text)
        summary = summarize_log(agent, text)
        entries.append(
            HistoryEntry(
                time=path.stat().st_mtime_ns and path_mtime(path),
                status=status,
                title=path.name,
                summary=summary,
                source=str(path),
            )
        )
    return entries


def classify_history_status(agent: str, text: str) -> str:
    if agent == "pdd_weekly" and "周报生成完成" in text:
        return "成功"
    if agent == "erp_miniapp" and any(token in text for token in ("流程完成", "上传测试已完成", "已完成上架信息填写")):
        return "警告" if any(token in text for token in (" WARNING", "警告", "缺失")) else "成功"
    if agent == "pdd_ads":
        if "Exit code: 0" in text:
            return "成功"
        if any(token in text for token in ("Exit code: 1", " ERROR", "失败", "NotionSyncError", "Traceback")):
            return "失败"
    status, _, _, _ = classify_log(agent, text)
    return status


def path_mtime(path: Path) -> str:
    from datetime import datetime

    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")


def summarize_log(agent: str, text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "空日志。"

    priorities = {
        "pdd_ads": ["Exit code:", "补漏检查完成", "同步完成", "ERROR", "Notion 请求失败", "缺少数据"],
        "pdd_weekly": ["周报生成完成", "检测到重复周报", "生成行数", "CRITICAL", "ERROR"],
        "erp_miniapp": ["流程完成", "上传测试已完成", "已完成上架信息填写", "ERROR", "WARNING"],
    }.get(agent, ["完成", "成功", "ERROR", "WARNING"])
    for token in priorities:
        for line in reversed(lines):
            if token in line:
                return line[:220]
    return lines[-1][:220]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="启动个人工作台本地网页。")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    return parser.parse_args()


def main() -> int:
    configure_console()
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), WorkbenchHandler)
    url = f"http://{args.host}:{args.port}/"
    print(f"工作台网页已启动：{url}")
    print("按 Ctrl+C 停止。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("工作台网页已停止。")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
