# ERP 到 Notion 再到拼多多周报的数据流

根据现有项目读取结果，广告数据和周报的正确链路如下：

```text
ERP 广告数据
  -> D:\desktop\codex\guanggao
  -> Notion 7 个店铺每日广告数据库
ERP 店铺概况、消费者体验和盈亏数据
  -> D:\desktop\codex\notion拼多多周报\pdd_weekly_report
  -> Notion 完整拼多多周报页面、7 个店铺广告库和盈亏数据库
```

## 第一层：ERP 到 Notion 广告数据库

现有项目 `D:\desktop\codex\guanggao` 已实现：

- 从 ERP 抓取一到七店广告数据。
- 写入对应 Notion 数据库。
- 判重规则：`日期 + plan_id + 店铺`。
- 每天 9 点通过 Windows 任务计划补漏同步。

## 第二层：Notion 周报生成

现有项目 `D:\desktop\codex\notion拼多多周报\pdd_weekly_report` 已实现：

- 读取 `SHOP_1_DB_ID` 到 `SHOP_7_DB_ID`，并从 ERP 读取店铺概况、消费者体验和盈亏数据。
- 个人工作台按截止昨天的当月单月区间运行，避免盈亏业务线汇总跨月。
- 全店托管单独汇总。
- 稳定成本按商品 ID 聚合。
- 在 Notion 周报页面下生成店铺概况、消费者体验、7 个店铺广告库和盈亏数据库。

## 工作台内 CSV 模拟器的处理

早期创建过一个工作台内 CSV 周报模拟器，但它不是现有真实链路，已经从工作台删除。

后续优先接入现有 `notion拼多多周报` 项目，而不是继续扩展 CSV 模拟器。

## ERP 认证入口

广告同步、周报、拼多多取价及小程序上架统一通过 Leedis 桌面客户端和专用 ERP Chrome 取得网页会话。客户端未登录时停止任务，人工登录后重试。数据流、Notion 写入规则及定时任务时间不变。配置和恢复步骤见 README 的 ERP 客户端登录章节。
