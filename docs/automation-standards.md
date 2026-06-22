# 自动化标准

本文件定义工作台内所有脚本、同步任务、定时任务和上架任务的统一约定。

## 项目边界

- 每个自动化必须归属于 `projects/<project-name>/`。
- 项目入口说明写在项目自己的 `README.md`。
- 运行、排障、恢复步骤写在项目自己的 `docs/runbook.md`。
- 脚本或任务配置放在项目自己的 `automation/` 目录。

## 自动化文档同步

修改以下内容后，必须同步更新对应文档：

- 脚本入口、命令参数、运行方式。
- 定时任务、计划任务、GitHub Actions 或其他调度配置。
- 输入输出路径、Notion 数据库、平台接口、字段映射。
- 重试、失败处理、恢复流程。
- 新增或变更环境变量。

优先更新：

- 项目 `README.md`。
- 项目 `docs/runbook.md`。
- 如存在外部 Notion/README/GitHub 文档，也要同步更新。

## 运行记录和状态

所有可重复运行的脚本都应接入工作台运行记录：

- 运行中、成功、失败状态必须在终端可见。
- 每次运行必须写入 `logs/script-runs.jsonl`。
- 日志至少包含项目、脚本、开始时间、结束时间、状态、耗时、命令和说明。
- 运行日志是本地运行产物，不提交到 Git。

Python 脚本优先复用 `tools/workbench_log.py`：

```python
from workbench_log import run_logged

if __name__ == "__main__":
    raise SystemExit(
        run_logged(
            project="project-id",
            script="script_name.py",
            func=main,
        )
    )
```

查看最近状态：

```powershell
python tools/workbench_status.py
```

## 命名约定

- 项目目录使用小写英文和连字符，例如 `pdd-auto-listing`。
- 自动化脚本使用动作开头，例如 `sync-*`、`import-*`、`export-*`、`report-*`、`publish-*`。
- 本地样例数据放 `data/samples/`。
- 运行产物放 `data/output/`，并按需加入 `.gitignore`。

## 环境变量

建议使用以下通用命名：

```text
NOTION_TOKEN=
NOTION_DATABASE_ID=
PDD_CLIENT_ID=
PDD_CLIENT_SECRET=
PDD_ACCESS_TOKEN=
ERP_BASE_URL=
ERP_USERNAME=
ERP_PASSWORD=
ADS_ACCOUNT_ID=
ADS_ACCESS_TOKEN=
```

真实值只能写入本地 `.env` 或系统环境变量，提交仓库的只能是 `.env.example`。

## 上线前检查

- 是否有 dry-run 或只读模式。
- 是否能记录成功、失败和跳过的数量。
- 是否明确失败后是否重试。
- 是否不会重复创建商品、周报或 Notion 记录。
- 是否在 `README.md` 和 `docs/runbook.md` 中写清楚恢复步骤。
