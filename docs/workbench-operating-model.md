# 工作台运行模型

工作台分三层：

## 1. 总入口

根目录 `README.md` 负责回答：

- 现在有哪些项目。
- 每个项目在哪里。
- 新增项目要怎么放。
- 通用凭据和文档规则在哪里。

## 2. 项目目录

每个项目目录负责回答：

- 这个项目做什么。
- 输入源是什么。
- 输出到哪里。
- 如何运行、排障、恢复。
- 哪些环境变量必须配置。

## 3. 自动化任务

每个自动化任务必须回答：

- 入口命令是什么。
- 是否支持 dry-run。
- 是否会写入外部系统。
- 失败后如何重试或恢复。
- 如何避免重复创建记录或商品。

所有自动化任务还必须写入工作台运行记录：

- 本地日志：`logs/script-runs.jsonl`
- 状态查看：`python tools/workbench_status.py`
- 脚本登记：`registry/scripts.yml`

## 推荐推进顺序

1. 先读取并登记现有四个项目，确认真实入口、数据流、日志和敏感文件边界。
2. 再做工作台状态面板，读取现有项目日志和运行历史。当前命令：`python tools/workbench_external_status.py`。
3. 再做统一启动入口，调用现有项目命令并写入工作台运行记录。当前命令：`python tools/workbench_run.py --list`。
4. 再做本地网页工作台。当前命令：`python tools/workbench_app.py`。
5. 最后再考虑是否把现有项目迁入 `projects/`，迁移前必须同步 README、runbook 和任务计划路径。

## 拼多多广告同步网页控制

工作台里的 `拼多多广告同步` Agent 不是普通任务列表，它需要保留原本本地桌面脚本的关键控制项：

- 单日日期：传给 `tools/workbench_run.py pdd-ads-sync-all --date YYYY-MM-DD`。
- 日期范围：传给 `tools/workbench_run.py pdd-ads-sync-all --range YYYY-MM-DD~YYYY-MM-DD`。
- 店铺：传给 `--store all` 或具体店铺 ID。
- 只检查、不写入 Notion：传给工作台 `--check-only`，由工作台转为广告脚本的 `--dry-run`。
- 重新登录并同步：传给 `--relogin`。
- 打开日志文件夹：打开 `D:\desktop\codex\guanggao\debug`。
- 页面不再额外显示底部通用任务行；`pdd-ads-catchup` 和 `pdd-ads-sync-all` 仍作为底层任务保留，由广告同步专用按钮统一调用。

真实执行仍然必须在网页输入 `EXECUTE`，避免误写 Notion。
