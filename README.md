# 个人工作台

这个目录用来集中管理所有自动化、数据同步、报表、上架和后续项目。工作台先读取并登记现有项目，再决定是否迁移、封装或新增脚本，避免凭空假设数据源。

## 当前项目

| 项目 | 目录 | 状态 | 说明 |
| --- | --- | --- | --- |
| 拼多多广告数据同步到 Notion | `D:\desktop\codex\guanggao` | 已存在 | 从 ERP 抓取拼多多一到七店广告数据，写入 Notion 每日广告数据库。 |
| Notion 拼多多周报生成器 | `D:\desktop\codex\notion拼多多周报\pdd_weekly_report` | 已存在 | 从 Notion 7 个店铺广告数据库读取上周数据，生成 Notion 周报页面。 |
| 拼多多自动上架工具 | `D:\desktop\codex\拼多多自动上架` | 已存在 | 使用 ERP 优质价和图片空间素材生成拼多多上架包，并辅助后台保存草稿。 |
| 小程序 ERP 自动上架商品工具 | `D:\desktop\codex\小程序自动上架\erp_auto_upload` | 已存在 | 使用本地素材目录在公司自研 ERP 后台新建商品，默认停在保存前。 |

## 目录说明

```text
.
├── docs/                 # 工作台规范、自动化标准、项目模板
├── registry/             # 项目登记表和后续可机器读取的配置
├── projects/             # 预留给后续迁入工作台的项目
└── AGENTS.md             # Codex/协作规则
```

已读取的四个现有项目登记见：

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

查看四个现有外部项目状态：

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

网页现在采用 Agent 详情工作区布局：左侧是 Agent 列表和搜索，右侧展示当前选中 Agent 的状态摘要、运行、历史、日志和文件信息。运行页只显示当前 Agent 相关任务，执行前可先预览命令；除 `status` 外真实执行都需要输入 `EXECUTE`。任务运行中会锁定执行按钮、显示已运行秒数，并像桌面脚本一样实时滚动显示 stdout/stderr 输出。运行输出会自动兼容 UTF-8 和 Windows GBK/cp936，避免中文日志在网页里乱码。

网页里的 `Agent 历史记录` 下拉框可以查看：

- 工作台运行记录
- 拼多多广告同步历史，会合并工作台手动执行记录和广告项目 debug 日志
- 拼多多周报历史
- 拼多多自动上架草稿历史
- 小程序 ERP 自动上架日志历史，会从日志里提取商品标题、素材目录、SKU 行数、上传统计、warning 和最近截图路径；状态卡按最后一次运行片段判断，避免同一天旧失败覆盖后续成功

历史记录按页加载，每页 20 条。记录超过一页时可用 `上一页` / `下一页` 翻看更早历史，避免一次性展开过多记录。

查看某个已接入工作台运行记录的脚本状态：

```powershell
python tools/workbench_status.py --script script_name.py
```

已登记现有脚本见 `registry/scripts.yml`。

## 凭据约定

- 不提交真实账号、密码、cookie、token、API key。
- 外部项目只登记 `.env.example` 或配置模板，不读取、不提交真实 `.env`。
- 通用凭据命名参考 `docs/automation-standards.md`。
