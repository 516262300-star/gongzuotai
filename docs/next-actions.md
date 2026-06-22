# 下一步执行清单

## 优先级

第一阶段先做 `Notion 拼多多周报`。

原因：

- 风险低，第一版可以只读数据并 dry-run 预览，不直接改商品或发布内容。
- 会先打通 Notion 凭据、字段映射和写入规则，后续广告数据同步也能复用。
- 周报指标明确后，可以反过来指导广告数据和 ERP 商品数据要沉淀哪些字段。

## 第 1 步：确认周报输入

需要确定：

- 拼多多数据来自哪里：后台导出的 Excel/CSV、API、还是人工整理表。
- 周报周期：自然周、上周一到周日、还是自定义日期。
- 需要看的核心指标：销售额、订单数、访客数、转化率、退款、推广花费、ROI 等。
- 是否需要按店铺、商品、类目、活动拆分。

产出：

- `projects/pdd-weekly-notion-report/docs/metric-definition.md`
- 一份样例数据放到 `projects/pdd-weekly-notion-report/data/samples/`

## 第 2 步：确认 Notion 输出

需要确定：

- 写入 Notion 页面，还是写入 Notion 数据库。
- 周报标题格式，例如 `拼多多周报 2026-W26`。
- Notion 字段：周期、店铺、销售额、订单数、推广花费、ROI、结论、待办。
- 重复写入规则：同一周期更新已有记录，还是创建新记录。

产出：

- `projects/pdd-weekly-notion-report/docs/notion-schema.md`
- 更新 `projects/pdd-weekly-notion-report/config/.env.example`

## 第 3 步：做第一版脚本

第一版只做本地 dry-run：

```powershell
python automation/build_weekly_report.py --input data/samples/pdd_weekly_sample.csv --week 2026-W26 --dry-run
```

当前已完成第一版 dry-run 脚本：

- 脚本：`projects/pdd-weekly-notion-report/automation/build_weekly_report.py`
- 样例数据：`projects/pdd-weekly-notion-report/data/samples/pdd_weekly_sample.csv`
- 输出：`projects/pdd-weekly-notion-report/data/output/pdd_weekly_2026-W26.md`

必须具备：

- 读取样例 CSV 或 Excel。
- 计算核心指标。
- 输出 Markdown 周报预览。
- 不写入 Notion。
- 记录缺失字段和异常数据。

## 第 4 步：接入 Notion 写入

在 dry-run 稳定后再增加：

```powershell
python automation/build_weekly_report.py --input data/export/pdd_weekly.csv --week 2026-W26 --write-notion
```

必须具备：

- 写入前校验 `NOTION_TOKEN` 和 `NOTION_DATABASE_ID`。
- 同一周期重复运行时可更新已有记录。
- 写入结果记录到日志。
- 失败时保留本地 Markdown 结果，方便人工粘贴。

## 第 5 步：再考虑定时化

周报脚本稳定后再加 Windows 计划任务或 GitHub Actions。添加定时任务时必须同步更新：

- 项目 `README.md`
- 项目 `docs/runbook.md`
- 如果有 Notion 使用说明，也要同步更新
