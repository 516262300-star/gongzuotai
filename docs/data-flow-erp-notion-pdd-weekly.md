# ERP 到 Notion 再到拼多多周报的数据流

正确链路如下：

```text
ERP 明细数据
  -> ERP 数据同步脚本
  -> Notion 明细数据库
  -> 拼多多周报汇总脚本
  -> Notion 拼多多周报数据库/页面
```

## 第一层：ERP 明细数据

ERP 是源头。后续周报不应该依赖人工从拼多多后台导出文件。

第一批建议同步这些明细：

- 订单明细
- 商品明细
- SKU
- 店铺
- 成交金额
- 订单数量
- 退款金额
- 库存，后续用于自动上架和补货判断

## 第二层：Notion 明细数据库

Notion 先做中间数据层，保存从 ERP 同步过来的可复核数据。

建议至少有一个数据库：

```text
PDD ERP Sales Detail
```

建议唯一键：

```text
date + shop_name + sku + order_id
```

如果 ERP 只能提供按天聚合数据，则唯一键改为：

```text
date + shop_name + sku
```

## 第三层：Notion 拼多多周报

周报脚本从 Notion 明细数据库读取数据，按周期汇总，然后写入周报数据库或页面。

周报唯一键：

```text
week + shop_name
```

重复运行时：

- 已有该周报则更新。
- 没有该周报则创建。
- 每次运行都写入 `logs/script-runs.jsonl`。

## 当前 CSV 脚本的定位

`projects/pdd-weekly-notion-report/automation/build_weekly_report.py` 当前读取 CSV，是本地模拟器，不是最终数据链路。

它的作用是：

- 先验证周报指标怎么算。
- 先验证 Markdown 周报长什么样。
- 先验证运行状态记录是否正常。

最终要改为：

```text
读取 Notion 明细数据库 -> 汇总 -> 写入 Notion 周报
```

