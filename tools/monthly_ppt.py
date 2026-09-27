"""Persistent browser workflow for the monthly PPT builder (localhost only)."""
from __future__ import annotations

import json
import mimetypes
import os
import re
import shutil
import subprocess
import threading
import uuid
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from workbench_log import append_record, now_local

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"D:\desktop\codex\美工月会ppt\设计师型号月报助手")
DATA = ROOT / "data" / "monthly-ppt"
STATE_FILE = DATA / "state.json"
LOCK = threading.RLock()
IMAGES = {".png", ".jpg", ".jpeg", ".webp"}
MAX_UPLOAD = 100 * 1024 * 1024
_state = None


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def save():
    DATA.mkdir(parents=True, exist_ok=True)
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(_state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(STATE_FILE)


def state():
    global _state
    with LOCK:
        if _state is not None:
            return _state
        _state = read_json(STATE_FILE, None)
        if not isinstance(_state, dict):
            old = read_json(SOURCE / ".build" / "gui-settings.json", {})
            period = str(old.get("Period") or now_local().strftime("%Y年%m月"))
            match = re.fullmatch(r"(\d{4})年(\d{1,2})月", period)
            month = f"{match[1]}-{int(match[2]):02d}" if match else now_local().strftime("%Y-%m")
            _state = {"settings": {
                "month": month,
                "designer_file": old.get("DesignerFile", str(SOURCE / "型号归属表模板.xlsx")),
                "sales_file": old.get("SalesFile", ""),
                "image_root": old.get("ImageRoot", str(SOURCE.parent / "work" / "designer_sales_2026-08" / "assets")),
                "output_dir": str(Path(old.get("OutputFile") or str(SOURCE.parent / "output" / "report.pptx")).parent),
                "designer_sheet": "Sheet1", "sales_sheet": "Worksheet", "refresh_thumbnails": False,
            }, "works": [], "jobs": []}
            works_root = Path(old.get("WorksRoot") or str(SOURCE / ".build" / "clipboard-portfolio"))
            if works_root.is_dir():
                for path in sorted(works_root.rglob("*")):
                    parts = path.relative_to(works_root).parts
                    if path.is_file() and path.suffix.lower() in IMAGES and len(parts) >= 3 and parts[0] in {"美工", "设计师"}:
                        _state["works"].append({"id": uuid.uuid4().hex, "role": parts[0], "name": parts[1], "filename": path.name, "path": str(path), "active": True})
        # A service restart must not leave an eternal running indicator.
        for job in _state["jobs"]:
            if job["status"] in {"queued", "running"}:
                job.update(status="interrupted", message="工作台服务已重启，请检查日志后重新生成。", finished_at=now_local().isoformat())
        save()
        return _state


def public_job(job):
    result = {k: v for k, v in job.items() if k not in {"command", "settings", "works"}}
    base = f"/api/monthly-ppt/jobs/{job['id']}"
    result["download_url"] = base + "/download" if job["status"] == "success" else None
    preview = Path(job["build_dir"]) / "meeting-preview"
    result["previews"] = [base + "/preview/" + p.name for p in sorted(preview.glob("slide-*.png"))] if preview.is_dir() else []
    return result


def snapshot():
    with LOCK:
        current = state()
        return {"settings": dict(current["settings"]),
                "works": [{k: v for k, v in item.items() if k != "path"} for item in current["works"]],
                "jobs": [public_job(job) for job in reversed(current["jobs"])],
                "template_url": "/api/monthly-ppt/template"}


def component(value):
    value = str(value).strip()
    if not value or len(value) > 100 or re.search(r'[<>:"/\\|?*\x00-\x1f]', value) or value in {".", ".."} or value.endswith((".", " ")):
        raise ValueError("姓名或文件名含不允许的字符。")
    if re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", value):
        raise ValueError("文件名是系统保留名称。")
    return value


def change_settings(values):
    settings = state()["settings"]
    for key in settings:
        if key in values:
            settings[key] = bool(values[key]) if key == "refresh_thumbnails" else str(values[key]).strip()
    save()


def upload(kind, filename, data, options):
    with LOCK:
        current = state()
        filename = component(filename)
        ext = Path(filename).suffix.lower()
        token = uuid.uuid4().hex
        if kind in {"designer", "sales"}:
            if ext not in {".xlsx", ".xlsm"}:
                raise ValueError("请上传 .xlsx 或 .xlsm 文件。")
            import io
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as workbook:
                    if "xl/workbook.xml" not in workbook.namelist():
                        raise ValueError("不是有效的 Excel 工作簿。")
            except zipfile.BadZipFile as exc:
                raise ValueError("Excel 文件损坏。") from exc
            path = DATA / "uploads" / token / filename
            settings_key = kind + "_file"
        elif kind == "work":
            if ext not in IMAGES:
                raise ValueError("作品仅支持 PNG、JPG、JPEG、WEBP。")
            role = options.get("role", "")
            if role not in {"美工", "设计师"}:
                raise ValueError("请选择美工或设计师。")
            name = component(options.get("name", ""))
            path = DATA / "uploads" / token / filename
            settings_key = None
        elif kind == "model":
            if ext not in IMAGES:
                raise ValueError("型号图片仅支持 PNG、JPG、JPEG、WEBP。")
            batch = str(options.get("batch", ""))
            if not re.fullmatch(r"[a-f0-9-]{32,36}", batch):
                raise ValueError("无效的文件夹上传标识。")
            parts = str(options.get("relative", "")).replace("\\", "/").split("/")
            if len(parts) != 2:
                raise ValueError("型号图片目录应为：图片根目录/设计师/型号.png。")
            parts = [component(part) for part in parts]
            path = DATA / "models" / batch / parts[0] / filename
            # Activate a folder only after the browser completes the whole batch.
            settings_key = None
        else:
            raise ValueError("不支持的上传类型。")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        if kind == "work":
            current["works"].append({"id": token, "role": role, "name": name, "filename": filename, "path": str(path), "active": True})
        elif settings_key:
            current["settings"][settings_key] = str(path)
        save()
        return {"ok": True, "id": token, "path": str(path), "image_root": str(path.parents[1]) if kind == "model" else None}


def validate(settings, works):
    problems = []
    if not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", settings["month"]):
        problems.append("请选择有效的报告月份。")
    for key, label in (("designer_file", "型号归属表"), ("sales_file", "当月交易明细")):
        path = Path(settings[key])
        if not path.is_file() or path.suffix.lower() not in {".xlsx", ".xlsm"}:
            problems.append(f"请上传或选择有效的{label}。")
    if not Path(settings["image_root"]).is_dir():
        problems.append("请选择有效的型号图片文件夹。")
    if not works:
        problems.append("请先录入至少一张作品图片。")
    if any(not Path(item["path"]).is_file() for item in works):
        problems.append("部分作品原文件不存在，请移除后重新上传。")
    if not settings["output_dir"] or not Path(settings["output_dir"]).is_absolute():
        problems.append("PPT 保存目录须为本机绝对路径。")
    if not (SOURCE / "run_monthly_meeting.ps1").is_file():
        problems.append("找不到 PPT 生成程序。")
    if problems:
        raise ValueError("\n".join(problems))


def start_job(settings):
    with LOCK:
        current = state()
        if any(j["status"] in {"running", "queued"} for j in current["jobs"]):
            raise ValueError("已有月报正在生成，请等待完成后再试。")
        change_settings(settings)
        settings = dict(current["settings"])
        works = [dict(item) for item in current["works"] if item.get("active", True)]
        validate(settings, works)
        stamp = now_local()
        token = uuid.uuid4().hex
        period = f"{settings['month'][:4]}年{int(settings['month'][5:])}月"
        job_dir = DATA / "jobs" / token
        job_dir.mkdir(parents=True)
        output = Path(settings["output_dir"]) / f"美工月会_{period}_{stamp:%Y%m%d_%H%M%S}_{token[:6]}_完整可编辑版.pptx"
        job = {"id": token, "status": "queued", "month": settings["month"], "started_at": stamp.isoformat(),
               "finished_at": None, "message": "正在准备作品和数据…", "progress": 2,
               "output": str(output), "build_dir": str(job_dir / "build"), "log_path": str(job_dir / "generation.log"),
               "settings": settings, "works": works, "work_count": len(works), "slide_count": 0}
        current["jobs"].append(job)
        save()
        threading.Thread(target=run_job, args=(job,), daemon=True).start()
        return public_job(job)


def run_job(job):
    started = now_local()
    settings = job["settings"]
    job_dir = Path(job["build_dir"]).parent
    works_root = job_dir / "works"
    result_code = 1
    try:
        with LOCK:
            job.update(status="running", progress=5)
            save()
        # Snapshot selected works so editing the browser draft cannot change this run.
        for index, item in enumerate(job["works"]):
            folder = works_root / component(item["role"]) / component(item["name"])
            folder.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item["path"], folder / f"{index:04d}_{component(item['filename'])}")
        command = [str(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"),
                   "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SOURCE / "run_monthly_meeting.ps1"),
                   "-DesignerFile", settings["designer_file"], "-SalesFile", settings["sales_file"],
                   "-WorksRoot", str(works_root), "-ImageRoot", settings["image_root"],
                   "-OutputFile", job["output"], "-Period", f"{settings['month'][:4]}年{int(settings['month'][5:])}月",
                   "-DesignerSheet", settings["designer_sheet"], "-SalesSheet", settings["sales_sheet"],
                   "-BuildDirectory", job["build_dir"]]
        if settings["refresh_thumbnails"]:
            command.append("-RefreshThumbnails")
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
        with Path(job["log_path"]).open("w", encoding="utf-8", buffering=1) as log:
            proc = subprocess.Popen(command, cwd=SOURCE, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, env=env)
            for raw in iter(proc.stdout.readline, b""):
                line = raw.decode("utf-8", errors="replace")
                log.write(line)
                for marker, progress, message in (("[1/3]", 15, "正在处理型号图片"), ("[2/3]", 35, "正在汇总销售额与净利润"), ("[3/3]", 60, "正在排版并生成逐页预览")):
                    if marker in line:
                        with LOCK:
                            job.update(progress=progress, message=message)
                            save()
            result_code = proc.wait()
        if result_code != 0:
            raise RuntimeError("生成失败，请查看下方日志，修正资料后重新生成。")
        with zipfile.ZipFile(job["output"]) as deck:
            if deck.testzip() is not None:
                raise RuntimeError("生成的 PPT 文件校验失败。")
            slides = [n for n in deck.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
            if not slides:
                raise RuntimeError("PPT 没有可用页面。")
        with LOCK:
            job.update(status="success", progress=100, slide_count=len(slides), message=f"生成完成，共 {len(slides)} 页，可预览或下载。")
    except Exception as exc:
        with LOCK:
            job.update(status="failed", message=str(exc))
        with Path(job["log_path"]).open("a", encoding="utf-8") as log:
            log.write(f"\n[工作台] {exc}\n")
    finally:
        finished = now_local()
        with LOCK:
            job["finished_at"] = finished.isoformat()
            save()
        append_record({"project": "designer-monthly-ppt", "script": "designer-monthly-ppt-web", "status": job["status"],
                       "exit_code": 0 if job["status"] == "success" else (result_code or 1),
                       "started_at": started.isoformat(), "finished_at": finished.isoformat(),
                       "duration_seconds": round((finished - started).total_seconds(), 2),
                       "message": job["message"], "workdir": str(SOURCE), "output": job["output"], "job_id": job["id"]})


def find_job(token):
    return next((j for j in state()["jobs"] if j["id"] == token), None)


def send_file(handler, path, download=False):
    if not path.is_file():
        handler.send_json({"error": "文件不存在。"}, 404)
        return
    handler.send_response(200)
    handler.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
    handler.send_header("Content-Length", str(path.stat().st_size))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    if download:
        handler.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + quote(path.name))
    handler.end_headers()
    with path.open("rb") as file:
        shutil.copyfileobj(file, handler.wfile)


def handle(handler):
    parsed = urlparse(handler.path)
    path = parsed.path
    if path == "/monthly-ppt":
        if handler.command != "GET":
            handler.send_json({"error": "method not allowed"}, 405)
        else:
            handler.send_html((ROOT / "tools" / "monthly_ppt.html").read_text(encoding="utf-8"))
        return True
    if not path.startswith("/api/monthly-ppt/"):
        return False
    try:
        # Mutations are same-origin JSON or binary uploads, never cross-site forms.
        if handler.command == "POST":
            origin = handler.headers.get("Origin")
            if origin and origin != "http://" + handler.headers.get("Host", ""):
                handler.send_json({"error": "不允许跨站请求。"}, 403)
                return True
            content_type = handler.headers.get("Content-Type", "").split(";")[0]
            if content_type not in {"application/json", "application/octet-stream"}:
                raise ValueError("请求格式不正确。")
            length = int(handler.headers.get("Content-Length", "0"))
            limit = MAX_UPLOAD if path.endswith("/upload") else 1024 * 1024
            if length <= 0 or length > limit:
                raise ValueError("文件过大或内容为空，单文件上限 100 MB。")
            raw = handler.rfile.read(length)
            if len(raw) != length:
                raise ValueError("文件上传不完整，请重试。")
            if path.endswith("/upload"):
                query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
                handler.send_json(upload(query.get("kind"), query.get("filename", ""), raw, query))
                return True
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("请求内容须为对象。")
            with LOCK:
                if path.endswith("/settings"):
                    change_settings(payload)
                    handler.send_json({"ok": True})
                elif path.endswith("/works"):
                    current = state()
                    ids = payload.get("ids", [])
                    for item in current["works"]:
                        if item["id"] in ids:
                            item["active"] = bool(payload.get("active", True))
                    save()
                    handler.send_json({"ok": True})
                elif path.endswith("/generate"):
                    handler.send_json(start_job(payload), 202)
                else:
                    handler.send_json({"error": "not found"}, 404)
            return True
        if path == "/api/monthly-ppt/state":
            handler.send_json(snapshot())
        elif path == "/api/monthly-ppt/template":
            send_file(handler, SOURCE / "型号归属表模板.xlsx", True)
        elif re.fullmatch(r"/api/monthly-ppt/works/[a-f0-9]{32}", path):
            token = path.rsplit("/", 1)[1]
            item = next((i for i in state()["works"] if i["id"] == token), None)
            if item:
                send_file(handler, Path(item["path"]))
            else:
                handler.send_json({"error": "作品不存在。"}, 404)
        else:
            match = re.fullmatch(r"/api/monthly-ppt/jobs/([a-f0-9]{32})(?:/(download|log|preview/slide-\d+\.png))?", path)
            job = find_job(match[1]) if match else None
            if not job:
                handler.send_json({"error": "任务不存在。"}, 404)
            elif match[2] == "download":
                if job["status"] != "success":
                    raise ValueError("PPT 尚未生成成功。")
                send_file(handler, Path(job["output"]), True)
            elif match[2] == "log":
                log = Path(job["log_path"])
                handler.send_json({"text": log.read_text(encoding="utf-8", errors="replace")[-60000:] if log.exists() else "正在准备…"})
            elif match[2] and match[2].startswith("preview/"):
                send_file(handler, Path(job["build_dir"]) / "meeting-preview" / match[2].split("/")[1])
            else:
                handler.send_json(public_job(job))
    except (ValueError, OSError) as exc:
        handler.send_json({"error": str(exc)}, 400)
    return True
