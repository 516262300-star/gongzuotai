# Notion 拼多多周报

## 项目目标

从 Notion 明细数据库汇总拼多多经营数据，生成周报内容，并写入指定 Notion 页面或数据库。Notion 明细数据由 `projects/erp-to-notion-sync/` 从 ERP 同步而来。

## 当前状态

- 状态：MVP dry-run 已创建
- 自动化脚本：`automation/build_weekly_report.py`
- 外部 Notion 页面：待补充

## 数据流

```text
ERP -> Notion 明细数据库 -> 指标汇总 -> Notion 拼多多周报 -> 复核
```

## 运行方式

从本项目目录运行：

```powershell
python automation/build_weekly_report.py --input data/samples/pdd_weekly_sample.csv --week 2026-W26 --dry-run
```

默认输出 Markdown 到：

```text
data/output/pdd_weekly_2026-W26.md
```

当前脚本只支持 CSV dry-run，不会写入 Notion。CSV 是本地模拟输入，用来模拟 Notion 明细库已有数据时的周报汇总结果。

运行时会自动显示状态，并写入工作台运行记录：

```text
logs/script-runs.jsonl
```

查看该脚本最近状态：

```powershell
python ..\..\tools\workbench_status.py --script build_weekly_report.py
```

## 环境变量

参考 `config/.env.example`。

## 文档

- 运行手册：`docs/runbook.md`
- 实施计划：`docs/implementation-plan.md`
- 指标定义：`docs/metric-definition.md`
- Notion 结构：`docs/notion-schema.md`

## 下一步

下一步先完成 `projects/erp-to-notion-sync/`，把 ERP 明细写入 Notion。之后把本脚本从读取 CSV 改为读取 Notion 明细数据库，再写入 Notion 周报。
