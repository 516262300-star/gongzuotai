# Notion 拼多多周报实施计划

## MVP 范围

第一版只处理一个店铺、一个周期的数据，已生成本地 Markdown 周报，不自动写入 Notion。

## 输入

优先支持 CSV，后续再支持 Excel 或 API。

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

## 待确认

- 实际导出的拼多多数据列名。
- Notion 是页面写入还是数据库写入。
- 是否需要多店铺。
- 是否需要和广告数据合并。
