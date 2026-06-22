# Notion 拼多多周报实施计划

## MVP 范围

第一版只处理一个店铺、一个周期的数据，已生成本地 Markdown 周报，不自动写入 Notion。

注意：CSV 只是本地模拟输入，最终数据源应为 Notion 明细数据库。Notion 明细数据库由 `projects/erp-to-notion-sync/` 从 ERP 同步生成。

## 输入

当前支持 CSV 只是为了模拟 Notion 明细数据。最终输入应改为 Notion 明细数据库查询结果。

建议字段：

| 字段 | 说明 |
| --- | --- |
| date | 日期 |
| shop_name | 店铺名称 |
| product_name | 商品名称 |
| sku | 商品编码 |
| visitors | 访客数 |
| orders | 订单数 |
| revenue | 销售额 |
| refund_amount | 退款金额 |
| ad_spend | 推广花费 |

## 输出

第一版输出 Markdown：

- 本周摘要
- 核心指标
- TOP 商品
- 异常项
- 下周动作

## 指标

| 指标 | 计算方式 |
| --- | --- |
| 销售额 | `sum(revenue)` |
| 订单数 | `sum(orders)` |
| 访客数 | `sum(visitors)` |
| 转化率 | `sum(orders) / sum(visitors)` |
| 退款率 | `sum(refund_amount) / sum(revenue)` |
| 推广 ROI | `sum(revenue) / sum(ad_spend)` |

## 第一版命令

```powershell
python automation/build_weekly_report.py --input data/samples/pdd_weekly_sample.csv --week 2026-W26 --dry-run
```

脚本路径：

```text
automation/build_weekly_report.py
```

样例数据：

```text
data/samples/pdd_weekly_sample.csv
```

## 最终链路

```text
ERP -> Notion 明细数据库 -> 拼多多周报汇总 -> Notion 周报数据库/页面
```

## 待确认

- ERP 明细同步到 Notion 后的真实字段名。
- Notion 是页面写入还是数据库写入。
- 是否需要多店铺。
- 是否需要和广告数据合并。
