# ERP 源数据字段

## 待确认

需要先确认 ERP 能提供哪些字段。

建议第一版至少包含：

| 字段 | 说明 |
| --- | --- |
| date | 订单或统计日期 |
| platform | 平台，例如拼多多 |
| shop_name | 店铺名称 |
| order_id | 订单号，如果有 |
| product_name | 商品名称 |
| sku | SKU |
| quantity | 数量 |
| revenue | 成交金额 |
| refund_amount | 退款金额 |
| stock | 库存，如果有 |

## 粒度选择

优先使用订单级明细。如果 ERP 暂时只能提供按天 SKU 聚合数据，也可以先用日聚合。

