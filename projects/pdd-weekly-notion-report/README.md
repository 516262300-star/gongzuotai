# Notion 拼多多周报

## 项目目标

汇总拼多多经营数据，生成周报内容，并写入指定 Notion 页面或数据库。

## 当前状态

- 状态：MVP dry-run 已创建
- 自动化脚本：`automation/build_weekly_report.py`
- 外部 Notion 页面：待补充

## 数据流

```text
拼多多数据源 -> 指标清洗 -> 周报生成 -> Notion 写入 -> 复核
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

当前脚本只支持 dry-run，不会写入 Notion。

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

用真实拼多多导出的 CSV 替换 `data/samples/pdd_weekly_sample.csv` 的样例字段，确认列名后再接入 Notion 写入。
