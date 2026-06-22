# Notion 明细数据库结构

## 推荐数据库

```text
PDD ERP Sales Detail
```

## 推荐字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| Name | title | 唯一键或摘要标题 |
| Date | date | 日期 |
| Platform | select | 平台 |
| Shop | select 或 rich_text | 店铺 |
| Order ID | rich_text | 订单号 |
| Product | rich_text | 商品名称 |
| SKU | rich_text | SKU |
| Quantity | number | 数量 |
| Revenue | number | 成交金额 |
| Refund Amount | number | 退款金额 |
| Stock | number | 库存 |
| Source | select | 数据来源，例如 ERP |
| Synced At | date | 同步时间 |

## 唯一键

订单级：

```text
date + shop_name + sku + order_id
```

日聚合：

```text
date + shop_name + sku
```

