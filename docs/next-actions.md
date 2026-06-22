# 下一步执行清单

## 优先级

第一阶段先把现有四个项目接入工作台，而不是新造数据源。

原因：

- 已有广告同步项目已经完成 `ERP 广告数据 -> Notion`。
- 已有周报项目已经完成 `Notion 7 店广告数据库 -> Notion 周报`。
- 已有两个上架项目分别面向拼多多后台和 ERP 自研后台，不能混成同一个项目。

## 第 1 步：接入现有项目登记

已读取并登记：

- `D:\desktop\codex\guanggao`
- `D:\desktop\codex\notion拼多多周报\pdd_weekly_report`
- `D:\desktop\codex\拼多多自动上架`
- `D:\desktop\codex\小程序自动上架\erp_auto_upload`

产出：

- `docs/existing-projects-audit.md`
- `registry/external-projects.yml`

## 第 2 步：统一状态面板

下一步应该做工作台状态面板，读取这些现有日志：

| 项目 | 状态来源 |
| --- | --- |
| 拼多多广告同步 | `D:\desktop\codex\guanggao\debug` |
| 拼多多周报 | `D:\desktop\codex\notion拼多多周报\pdd_weekly_report\logs` |
| 拼多多自动上架 | `D:\desktop\codex\拼多多自动上架\.tmp_tool\saved_draft_history.json` |
| 小程序 ERP 自动上架 | `D:\desktop\codex\小程序自动上架\erp_auto_upload\logs` |

产出：

- 工作台命令：`python tools/workbench_external_status.py`
- 显示每个项目最近一次成功/失败/警告/未运行、运行时间、日志文件和建议

当前已完成只读状态面板。它不会执行任何同步或上架，只读取日志和草稿历史。

## 第 3 步：统一启动入口

给工作台增加启动命令，不直接改四个项目内部逻辑：

```powershell
python tools/workbench_run.py pdd-ads-yesterday
python tools/workbench_run.py pdd-weekly-report
python tools/workbench_run.py pdd-publisher
python tools/workbench_run.py erp-miniapp-upload
```

要求：

- 调用现有项目命令。
- 每次运行写入工作台 `logs/script-runs.jsonl`。
- 不读取或提交真实 `.env`、登录态、`config.yaml`。

## 第 4 步：再考虑迁移代码

在工作台状态和启动入口稳定后，再决定是否把四个项目代码迁入 `projects/`。迁移前必须：

- 保留原项目 Git 历史或明确重新建档。
- 迁移 `.env.example`，不迁移 `.env`。
- 迁移日志规则，不迁移本地运行日志。
- 更新对应 README、runbook、任务计划路径。
