#!/usr/bin/env python3
"""Local web dashboard for the personal workbench."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from workbench_external_status import collect_statuses
from workbench_log import LOG_PATH, configure_console
from workbench_run import TASKS


WORKBENCH_ROOT = Path(__file__).resolve().parents[1]


INDEX_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>个人工作台</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #ffffff;
      --line: #d9dee7;
      --text: #1d2430;
      --muted: #657084;
      --good: #147d4f;
      --bad: #b42318;
      --warn: #a15c00;
      --idle: #556070;
      --focus: #2563eb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      font-size: 14px;
      letter-spacing: 0;
    }
    header {
      height: 56px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 24px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    h1 { margin: 0; font-size: 18px; font-weight: 650; }
    main {
      display: grid;
      grid-template-columns: minmax(420px, 1.05fr) minmax(420px, .95fr);
      gap: 16px;
      padding: 16px;
      max-width: 1480px;
      margin: 0 auto;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      min-width: 0;
    }
    .section-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
    }
    h2 { margin: 0; font-size: 15px; font-weight: 650; }
    button, select, input {
      font: inherit;
      min-height: 34px;
      border-radius: 6px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
    }
    button {
      padding: 0 12px;
      cursor: pointer;
      white-space: nowrap;
    }
    button.primary { background: var(--focus); border-color: var(--focus); color: #fff; }
    button.danger { background: #fff7f5; border-color: #f2b8b5; color: var(--bad); }
    button:disabled { opacity: .55; cursor: not-allowed; }
    .status-list, .task-list { display: grid; gap: 0; }
    .status-row, .task-row {
      display: grid;
      gap: 10px;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
    }
    .status-row:last-child, .task-row:last-child { border-bottom: 0; }
    .row-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .name { font-weight: 650; min-width: 0; overflow-wrap: anywhere; }
    .summary, .meta, .detail, .path { color: var(--muted); line-height: 1.5; overflow-wrap: anywhere; }
    .badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 54px;
      height: 26px;
      padding: 0 9px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 650;
      border: 1px solid transparent;
    }
    .success { color: var(--good); background: #eaf7ef; border-color: #b9e4c6; }
    .failed { color: var(--bad); background: #fff1f0; border-color: #f2b8b5; }
    .warning { color: var(--warn); background: #fff7e6; border-color: #ffd591; }
    .unknown, .idle { color: var(--idle); background: #f1f3f6; border-color: #d9dee7; }
    .task-actions { display: flex; flex-wrap: wrap; gap: 8px; }
    .task-grid { display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: start; }
    .confirm {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      padding: 12px 16px;
      border-top: 1px solid var(--line);
      background: #fbfcfe;
    }
    .confirm input { padding: 0 10px; min-width: 0; }
    pre {
      margin: 0;
      padding: 14px 16px;
      height: 330px;
      overflow: auto;
      border-top: 1px solid var(--line);
      background: #111827;
      color: #e5e7eb;
      font-family: Consolas, "Cascadia Mono", monospace;
      font-size: 12px;
      line-height: 1.5;
      white-space: pre-wrap;
    }
    .toolbar { display: flex; align-items: center; gap: 8px; }
    @media (max-width: 980px) {
      main { grid-template-columns: 1fr; }
      header { padding: 0 16px; }
      .task-grid, .confirm { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>个人工作台</h1>
    <div class="toolbar">
      <button id="refreshBtn">刷新状态</button>
      <button id="statusBtn" class="primary">运行状态检查</button>
    </div>
  </header>
  <main>
    <section>
      <div class="section-head">
        <h2>项目状态</h2>
        <span class="meta" id="statusMeta">读取中</span>
      </div>
      <div class="status-list" id="statusList"></div>
    </section>
    <section>
      <div class="section-head">
        <h2>任务入口</h2>
        <span class="meta">执行任务需要确认</span>
      </div>
      <div class="task-list" id="taskList"></div>
      <div class="confirm">
        <input id="confirmText" placeholder="执行真实任务前输入 EXECUTE" />
        <button id="clearOutputBtn">清空输出</button>
      </div>
      <pre id="output">等待操作。</pre>
    </section>
  </main>
  <script>
    const statusList = document.getElementById("statusList");
    const statusMeta = document.getElementById("statusMeta");
    const taskList = document.getElementById("taskList");
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
      } catch (error) {
        writeOutput(error.message);
      }
    }

    document.getElementById("refreshBtn").addEventListener("click", loadStatus);
    document.getElementById("statusBtn").addEventListener("click", () => runTask("status", "execute"));
    document.getElementById("clearOutputBtn").addEventListener("click", () => writeOutput("等待操作。"));
    taskList.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-task]");
      if (!button) return;
      runTask(button.dataset.task, button.dataset.mode);
    });

    loadStatus();
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
        path = urlparse(self.path).path
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

