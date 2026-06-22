#!/usr/bin/env python3
"""Local web dashboard for the personal workbench."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
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
    details: list[str] = field(default_factory=list)


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
      grid-template-columns: 318px minmax(0, 1fr);
      min-height: 100vh;
      padding-top: 48px;
    }
    .topbar {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 0 18px;
      background: #fff;
      border-bottom: 1px solid var(--line);
      z-index: 5;
    }
    .topbrand {
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 750;
    }
    .logo-mark {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 26px;
      height: 26px;
      border-radius: 7px;
      background: var(--accent);
      color: #fff;
      font-weight: 800;
      font-size: 14px;
    }
    .breadcrumb { color: var(--muted); font-weight: 500; }
    .top-actions { display: flex; align-items: center; gap: 12px; color: var(--muted); }
    .local-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--good);
    }
    .icon-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 30px;
      min-height: 30px;
      padding: 0;
      color: var(--muted);
    }
    aside {
      position: sticky;
      top: 48px;
      height: calc(100vh - 48px);
      padding: 18px 14px;
      background: var(--surface);
      color: var(--text);
      border-right: 1px solid var(--line);
      overflow: auto;
    }
    .brand {
      display: grid;
      gap: 5px;
      padding: 6px 8px 14px;
      border-bottom: 1px solid var(--line);
    }
    h1 { margin: 0; font-size: 18px; font-weight: 700; }
    .brand-sub { color: var(--muted); font-size: 12px; line-height: 1.5; }
    .agent-tools {
      display: grid;
      gap: 10px;
      padding: 14px 8px 10px;
    }
    .agent-list-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      font-weight: 750;
    }
    .filter-row {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
    .filter-chip {
      min-height: 30px;
      padding: 0 10px;
      border-color: var(--line);
      background: #fff;
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
    }
    .filter-chip.active {
      background: var(--accent-weak);
      border-color: #b8cffb;
      color: var(--accent);
    }
    .agent-search {
      width: 100%;
      padding: 0 10px;
      border-color: var(--line);
      background: var(--surface-soft);
    }
    .agent-list {
      display: grid;
      gap: 6px;
      padding: 0 8px 12px;
    }
    .agent-button {
      display: grid;
      grid-template-columns: 42px minmax(0, 1fr) auto;
      gap: 5px 10px;
      align-items: center;
      width: 100%;
      min-height: 86px;
      padding: 10px;
      border: 1px solid transparent;
      border-radius: 8px;
      background: transparent;
      text-align: left;
      color: var(--text);
    }
    .agent-button:hover { background: var(--surface-soft); border-color: var(--line); }
    .agent-button.active { background: var(--accent-weak); border-color: #b8cffb; }
    .agent-icon {
      grid-column: 1;
      grid-row: 1 / 4;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      border-radius: 9px;
      color: #fff;
      font-weight: 800;
      box-shadow: inset 0 0 0 1px rgba(255,255,255,.25);
    }
    .icon-workbench { background: #475569; }
    .icon-pdd_ads, .icon-pdd_publisher { background: #dc2626; }
    .icon-pdd_weekly { background: #111827; }
    .icon-erp_miniapp { background: #2563eb; }
    .agent-name { grid-column: 2; grid-row: 1; font-weight: 700; overflow-wrap: anywhere; }
    .agent-button .badge { grid-column: 3; grid-row: 1; justify-self: end; align-self: start; }
    .agent-sub { grid-column: 2 / 4; grid-row: 2; color: var(--muted); font-size: 12px; line-height: 1.45; overflow-wrap: anywhere; }
    .agent-count { grid-column: 2; grid-row: 3; color: var(--muted); font-size: 12px; }
    .risk {
      grid-column: 3;
      grid-row: 3;
      justify-self: end;
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }
    .sidebar-foot {
      padding: 12px 8px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 12px;
    }
    nav { display: grid; gap: 6px; padding: 16px 0; }
    nav a {
      display: flex;
      align-items: center;
      gap: 9px;
      min-height: 36px;
      padding: 0 10px;
      border-radius: 6px;
      color: var(--text);
      text-decoration: none;
      font-weight: 600;
    }
    nav a:hover { background: var(--surface-soft); }
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
      border-top: 1px solid var(--line);
      color: var(--muted);
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
    .is-running button[data-task],
    .is-running #statusBtn {
      pointer-events: none;
    }
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
    .detail-header {
      display: grid;
      gap: 12px;
      padding: 16px;
      margin-bottom: 14px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
    }
    .detail-title-row {
      display: flex;
      justify-content: space-between;
      align-items: start;
      gap: 14px;
    }
    .detail-title {
      display: grid;
      grid-template-columns: 44px minmax(0, 1fr);
      gap: 5px 12px;
      min-width: 0;
    }
    .detail-title .agent-icon { grid-row: span 3; width: 40px; height: 40px; }
    .detail-title h3 { font-size: 20px; }
    .detail-title h3, .detail-title .summary, .detail-title .path { grid-column: 2; }
    .detail-actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
    .detail-metrics {
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 10px;
    }
    .mini-metric {
      display: grid;
      gap: 4px;
      padding: 11px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-soft);
      min-height: 68px;
    }
    .mini-metric strong { font-size: 18px; line-height: 1.1; }
    .mini-metric span { color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
    .workspace {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 14px;
    }
    .tabs {
      display: flex;
      gap: 4px;
      padding: 8px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfe;
    }
    .tab {
      min-height: 32px;
      padding: 0 12px;
      border-color: transparent;
      background: transparent;
      font-weight: 650;
      color: var(--muted);
    }
    .tab.active {
      background: #fff;
      color: var(--accent);
      border-color: var(--line);
    }
    .tab-panel[hidden] { display: none; }
    .tab-panel { min-height: 260px; }
    .panel-note {
      padding: 12px 16px;
      color: var(--muted);
      border-bottom: 1px solid var(--line);
      background: var(--surface-soft);
      line-height: 1.5;
    }
    .run-grid {
      display: grid;
      grid-template-columns: minmax(360px, .9fr) minmax(380px, 1.1fr);
      gap: 14px;
      padding: 14px 16px;
    }
    .run-box {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: #fff;
      display: grid;
      gap: 12px;
    }
    .run-box h4 {
      margin: 0;
      font-size: 14px;
    }
    .control-grid {
      display: grid;
      grid-template-columns: 96px minmax(0, 1fr);
      gap: 10px;
      align-items: center;
    }
    .fake-select {
      min-height: 34px;
      display: flex;
      align-items: center;
      padding: 0 10px;
      border: 1px solid var(--line-strong);
      border-radius: 6px;
      background: var(--surface-soft);
      color: var(--text);
    }
    .command-preview {
      min-height: 170px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #f8fafc;
      color: #334155;
      font-family: Consolas, "Cascadia Mono", monospace;
      font-size: 12px;
      line-height: 1.6;
      white-space: pre-wrap;
      overflow: auto;
    }
    .run-inline-actions { display: flex; gap: 8px; flex-wrap: wrap; }
    .ads-panel {
      padding: 16px;
      border-bottom: 1px solid var(--line);
      background: #fff;
    }
    .ads-panel h4 {
      margin: 0 0 6px;
      font-size: 17px;
    }
    .ads-panel .summary {
      margin-bottom: 14px;
    }
    .ads-form {
      display: grid;
      grid-template-columns: repeat(4, minmax(150px, 1fr)) minmax(170px, auto);
      gap: 12px 14px;
      align-items: end;
      max-width: 980px;
    }
    .field {
      display: grid;
      gap: 6px;
    }
    .field label {
      color: var(--text);
      font-weight: 650;
      font-size: 13px;
    }
    .field input, .field select {
      min-width: 0;
      width: 100%;
      padding: 0 10px;
    }
    .check-field {
      display: flex;
      align-items: center;
      gap: 8px;
      min-height: 34px;
      color: var(--text);
      font-weight: 650;
    }
    .check-field input {
      width: 16px;
      min-height: 16px;
    }
    .ads-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 14px;
    }
    .ads-actions .right-actions {
      margin-left: auto;
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
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
    .history-details {
      display: grid;
      gap: 4px;
      margin: 2px 0 0;
      padding: 0;
      list-style: none;
    }
    .history-details li {
      color: var(--muted);
      line-height: 1.45;
      overflow-wrap: anywhere;
    }
    .history-details li::before {
      content: "- ";
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
    .agent-button .badge {
      width: fit-content;
      justify-self: end;
      align-self: start;
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
    .run-state {
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .run-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #64748b;
    }
    .run-dot.active {
      background: #60a5fa;
      animation: pulse 1s infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: .35; }
      50% { opacity: 1; }
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
      .agent-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .detail-metrics { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .run-grid { grid-template-columns: 1fr; }
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
      .agent-list { grid-template-columns: 1fr; }
      .kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .detail-title-row { display: grid; }
      .detail-title { grid-template-columns: 40px minmax(0, 1fr); }
      .detail-actions { justify-content: flex-start; }
      .detail-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .run-grid { padding: 12px; }
      .ads-form { grid-template-columns: 1fr; }
      .ads-actions .right-actions { margin-left: 0; }
      .control-grid { grid-template-columns: 1fr; }
      .task-grid, .confirm { grid-template-columns: 1fr; }
      .task-actions { justify-content: flex-start; }
      select { min-width: 0; width: 100%; }
      .section-head { align-items: stretch; flex-direction: column; }
    }
  </style>
</head>
<body>
  <div class="topbar">
    <div class="topbrand">
      <span class="logo-mark">W</span>
      <span>自动化控制台</span>
      <span class="breadcrumb">/ 个人工作台</span>
    </div>
    <div class="top-actions">
      <span class="local-dot"></span>
      <span>本机 127.0.0.1</span>
      <button class="icon-btn" type="button" title="设置">⚙</button>
      <button class="icon-btn" type="button" title="帮助">?</button>
      <span>运营同学</span>
    </div>
  </div>
  <div class="app-shell">
    <aside>
      <div class="brand">
        <h1>Agent 列表 (<span id="agentTotal">0</span>)</h1>
        <div class="brand-sub">ERP、Notion、拼多多、小程序自动化统一入口</div>
      </div>
      <div class="agent-tools">
        <div class="agent-list-head">
          <span>筛选</span>
          <button class="icon-btn" id="clearSearchBtn" type="button" title="清空搜索">×</button>
        </div>
        <input class="agent-search" id="agentSearch" placeholder="搜索 Agent 名称 / 备注 / 命令..." />
        <div class="filter-row" id="agentFilters">
          <button class="filter-chip active" data-filter="all" type="button">全部 <span id="filterAll">0</span></button>
          <button class="filter-chip" data-filter="成功" type="button">成功 <span id="filterSuccess">0</span></button>
          <button class="filter-chip" data-filter="警告" type="button">警告 <span id="filterWarning">0</span></button>
          <button class="filter-chip" data-filter="失败" type="button">失败 <span id="filterFailed">0</span></button>
          <button class="filter-chip" data-filter="未运行" type="button">未运行 <span id="filterIdle">0</span></button>
        </div>
      </div>
      <div class="agent-list" id="agentList"></div>
      <div class="sidebar-foot" id="agentTotalFoot">共 0 项</div>
      <div class="nav-note">真实任务需要输入 EXECUTE。状态检查和历史查看只读，不会写 Notion 或执行上架。</div>
    </aside>
    <div class="content">
      <header>
        <div class="page-title">
          <h2>Agent 详情工作区</h2>
          <p>左侧选择 agent，右侧集中处理运行、历史和实时日志。</p>
        </div>
        <div class="toolbar">
          <button id="refreshBtn">刷新状态</button>
          <button id="statusBtn" class="primary">运行状态检查</button>
        </div>
      </header>
      <section class="detail-header">
        <div class="detail-title-row">
          <div class="detail-title">
            <span class="agent-icon icon-erp_miniapp" id="selectedAgentIcon">ERP</span>
            <h3 id="selectedAgentName">读取中</h3>
            <div class="summary" id="selectedAgentSummary">正在读取 agent 状态。</div>
            <div class="path" id="selectedAgentSource">-</div>
          </div>
          <div class="detail-actions">
            <select id="agentSelect" aria-label="选择 Agent"></select>
            <button id="refreshAgentBtn">刷新当前</button>
          </div>
        </div>
        <div class="detail-metrics" id="agentMetrics"></div>
      </section>
      <main class="workspace">
        <section>
          <div class="tabs" role="tablist">
            <button class="tab active" data-tab="run" type="button">运行</button>
            <button class="tab" data-tab="history" type="button">历史</button>
            <button class="tab" data-tab="logs" type="button">日志</button>
            <button class="tab" data-tab="files" type="button">文件</button>
          </div>
          <div class="tab-panel" id="tab-run">
            <div class="panel-note">只显示当前 agent 相关任务。先点预览，确认无误后再输入 EXECUTE 执行。</div>
            <div class="task-list" id="taskList"></div>
            <div class="confirm">
              <input id="confirmText" placeholder="执行真实任务前输入 EXECUTE" />
              <button id="clearOutputBtn">清空输出</button>
            </div>
          </div>
          <div class="tab-panel" id="tab-history" hidden>
            <div class="panel-note">当前 agent 最近 20 条历史记录，ERP 小程序会展开素材目录、SKU、上传统计和 warning。</div>
            <div class="history-list" id="historyList"></div>
          </div>
          <div class="tab-panel" id="tab-logs" hidden>
            <div class="panel-note">实时输出固定在下方；执行任务时会逐行滚动显示脚本 stdout/stderr。</div>
            <div class="status-list" id="statusList"></div>
          </div>
          <div class="tab-panel" id="tab-files" hidden>
            <div class="panel-note">当前 agent 的关键目录、日志源和下一步建议。</div>
            <div class="status-list" id="fileList"></div>
          </div>
        </section>
        <section>
          <div class="output-head">
            <span class="run-state"><i class="run-dot" id="runDot"></i><span id="runStateText">运行输出</span></span>
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
    const agentList = document.getElementById("agentList");
    const agentSearch = document.getElementById("agentSearch");
    const agentFilters = document.getElementById("agentFilters");
    const agentTotal = document.getElementById("agentTotal");
    const agentTotalFoot = document.getElementById("agentTotalFoot");
    const filterAll = document.getElementById("filterAll");
    const filterSuccess = document.getElementById("filterSuccess");
    const filterWarning = document.getElementById("filterWarning");
    const filterFailed = document.getElementById("filterFailed");
    const filterIdle = document.getElementById("filterIdle");
    const clearSearchBtn = document.getElementById("clearSearchBtn");
    const selectedAgentName = document.getElementById("selectedAgentName");
    const selectedAgentIcon = document.getElementById("selectedAgentIcon");
    const selectedAgentSummary = document.getElementById("selectedAgentSummary");
    const selectedAgentSource = document.getElementById("selectedAgentSource");
    const agentMetrics = document.getElementById("agentMetrics");
    const fileList = document.getElementById("fileList");
    const output = document.getElementById("output");
    const confirmText = document.getElementById("confirmText");
    const runDot = document.getElementById("runDot");
    const runStateText = document.getElementById("runStateText");

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
    const appendOutput = (text) => {
      output.textContent += text;
      output.scrollTop = output.scrollHeight;
    };
    const statusOrder = ["成功", "失败", "警告", "未运行"];
    const taskAgent = {
      "status": "workbench",
      "pdd-ads-catchup": "pdd_ads",
      "pdd-ads-sync-all": "pdd_ads",
      "pdd-weekly-report": "pdd_weekly",
      "pdd-publisher": "pdd_publisher",
      "erp-miniapp-upload": "erp_miniapp"
    };
    const agentIcons = {
      workbench: "工",
      pdd_ads: "拼",
      pdd_weekly: "周",
      pdd_publisher: "上",
      erp_miniapp: "ERP"
    };
    const riskMap = {
      workbench: "低风险",
      pdd_ads: "中风险",
      pdd_weekly: "中风险",
      pdd_publisher: "低风险",
      erp_miniapp: "中风险"
    };
    const scheduleMap = {
      workbench: "手动",
      pdd_ads: "明日 09:00",
      pdd_weekly: "下周一 10:00",
      pdd_publisher: "手动",
      erp_miniapp: "手动"
    };
    let allAgents = [];
    let allStatuses = [];
    let allTasks = [];
    let selectedAgent = "erp_miniapp";
    let agentFilter = "all";
    let runningTask = null;
    let runningTimer = null;
    let runningStartedAt = 0;
    let activeRunController = null;

    function agentIcon(agentId) {
      return agentIcons[agentId] || "A";
    }

    function riskForAgent(agentId) {
      return riskMap[agentId] || "低风险";
    }

    function agentSubtitle(agentId) {
      const task = tasksForAgent(agentId)[0];
      return `${task ? task.id : agentId} | 外部系统`;
    }

    function successRate(status) {
      if (status === "成功") return "100%";
      if (status === "失败") return "0%";
      if (status === "警告") return "需复核";
      return "-";
    }

    function defaultYesterday() {
      const date = new Date();
      date.setDate(date.getDate() - 1);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, "0");
      const day = String(date.getDate()).padStart(2, "0");
      return `${year}-${month}-${day}`;
    }

    async function fetchJSON(url, options) {
      const response = await fetch(url, options);
      const text = await response.text();
      let data;
      try { data = JSON.parse(text); } catch { data = { ok: false, output: text }; }
      if (!response.ok) throw new Error(data.error || text || response.statusText);
      return data;
    }

    async function loadStatus() {
      try {
        const data = await fetchJSON("/api/status");
        allStatuses = data;
        renderAgentList();
        renderSelectedAgent();
      } catch (error) {
        selectedAgentSummary.textContent = `读取失败：${error.message}`;
      }
    }

    function statusForAgent(agentId) {
      if (agentId === "workbench") {
        return {
          id: "workbench",
          name: "工作台运行记录",
          status: "成功",
          summary: "工作台本机服务已启动。",
          latest_time: new Date().toLocaleTimeString(),
          source: "D:\\desktop\\codex\\工作台",
          next_action: "选择任务预览或执行。"
        };
      }
      return allStatuses.find(item => item.id === agentId) || {
        id: agentId,
        name: agentName(agentId),
        status: "未知",
        summary: "暂未读取到状态。",
        latest_time: "-",
        source: "-",
        next_action: "刷新状态。"
      };
    }

    function agentName(agentId) {
      return allAgents.find(agent => agent.id === agentId)?.name || agentId;
    }

    function tasksForAgent(agentId) {
      return allTasks.filter(task => taskAgent[task.id] === agentId);
    }

    function renderAgentList() {
      const query = (agentSearch.value || "").trim().toLowerCase();
      agentTotal.textContent = String(allAgents.length);
      agentTotalFoot.textContent = `共 ${allAgents.length} 项`;
      const counts = { all: allAgents.length, "成功": 0, "警告": 0, "失败": 0, "未运行": 0 };
      allAgents.forEach(agent => {
        const currentStatus = statusForAgent(agent.id).status || "未知";
        if (counts[currentStatus] !== undefined) counts[currentStatus] += 1;
      });
      filterAll.textContent = String(counts.all);
      filterSuccess.textContent = String(counts["成功"]);
      filterWarning.textContent = String(counts["警告"]);
      filterFailed.textContent = String(counts["失败"]);
      filterIdle.textContent = String(counts["未运行"]);

      const filtered = allAgents.filter(agent => {
        const status = statusForAgent(agent.id);
        const haystack = `${agent.name} ${agent.id} ${status.summary || ""} ${agentSubtitle(agent.id)}`.toLowerCase();
        const matchesQuery = !query || haystack.includes(query);
        const matchesFilter = agentFilter === "all" || status.status === agentFilter;
        return matchesQuery && matchesFilter;
      });
      agentList.innerHTML = filtered.map(agent => {
        const status = statusForAgent(agent.id);
        return `
          <button class="agent-button ${agent.id === selectedAgent ? "active" : ""}" data-agent="${escapeHTML(agent.id)}" type="button">
            <span class="agent-icon icon-${escapeHTML(agent.id)}">${escapeHTML(agentIcon(agent.id))}</span>
            <span class="agent-name">${escapeHTML(agent.name)}</span>
            <span class="badge ${badgeClass(status.status)}">${escapeHTML(status.status)}</span>
            <span class="agent-sub">${escapeHTML(agentSubtitle(agent.id))}</span>
            <span class="agent-count">最近运行：${escapeHTML(status.latest_time || "-")}</span>
            <span class="risk">${escapeHTML(riskForAgent(agent.id))}</span>
          </button>
        `;
      }).join("") || `<div class="empty">没有匹配的 Agent。</div>`;
    }

    function renderSelectedAgent() {
      const status = statusForAgent(selectedAgent);
      const tasks = tasksForAgent(selectedAgent);
      selectedAgentIcon.className = `agent-icon icon-${selectedAgent}`;
      selectedAgentIcon.textContent = agentIcon(selectedAgent);
      selectedAgentName.textContent = status.name || agentName(selectedAgent);
      selectedAgentSummary.textContent = status.summary || "-";
      selectedAgentSource.textContent = status.source || "-";
      agentMetrics.innerHTML = [
        ["状态", status.status || "未知"],
        ["风险等级", riskForAgent(selectedAgent)],
        ["最近运行", status.latest_time || "-"],
        ["下次计划运行", scheduleMap[selectedAgent] || "手动"],
        ["成功率（近 7 天）", successRate(status.status)],
        ["最近结果", status.status || "未知"]
      ].map(([label, value]) => `
        <div class="mini-metric">
          <strong>${escapeHTML(value)}</strong>
          <span>${escapeHTML(label)}</span>
        </div>
      `).join("");
      statusList.innerHTML = `
        <div class="status-row">
          <div class="row-top">
            <div class="name">${escapeHTML(status.name || agentName(selectedAgent))}</div>
            <span class="badge ${badgeClass(status.status)}">${escapeHTML(status.status)}</span>
          </div>
          <div class="summary">${escapeHTML(status.summary)}</div>
          <div class="meta">最近时间：${escapeHTML(status.latest_time)}</div>
          <div class="path">${escapeHTML(status.source)}</div>
          <div class="detail">${escapeHTML(status.next_action)}</div>
        </div>
      `;
      fileList.innerHTML = `
        <div class="status-row">
          <div class="name">状态来源</div>
          <div class="path">${escapeHTML(status.source || "-")}</div>
        </div>
        <div class="status-row">
          <div class="name">任务工作目录</div>
          ${tasks.map(task => `<div class="path">${escapeHTML(task.name)}：${escapeHTML(task.workdir)}</div>`).join("") || `<div class="summary">暂无关联任务。</div>`}
        </div>
      `;
      renderTasks();
      loadHistory();
    }

    function renderAllStatuses() {
      statusList.innerHTML = allStatuses.map(item => `
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
    }

    async function loadHistoryAgents() {
      const agents = await fetchJSON("/api/history-agents");
      allAgents = agents;
      agentSelect.innerHTML = agents.map(agent => `<option value="${escapeHTML(agent.id)}">${escapeHTML(agent.name)}</option>`).join("");
      agentSelect.value = selectedAgent;
      renderAgentList();
      renderSelectedAgent();
    }

    async function loadHistory() {
      const agent = selectedAgent || "workbench";
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
            ${item.details?.length ? `<ul class="history-details">${item.details.map(detail => `<li>${escapeHTML(detail)}</li>`).join("")}</ul>` : ""}
            <div class="path">${escapeHTML(item.source)}</div>
          </div>
        `).join("");
      } catch (error) {
        historyList.innerHTML = `<div class="empty">${escapeHTML(error.message)}</div>`;
      }
    }

    async function loadTasks() {
      const data = await fetchJSON("/api/tasks");
      allTasks = data;
      renderAgentList();
      renderSelectedAgent();
    }

    function renderTasks() {
      const tasks = tasksForAgent(selectedAgent);
      if (!tasks.length) {
        taskList.innerHTML = `<div class="empty">当前 agent 暂无可执行任务。</div>`;
        return;
      }
      const adsPanel = selectedAgent === "pdd_ads" ? renderAdsPanel() : "";
      const visibleTasks = selectedAgent === "pdd_ads"
        ? tasks.filter(task => task.id === "pdd-ads-sync-all")
        : tasks;
      const runPanel = renderRunPanel(visibleTasks);
      const genericTaskRows = selectedAgent === "pdd_ads" ? "" : visibleTasks.map(task => `
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
      taskList.innerHTML = adsPanel + runPanel + genericTaskRows;
    }

    function renderRunPanel(tasks) {
      const firstTask = tasks[0];
      const command = commandPreview(firstTask);
      return `
        <div class="run-grid">
          <div class="run-box">
            <h4>执行控制</h4>
            <div class="control-grid">
              <span>运行模式</span><span class="fake-select">${firstTask.writes_external_system ? "真实执行（写操作）" : "本地启动 / 只读"}</span>
              <span>目标环境</span><span class="fake-select">本机 127.0.0.1</span>
              <span>预览范围</span><span class="fake-select">${tasks.length > 1 ? `${tasks.length} 个任务` : "当前任务"}</span>
              <span>执行窗口</span><span class="fake-select">${firstTask.detached ? "后台启动" : "等待完成"}</span>
            </div>
            <label class="check-field"><input type="checkbox" checked disabled /> 执行前先预览（推荐）</label>
            <label class="check-field"><input type="checkbox" checked disabled /> 输出实时滚动显示</label>
            <div class="run-inline-actions">
              <button class="${firstTask.writes_external_system ? "danger" : ""}" data-task="${escapeHTML(firstTask.id)}" data-mode="execute" type="button">执行（写入）</button>
              <button data-task="${escapeHTML(firstTask.id)}" data-mode="dry-run" type="button">预览（只读）</button>
            </div>
          </div>
          <div class="run-box">
            <h4>命令预览</h4>
            <pre class="command-preview">${escapeHTML(command)}</pre>
            <div class="panel-note">说明：预览只展示工作台将执行的命令；真实写入仍需要输入 EXECUTE。</div>
          </div>
        </div>
      `;
    }

    function commandPreview(task) {
      if (!task) return "";
      return `${task.command}\n\n工作目录：${task.workdir}\n写外部系统：${task.writes_external_system ? "是" : "否"}`;
    }

    function renderAdsPanel() {
      const date = defaultYesterday();
      return `
        <div class="ads-panel">
          <h4>拼多多广告数据同步</h4>
          <div class="summary">默认同步一到七店。ERP 登录过期时会优先用 .env 里的账号密码自动登录，失败时再按日志提示处理。</div>
          <div class="ads-form">
            <div class="field">
              <label for="adsSingleDate">单日日期</label>
              <input id="adsSingleDate" type="date" value="${escapeHTML(date)}" />
            </div>
            <div class="field">
              <label for="adsStore">店铺</label>
              <select id="adsStore">
                <option value="all">all</option>
                <option value="22">一店 22</option>
                <option value="23">二店 23</option>
                <option value="24">三店 24</option>
                <option value="25">四店 25</option>
                <option value="26">五店 26</option>
                <option value="27">六店 27</option>
                <option value="28">七店 28</option>
              </select>
            </div>
            <label class="check-field">
              <input id="adsCheckOnly" type="checkbox" />
              只检查，不写入 Notion
            </label>
            <div class="field">
              <label for="adsRangeStart">范围开始</label>
              <input id="adsRangeStart" type="date" value="${escapeHTML(date)}" />
            </div>
            <div class="field">
              <label for="adsRangeEnd">范围结束</label>
              <input id="adsRangeEnd" type="date" value="${escapeHTML(date)}" />
            </div>
          </div>
          <div class="ads-actions">
            <button data-ads-action="yesterday" type="button">同步昨天</button>
            <button data-ads-action="single" type="button">同步单日</button>
            <button data-ads-action="range" type="button">同步日期范围</button>
            <button data-ads-action="relogin" type="button">重新登录并同步</button>
            <div class="right-actions">
              <button data-ads-action="stop" type="button">停止当前运行</button>
              <button data-ads-action="open-log" type="button">打开日志文件夹</button>
            </div>
          </div>
        </div>
      `;
    }

    function adsOptions(action) {
      const singleDate = document.getElementById("adsSingleDate")?.value || defaultYesterday();
      const rangeStart = document.getElementById("adsRangeStart")?.value || singleDate;
      const rangeEnd = document.getElementById("adsRangeEnd")?.value || rangeStart;
      const store = document.getElementById("adsStore")?.value || "all";
      const checkOnly = Boolean(document.getElementById("adsCheckOnly")?.checked);
      if (action === "range") {
        return { date_range: `${rangeStart}~${rangeEnd}`, store, check_only: checkOnly };
      }
      if (action === "relogin") {
        return { date: singleDate, store, check_only: checkOnly, relogin: true };
      }
      return { date: singleDate, store, check_only: checkOnly };
    }

    function setButtonsDisabled(disabled) {
      document.querySelectorAll("button[data-task], #statusBtn").forEach(button => {
        button.disabled = disabled;
      });
      document.body.classList.toggle("is-running", disabled);
    }

    function setRunState(label, active = false) {
      runStateText.textContent = label;
      runDot.classList.toggle("active", active);
    }

    function startRunTimer(task, mode) {
      runningTask = task;
      runningStartedAt = Date.now();
      setButtonsDisabled(true);
      setRunState(`${mode === "execute" ? "执行中" : "预览中"}：${task} | 0 秒`, true);
      writeOutput("");
      appendOutput([
        `正在${mode === "execute" ? "执行" : "预览"}：${task}`,
        "",
        "任务运行中，请不要重复点击执行。下面会实时滚动显示脚本输出。",
        ""
      ].join("\n"));
      runningTimer = window.setInterval(() => {
        const seconds = Math.floor((Date.now() - runningStartedAt) / 1000);
        setRunState(`${mode === "execute" ? "执行中" : "预览中"}：${task} | ${seconds} 秒`, true);
      }, 1000);
    }

    function stopRunTimer(success) {
      if (runningTimer) {
        window.clearInterval(runningTimer);
        runningTimer = null;
      }
      const seconds = runningStartedAt ? Math.floor((Date.now() - runningStartedAt) / 1000) : 0;
      setRunState(`${success ? "已完成" : "已失败"}：${runningTask || "-"} | ${seconds} 秒`, false);
      runningTask = null;
      runningStartedAt = 0;
      setButtonsDisabled(false);
    }

    async function openLogFolder() {
      try {
        await fetchJSON("/api/open-path", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: "D:\\desktop\\codex\\guanggao\\debug" })
        });
        appendOutput("\n[工作台] 已请求打开日志文件夹：D:\\desktop\\codex\\guanggao\\debug\n");
      } catch (error) {
        appendOutput(`\n[工作台] 打开日志文件夹失败：${error.message}\n`);
      }
    }

    function stopCurrentRun() {
      if (!activeRunController || !runningTask) {
        appendOutput("\n[工作台] 当前没有正在运行的任务。\n");
        return;
      }
      activeRunController.abort();
      appendOutput("\n[工作台] 已发送停止请求，正在等待脚本退出。\n");
    }

    async function runTask(task, mode, options = {}) {
      if (runningTask) {
        writeOutput(`已有任务正在运行：${runningTask}\n请等待完成后再执行其他任务。`);
        return;
      }
      startRunTimer(task, mode);
      let success = false;
      activeRunController = new AbortController();
      try {
        const payload = { task, mode, confirm: confirmText.value, options };
        const response = await fetch("/api/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          signal: activeRunController.signal
        });
        if (!response.ok) {
          const text = await response.text();
          throw new Error(text || response.statusText);
        }
        if (!response.body) {
          throw new Error("浏览器不支持流式输出。");
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          appendOutput(decoder.decode(value, { stream: true }));
        }
        appendOutput(decoder.decode());
        const exitMatch = output.textContent.match(/\[工作台\] 任务结束，退出码：(\d+)/);
        success = exitMatch ? exitMatch[1] === "0" : true;
        stopRunTimer(success);
        await loadStatus();
        await loadHistory();
      } catch (error) {
        appendOutput(`\n${error.name === "AbortError" ? "任务已停止。" : error.message}\n`);
        stopRunTimer(false);
      } finally {
        activeRunController = null;
      }
    }

    function selectAgent(agentId) {
      selectedAgent = agentId;
      agentSelect.value = agentId;
      renderAgentList();
      renderSelectedAgent();
    }

    function activateTab(tabName) {
      document.querySelectorAll(".tab").forEach(tab => {
        tab.classList.toggle("active", tab.dataset.tab === tabName);
      });
      document.querySelectorAll(".tab-panel").forEach(panel => {
        panel.hidden = panel.id !== `tab-${tabName}`;
      });
    }

    document.getElementById("refreshBtn").addEventListener("click", async () => {
      await loadStatus();
      await loadHistory();
    });
    document.getElementById("refreshAgentBtn").addEventListener("click", async () => {
      await loadStatus();
      await loadHistory();
    });
    document.getElementById("statusBtn").addEventListener("click", () => runTask("status", "execute"));
    document.getElementById("clearOutputBtn").addEventListener("click", () => writeOutput("等待操作。"));
    agentSearch.addEventListener("input", renderAgentList);
    clearSearchBtn.addEventListener("click", () => {
      agentSearch.value = "";
      renderAgentList();
    });
    agentFilters.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-filter]");
      if (!button) return;
      agentFilter = button.dataset.filter;
      document.querySelectorAll(".filter-chip").forEach(chip => chip.classList.toggle("active", chip === button));
      renderAgentList();
    });
    agentSelect.addEventListener("change", () => selectAgent(agentSelect.value));
    agentList.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-agent]");
      if (!button) return;
      selectAgent(button.dataset.agent);
    });
    document.querySelector(".tabs").addEventListener("click", (event) => {
      const button = event.target.closest("button[data-tab]");
      if (!button) return;
      activateTab(button.dataset.tab);
    });
    taskList.addEventListener("click", (event) => {
      const adsButton = event.target.closest("button[data-ads-action]");
      if (adsButton) {
        const action = adsButton.dataset.adsAction;
        if (action === "stop") return stopCurrentRun();
        if (action === "open-log") return openLogFolder();
        const options = adsOptions(action);
        return runTask("pdd-ads-sync-all", "execute", options);
      }
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
        if path == "/api/open-path":
            self.handle_open_path()
            return
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
        options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
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
        command.extend(self.option_args(task_id, options))
        if mode == "dry-run":
            command.append("--dry-run")
        else:
            command.append("--execute")

        self.stream_command(command)

    def option_args(self, task_id: str, options: dict[str, object]) -> list[str]:
        if task_id not in {"pdd-ads-sync-all", "pdd-ads-catchup"}:
            return []
        args: list[str] = []
        if options.get("date"):
            args.extend(["--date", str(options["date"])])
        if options.get("date_range"):
            args.extend(["--range", str(options["date_range"])])
        if options.get("store"):
            args.extend(["--store", str(options["store"])])
        if options.get("relogin"):
            args.append("--relogin")
        if options.get("check_only"):
            args.append("--check-only")
        return args

    def handle_open_path(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(body or "{}")
        except (ValueError, json.JSONDecodeError):
            self.send_json({"error": "请求 JSON 无效"}, HTTPStatus.BAD_REQUEST)
            return

        requested = Path(str(payload.get("path") or ""))
        allowed = [
            Path(r"D:\desktop\codex\guanggao\debug"),
            WORKBENCH_ROOT / "logs",
        ]
        if requested not in allowed:
            self.send_json({"error": "不允许打开这个路径"}, HTTPStatus.BAD_REQUEST)
            return
        requested.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                subprocess.Popen(["explorer", str(requested)])
            else:
                subprocess.Popen(["xdg-open", str(requested)])
        except OSError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self.send_json({"ok": True, "path": str(requested)})

    def stream_command(self, command: list[str]) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        command = [command[0], "-u", *command[1:]]
        try:
            process = subprocess.Popen(
                command,
                cwd=WORKBENCH_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                env=env,
            )
        except OSError as exc:
            self.write_stream(f"[工作台] 启动失败：{exc}\n")
            return

        assert process.stdout is not None
        try:
            for line in iter(process.stdout.readline, b""):
                self.write_stream(decode_process_output(line))
            exit_code = process.wait()
            self.write_stream(f"\n[工作台] 任务结束，退出码：{exit_code}\n")
        except (BrokenPipeError, ConnectionResetError):
            process.terminate()

    def write_stream(self, text: str) -> None:
        self.wfile.write(text.encode("utf-8", errors="replace"))
        self.wfile.flush()


def decode_process_output(data: bytes) -> str:
    """Decode mixed Windows subprocess output before streaming it to the browser."""
    for encoding in ("utf-8-sig", "utf-8", "gbk", "cp936"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


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

    if agent == "erp_miniapp":
        return collect_erp_miniapp_history(limit)

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


def collect_erp_miniapp_history(limit: int = 20) -> list[HistoryEntry]:
    config = PROJECTS["erp_miniapp"]
    log_dir = config.get("log_dir")
    if not isinstance(log_dir, Path) or not log_dir.exists():
        return []

    files = sorted(
        [path for path in log_dir.glob("*.log") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:limit]

    entries: list[HistoryEntry] = []
    for path in files:
        text = read_text_tail(path, 1200)
        sessions = split_erp_log_sessions(text) if path.name.startswith("run_") else [(path_mtime(path), text)]
        for session_time, session_text in sessions:
            status = classify_history_status("erp_miniapp", session_text)
            summary, details = summarize_erp_miniapp_log(path, session_text, session_time)
            entries.append(
                HistoryEntry(
                    time=session_time or path_mtime(path),
                    status=status,
                    title=erp_miniapp_history_title(path, session_text),
                    summary=summary,
                    source=str(path),
                    details=details,
                )
            )
    return sorted(entries, key=lambda item: item.time, reverse=True)[:limit]


def split_erp_log_sessions(text: str) -> list[tuple[str, str]]:
    from datetime import datetime

    sessions: list[list[str]] = []
    current: list[str] = []
    last_time: datetime | None = None
    current_time = ""

    for line in text.splitlines():
        timestamp = parse_log_timestamp(line)
        if timestamp:
            parsed = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            if current and last_time and (parsed - last_time).total_seconds() > 10 * 60:
                sessions.append(current)
                current = []
            last_time = parsed
            current_time = timestamp
        current.append(line)

    if current:
        sessions.append(current)

    result: list[tuple[str, str]] = []
    for session in sessions:
        timestamps = [parse_log_timestamp(line) for line in session]
        timestamps = [item for item in timestamps if item]
        result.append((timestamps[-1] if timestamps else current_time, "\n".join(session)))
    return result


def parse_log_timestamp(line: str) -> str:
    match = re.match(r"^(20\d{2}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
    return match.group(1) if match else ""


def erp_miniapp_history_title(path: Path, text: str) -> str:
    if "cmd_upload_test" in text or path.name.startswith("upload_"):
        return f"上传测试 / {path.name}"
    if "cmd_form_test" in text or path.name.startswith("form_"):
        return f"表单测试 / {path.name}"
    if "cmd_upload" in text or "流程完成" in text:
        return f"完整上架流程 / {path.name}"
    if "cmd_price_query" in text:
        return f"查价 / {path.name}"
    if "cmd_parse" in text:
        return f"素材解析 / {path.name}"
    return path.name


def summarize_erp_miniapp_log(path: Path, text: str, session_time: str = "") -> tuple[str, list[str]]:
    details: list[str] = []

    title = last_regex_group(text, r"填写链接标题：(.+)")
    if title:
        details.append(f"商品标题：{title}")

    material_root = infer_erp_material_root(text, title)
    if material_root:
        details.append(f"素材目录：{material_root}")

    sku_count = last_regex_group(text, r"填写 SKU 行\s+(\d+)")
    if sku_count:
        details.append(f"SKU 行数：{sku_count}")

    upload_parts = []
    gallery_count = last_regex_group(text, r"开始上传主图：(\d+)\s*个")
    original_count = last_regex_group(text, r"开始上传主图原图：(\d+)\s*个")
    detail_count = last_regex_group(text, r"详情页内容图片上传完成：(\d+)\s*张")
    size_count = last_regex_group(text, r"尺寸图上传完成：(\d+)\s*张")
    video_count = last_regex_group(text, r"开始上传视频：(\d+)\s*个")
    if gallery_count:
        upload_parts.append(f"主图 {gallery_count}")
    if original_count:
        upload_parts.append(f"原图 {original_count}")
    if detail_count:
        upload_parts.append(f"详情图 {detail_count}")
    if size_count:
        upload_parts.append(f"尺寸图 {size_count}")
    if video_count:
        upload_parts.append(f"视频 {video_count}")
    if upload_parts:
        details.append("上传统计：" + " / ".join(upload_parts))

    warning_lines = [line.strip() for line in text.splitlines() if " WARNING " in line or "警告" in line]
    if warning_lines:
        details.append(f"Warning 数量：{len(warning_lines)}")
        details.extend(f"Warning：{line[:220]}" for line in warning_lines[-2:])

    screenshot = latest_erp_screenshot(path, session_time)
    if screenshot:
        details.append(f"最近截图：{screenshot}")

    result = erp_result_summary(text)
    if not result:
        result = summarize_log("erp_miniapp", text)
    return result, details[:8]


def erp_result_summary(text: str) -> str:
    if "流程完成" in text:
        if "已完成上架信息填写，默认停在保存前" in text:
            return "完整流程完成，已填写上架信息，默认停在保存前。"
        return "完整流程完成。"
    if "上传测试已完成" in text:
        return "上传测试完成，未保存商品。"
    if "表单测试完成" in text:
        return "表单测试完成，未上传、未保存。"
    if "ERP 登录完成" in text:
        return "ERP 登录完成，后续步骤见日志。"
    if "视频缺失或未匹配关键字" in text:
        return "素材解析出现 warning：视频缺失或未匹配关键字。"
    if "未找到 ffprobe" in text:
        return "素材解析出现 warning：未找到 ffprobe，跳过视频分辨率读取。"
    return ""


def infer_erp_material_root(text: str, title: str = "") -> str:
    candidates: list[str] = []
    for pattern in (
        r"视频缺失或未匹配关键字：(.+?)\\视频",
        r"未找到 ffprobe，跳过视频分辨率读取：(.+?)\\视频",
    ):
        for match in re.findall(pattern, text):
            candidates.append(str(match).strip())
    if not candidates:
        return ""
    if title:
        title_matches = [item for item in candidates if title.lower() in item.lower()]
        if title_matches:
            return title_matches[-1]
    non_temp = [item for item in candidates if "AppData\\Local\\Temp" not in item]
    if non_temp:
        unique = list(dict.fromkeys(non_temp))
        return "；".join(unique[-3:])
    return candidates[-1]


def last_regex_group(text: str, pattern: str) -> str:
    matches = re.findall(pattern, text)
    if not matches:
        return ""
    value = matches[-1]
    if isinstance(value, tuple):
        value = value[0]
    return str(value).strip()


def latest_erp_screenshot(log_path: Path, session_time: str = "") -> str:
    from datetime import datetime

    screenshot_dir = log_path.parent / "screenshots"
    if not screenshot_dir.exists():
        return ""
    if session_time:
        session_ts = datetime.strptime(session_time, "%Y-%m-%d %H:%M:%S").timestamp()
        lower_bound = session_ts - 20 * 60
        upper_bound = session_ts + 10 * 60
    else:
        lower_bound = log_path.stat().st_mtime - 4 * 60 * 60
        upper_bound = log_path.stat().st_mtime + 10 * 60
    screenshots = [
        path
        for path in screenshot_dir.glob("*.png")
        if lower_bound <= path.stat().st_mtime <= upper_bound
    ]
    if not screenshots and not session_time:
        screenshots = list(screenshot_dir.glob("*.png"))
    if not screenshots:
        return ""
    return str(max(screenshots, key=lambda item: item.stat().st_mtime))


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
