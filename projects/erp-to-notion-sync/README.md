# ERP 数据同步到 Notion

## 项目目标

从 ERP 读取拼多多相关的订单、商品、SKU、金额、退款、库存等明细，清洗后写入 Notion 明细数据库。这个项目是拼多多周报、广告复盘和后续自动上架的数据底座。

## 当前状态

- 状态：规划中
- 自动化脚本：未创建
- 外部 Notion 明细数据库：待补充

## 数据流

```text
ERP 明细数据 -> 字段清洗/唯一键生成 -> Notion 明细数据库 -> 周报/复盘/自动化复用
```

## 运行方式

当前暂无可执行脚本。第一版建议先做 dry-run，只输出准备写入 Notion 的记录预览，不真实写入。

计划命令：

```powershell
python automation/sync_erp_to_notion.py --dry-run
```

## 环境变量

参考 `config/.env.example`。

## 文档

- 运行手册：`docs/runbook.md`
- ERP 字段：`docs/erp-source-schema.md`
- Notion 明细库：`docs/notion-detail-schema.md`

