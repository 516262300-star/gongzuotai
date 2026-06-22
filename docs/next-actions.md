# 下一步执行清单

## 优先级

第一阶段先做 `ERP 数据同步到 Notion`，再做 `Notion 拼多多周报`。

原因：

- ERP 是业务数据源头，周报不应该长期依赖人工导出。
- Notion 明细数据库是中间层，后续周报、广告复盘、自动上架都可以复用。
- 周报脚本应该从 Notion 明细库汇总，再写回 Notion 周报库。

## 第 1 步：确认 ERP 到 Notion 的明细输入

需要确定：

- ERP 能导出或接口读取哪些数据：订单、商品、SKU、库存、退款、金额。
- ERP 数据是实时接口、定时导出文件，还是数据库读取。
- ERP 里能否区分平台、店铺、商品、SKU、订单时间。
- Notion 明细库按订单粒度还是按天 SKU 粒度保存。

产出：

- `projects/erp-to-notion-sync/docs/erp-source-schema.md`
- `projects/erp-to-notion-sync/docs/notion-detail-schema.md`

## 第 2 步：建立 Notion 明细数据库

需要确定：

- 明细数据库 ID。
- 唯一键规则：订单级用 `date + shop_name + sku + order_id`，日聚合用 `date + shop_name + sku`。
- 字段类型：日期、文本、数字、状态、复选框。
- 重复同步规则：同一唯一键更新已有记录，不重复创建。

产出：

- Notion 明细数据库
- 更新 `projects/erp-to-notion-sync/config/.env.example`

## 第 3 步：做 ERP 到 Notion dry-run 脚本

第一版只做本地 dry-run：

```powershell
python automation/sync_erp_to_notion.py --dry-run
```

必须具备：

- 读取 ERP 样例数据或接口响应。
- 做字段清洗和唯一键生成。
- 输出将要写入 Notion 的记录预览。
- 不写入 Notion。
- 每次运行记录到 `logs/script-runs.jsonl`。

## 第 4 步：再做周报汇总

当前已完成一个 CSV 本地模拟脚本：

```powershell
python automation/build_weekly_report.py --input data/samples/pdd_weekly_sample.csv --week 2026-W26 --dry-run
```

当前已完成第一版 dry-run 脚本：

- 脚本：`projects/pdd-weekly-notion-report/automation/build_weekly_report.py`
- 样例数据：`projects/pdd-weekly-notion-report/data/samples/pdd_weekly_sample.csv`
- 输出：`projects/pdd-weekly-notion-report/data/output/pdd_weekly_2026-W26.md`
- 运行记录：`logs/script-runs.jsonl`
- 状态查看：`python tools/workbench_status.py --script build_weekly_report.py`

它不是最终数据链路，只用于模拟 Notion 明细数据已经存在时的周报汇总。

最终脚本应该改为：

```text
读取 Notion 明细数据库 -> 汇总指标 -> 写入 Notion 拼多多周报
```

## 第 5 步：接入 Notion 周报写入

在 ERP 明细同步稳定后再增加：

```powershell
python automation/build_weekly_report.py --week 2026-W26 --read-notion --write-notion
```

必须具备：

- 写入前校验 `NOTION_TOKEN` 和 `NOTION_DATABASE_ID`。
- 同一周期重复运行时可更新已有记录。
- 写入结果记录到日志。
- 失败时保留本地 Markdown 结果，方便人工粘贴。

## 第 6 步：再考虑定时化

周报脚本稳定后再加 Windows 计划任务或 GitHub Actions。添加定时任务时必须同步更新：

- 项目 `README.md`
- 项目 `docs/runbook.md`
- 如果有 Notion 使用说明，也要同步更新
