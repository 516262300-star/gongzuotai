# Notion 拼多多周报运行手册

## 当前状态

已有第一版 dry-run 脚本，不会写入 Notion。

## 运行命令

从 `projects/pdd-weekly-notion-report/` 目录运行：

```powershell
python automation/build_weekly_report.py --input data/samples/pdd_weekly_sample.csv --week 2026-W26 --dry-run
```

输出文件：

```text
data/output/pdd_weekly_2026-W26.md
```

## 输入文件格式

CSV 必须包含以下列：

```text
date,shop_name,product_name,sku,visitors,orders,revenue,refund_amount,ad_spend
```

## 失败处理

- 如果缺少必要列，脚本会停止并打印缺失列名。
- 如果数字为空或无法识别，脚本会按 0 处理，并在周报的数据检查区展示 warning。
- 当前脚本不写入 Notion，因此失败后不会影响外部系统。

## 上线前必须补充

- 拼多多数据来源。
- 周报指标定义。
- Notion 页面或数据库 ID。
- dry-run 预览命令。
- 写入命令。
- 重复周报检测规则。
- 失败恢复步骤。
