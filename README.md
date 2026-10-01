# 个人工作台

这个目录用来集中管理所有自动化、数据同步、报表、上架和后续项目。工作台先读取并登记现有项目，再决定是否迁移、封装或新增脚本，避免凭空假设数据源。

## 当前项目

| 项目 | 目录 | 状态 | 说明 |
| --- | --- | --- | --- |
| 拼多多广告数据同步到 Notion | `D:\desktop\codex\guanggao` | 已存在 | 从 ERP 抓取拼多多一到七店广告数据，写入 Notion 每日广告数据库。 |
| Notion 拼多多周报生成器 | `D:\desktop\codex\notion拼多多周报\pdd_weekly_report` | 已存在 | 汇总店铺概况、消费者体验、7 店广告与盈亏，生成完整 Notion 周报页面。 |
| 拼多多自动上架工具 | `D:\desktop\codex\拼多多自动上架` | 已存在 | 使用 ERP 优质价和图片空间素材生成拼多多上架包，并辅助后台保存草稿。 |
| 小程序 ERP 自动上架商品工具 | `D:\desktop\codex\小程序自动上架\erp_auto_upload` | 已存在 | 使用本地素材目录在公司自研 ERP 后台新建商品，默认停在保存前。 |
| 美工月报 PPT | `D:\desktop\codex\美工月会ppt\设计师型号月报助手` | 已接入 | 在工作台网页录入作品和销售数据、生成、预览与下载可编辑 PPT。 |

## 目录说明

```text
.
├── docs/                 # 工作台规范、自动化标准、项目模板
├── registry/             # 项目登记表和后续可机器读取的配置
├── projects/             # 预留给后续迁入工作台的项目
└── AGENTS.md             # Codex/协作规则
```

已读取的现有项目登记见：

```text
registry/external-projects.yml
docs/existing-projects-audit.md
```

每个项目目录建议保持一致：

```text
project-name/
├── README.md             # 项目入口说明
├── automation/           # 脚本、定时任务、同步任务
├── config/               # 示例配置，真实密钥不要提交
├── data/                 # 本地样例数据、导入导出文件
└── docs/                 # 运行手册、Notion/外部文档同步说明
```

## 新增项目流程

1. 在 `projects/` 下创建项目目录。
2. 复制 `docs/project-template.md` 的结构。
3. 在 `registry/projects.yml` 登记项目名称、负责人、状态、入口和文档。
4. 如果新增或修改自动化脚本，同步更新该项目 `README.md` 和 `docs/runbook.md`。
5. 涉及密钥时，只提交 `.env.example`，真实值放本地 `.env` 或系统环境变量。

## 下一步

优先把现有四个项目接入工作台状态面板和统一启动入口。广告同步与周报的真实链路是：`ERP 广告数据 -> Notion 7 店每日广告数据库 -> Notion 拼多多周报`。执行清单见 `docs/next-actions.md`。

## 脚本运行状态

工作台脚本统一记录运行历史到：

```text
logs/script-runs.jsonl
```

运行已接入的脚本时，会在终端显示：

```text
[运行中] script.py | 项目：project-id | 开始：YYYY-MM-DD HH:mm:ss Asia/Shanghai
[成功] script.py | 完成：YYYY-MM-DD HH:mm:ss Asia/Shanghai | 耗时：1.23s
```

查看最近运行状态：

```powershell
python tools/workbench_status.py
```

查看已接入外部项目状态：

```powershell
python tools/workbench_external_status.py
```

查看和启动已登记任务：

```powershell
python tools\workbench_run.py --list
python tools\workbench_run.py status
python tools\workbench_run.py pdd-weekly-report --dry-run
python tools\workbench_run.py pdd-weekly-report --execute
```

工作台启动拼多多周报时，会自动计算截止日为昨天、开始日为截止日所在月份的 1 日，并使用项目虚拟环境显式传给主脚本。例如 2026-08-08 启动时执行 `.\.venv\Scripts\python.exe main.py --start-date 2026-08-01 --end-date 2026-08-07`，避免盈亏业务线汇总读取跨月区间。

除 `status` 外，真实启动都必须加 `--execute`。

启动本地网页工作台：

```powershell
python tools\workbench_app.py
```

默认地址：

```text
http://127.0.0.1:8787/
```

安装 Windows 登录后自动启动：

```powershell
powershell -ExecutionPolicy Bypass -File tools\workbench_autostart.ps1 -Mode Install
```

查看自动启动状态：

```powershell
powershell -ExecutionPolicy Bypass -File tools\workbench_autostart.ps1 -Mode Status
```

卸载自动启动：

```powershell
powershell -ExecutionPolicy Bypass -File tools\workbench_autostart.ps1 -Mode Uninstall
```

自动启动使用 Windows 计划任务 `CodexWorkbenchApp`，触发条件是当前用户登录 Windows，并每 5 分钟守护检查一次。计划任务通过 `tools\workbench_autostart.vbs` 静默调用 `tools\workbench_autostart.ps1 -Mode Ensure`，避免 Windows Terminal 弹出黑色窗口；如果 `127.0.0.1:8787` 已经有工作台服务在监听，就直接退出；如果没有监听，就后台启动 `tools\workbench_app.py`。计划任务自身日志写入 `logs\workbench_autostart.log`，网页服务输出写入 `logs\workbench_app_stdout.log` 和 `logs\workbench_app_stderr.log`。

网页现在采用 Agent 详情工作区布局：左侧是 Agent 列表和搜索，右侧展示当前选中 Agent 的状态摘要、运行、历史、日志和文件信息。运行页只显示当前 Agent 相关任务，执行前可先预览命令；除 `status`、客户端登录与打开系统外，真实执行都需要输入 `EXECUTE`。任务运行中会锁定执行按钮、显示已运行秒数，并像桌面脚本一样实时滚动显示 stdout/stderr 输出。运行输出会自动兼容 UTF-8 和 Windows GBK/cp936，避免中文日志在网页里乱码。

网页里的 `Agent 历史记录` 下拉框可以查看：

- 工作台运行记录
- 拼多多广告同步历史，会合并工作台手动执行记录和广告项目 debug 日志
- 拼多多周报历史
- 拼多多自动上架草稿历史，会按保存草稿记录逐条显示商品标题、店铺名、店铺 ID、商品 ID、记录键和商品链接
- 小程序 ERP 自动上架日志历史，会从日志里提取商品标题、素材目录、SKU 行数、上传统计、warning 和最近截图路径；状态卡按最后一次运行片段判断，避免同一天旧失败覆盖后续成功

历史记录按页加载，每页 20 条。记录超过一页时可用 `上一页` / `下一页` 翻看更早历史，避免一次性展开过多记录；拼多多自动上架的草稿历史会一直读取 `saved_draft_history.json` 里的全部记录，而不是只显示最近 5 条。

查看某个已接入工作台运行记录的脚本状态：

```powershell
python tools/workbench_status.py --script script_name.py
```

已登记现有脚本见 `registry/scripts.yml`。

## 美工月报 PPT

打开 `http://127.0.0.1:8787/`，左侧选择“美工月报 PPT”，在“运行”页直接完成：

1. 选择报告月份，按身份和姓名粘贴、拖入或上传作品；也可导入按“美工或设计师/姓名/图片”分类的作品根文件夹。
2. 上传型号归属表和当月交易明细（`.xlsx/.xlsm`），选择型号图片根文件夹，或沿用网页中显示的已有资料。
3. 确认保存目录和工作表名称，点击“生成完整月报 PPT”。这里无需输入 `EXECUTE`，不会打开桌面脚本窗口。
4. 网页显示阶段进度和日志，完成后可以逐页预览、放大和下载 PPT。历史月报可再次预览和下载。

首次使用带入原助手的设置及作品；后续网页资料独立保存在 `data/monthly-ppt/state.json`。作品移除只改变选中状态，可恢复，不删除原图片。每次任务快照所选作品，使用独立构建目录，输出文件名带时间和任务标识，避免覆盖原月报。默认输出目录为 `D:\desktop\codex\美工月会ppt\output`，可在网页修改。

后台复用 `run_monthly_meeting.ps1` 并传入 `-BuildDirectory`，保留原有排版和计算逻辑。最终一份可编辑 PPT 包含前半部分作品展示和后半部分型号销售利润。单文件上传上限 100 MB。生成只在本机执行，不新增定时任务或凭据，也不写外部系统。刷新网页后可恢复进度，同一时间只允许一个月报生成任务。

状态与历史现在展示真实的生成结果；PPT 经过 ZIP 完整性和页面检查后才提供下载。任务日志及预览存放在 `data/monthly-ppt/jobs/<任务ID>/`，统一记录写到 `logs/script-runs.jsonl`，script 为 `designer-monthly-ppt-web`。资料和生成文件已从 Git 排除。服务中断的任务标为“已中断”，重新生成即可；其他错误可展开生成日志，修正输入后重试。旧桌面启动任务已从工作台移除。

网页和后端分别为 `tools/monthly_ppt.html`、`tools/monthly_ppt.py`；后端通过 `workbench_app.py` 提供同源接口。相关测试：`python -m unittest discover -s tests -v`。

## ERP 客户端登录（2026-09-30）

ERP 统一复用 **Leedis 桌面客户端**。先在客户端完成登录，任务通过客户端“打开系统”取得专用 ERP Chrome 的网页登录态；不再读取 ERP_USERNAME、ERP_PHONE、ERP_PASSWORD，也不回退账号密码或脚本扫码登录。客户端凭据仍由客户端和 Windows 凭据管理器保管。任务只在内存使用 ldswj.net 的网站 Cookie，不再读取旧 `.auth/session.json`、`.erp_session.bin` 或 `states/erp.json`。

本机已配置客户端。换电脑时安装 LeedisClient.exe、Google Chrome 和项目 requirements.txt，然后运行工作台仓库的安装命令（替换成实际客户端路径）：

```powershell
powershell -ExecutionPolicy Bypass -File tools/setup_erp_client.ps1 -ClientExe "D:\desktop\客户端登录\Leedis-Windows\LeedisClient.exe"
```

配置保存在 `%LOCALAPPDATA%/LeedisDesktop/workbench-config.json`，只记录客户端路径；也可用 `ERP_CLIENT_EXE` 覆盖路径。安装脚本生成客户端需要的 `%USERPROFILE%/Desktop/ERP Chrome.lnk`，使用独立浏览器目录 `%LOCALAPPDATA%/LeedisDesktop/erp-chrome` 和本机 9222 端口。已有配置和快捷方式先备份再更新。网站登录态属于敏感本机数据，不提交到 GitHub。

客户端尚未运行时自动启动并尝试恢复已有登录；未登录、客户端忙、9222 不可用或登录过期无法恢复时，任务失败并显示提示。请在客户端登录后重试原任务；不会自动尝试账号密码，不会关闭客户端或 ERP Chrome。自动任务仍需在已登录 Windows 的同一用户会话下执行。切换客户端账号后，应结束当前任务并重新运行。

```powershell
python tools/erp_desktop_auth.py login  # 客户端登录，需要授权时由本人完成
python tools/erp_desktop_auth.py check  # 打开系统并只读检查网页会话
```

公共接入代码维护源为工作台 `tools/erp_desktop_auth.py`；各业务仓库包含同版副本，可独立运行。更新公共模块时同步四个业务副本。升级无需移植旧网页 Cookie，旧密码配置可自行删除，程序已不再使用。

## 凭据约定

- 不提交真实账号、密码、cookie、token、API key。
- 外部项目只登记 `.env.example` 或配置模板，不读取、不提交真实 `.env`。
- 通用凭据命名参考 `docs/automation-standards.md`。

### ERP 浏览器接入重试（2026-10-01）

公共登录模块与工作台维护源保持一致。客户端打开系统成功后，ERP Chrome 连接最多尝试 3 次（每次最多 10 秒）；网页会话在 45 秒等待期内重试验证，单次请求最多 10 秒，在途请求可能使总等待略超 45 秒。短暂超时或连接重置会重试，不重复调用客户端登录。最终错误区分本机 9222 连接失败和网页会话验证失败，记录异常类型或 HTTP 状态，不输出凭据。请先确认 ERP 网页正常打开；显示登录页时在客户端完成登录后重跑原任务。
