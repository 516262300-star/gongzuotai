# ERP 到 Notion 再到拼多多周报的数据流

根据现有项目读取结果，广告数据和周报的正确链路如下：

```text
ERP 广告数据
  -> D:\desktop\codex\guanggao
  -> Notion 7 个店铺每日广告数据库
  -> D:\desktop\codex\notion拼多多周报\pdd_weekly_report
  -> Notion 拼多多周报页面和 7 个店铺内嵌数据库
```

## 第一层：ERP 到 Notion 广告数据库

现有项目 `D:\desktop\codex\guanggao` 已实现：

- 从 ERP 抓取一到七店广告数据。
- 写入对应 Notion 数据库。
- 判重规则：`日期 + plan_id + 店铺`。
- 每天 9 点通过 Windows 任务计划补漏同步。

## 第二层：Notion 周报生成

现有项目 `D:\desktop\codex\notion拼多多周报\pdd_weekly_report` 已实现：

- 读取 `SHOP_1_DB_ID` 到 `SHOP_7_DB_ID`。
- 按上周一到上周日过滤。
- 全店托管单独汇总。
- 稳定成本按商品 ID 聚合。
- 在 Notion 周报页面下创建 7 个店铺内嵌数据库。

## 工作台内 CSV 模拟器的处理

早期创建过一个工作台内 CSV 周报模拟器，但它不是现有真实链路，已经从工作台删除。

后续优先接入现有 `notion拼多多周报` 项目，而不是继续扩展 CSV 模拟器。
