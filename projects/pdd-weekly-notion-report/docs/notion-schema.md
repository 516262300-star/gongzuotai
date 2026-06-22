# Notion 周报结构

## 推荐方式

建议使用 Notion 数据库承载周报，每周一条记录。这样后续可以按店铺、周期、指标状态筛选，也方便广告数据同步项目复用。

## 推荐字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| Name | title | 周报标题，例如 `拼多多周报 2026-W26` |
| Week | rich_text 或 select | 周期，例如 `2026-W26` |
| Shop | rich_text 或 select | 店铺 |
| Start Date | date | 周期开始日期 |
| End Date | date | 周期结束日期 |
| Revenue | number | 销售额 |
| Orders | number | 订单数 |
| Visitors | number | 访客数 |
| Conversion Rate | number | 转化率 |
| Refund Amount | number | 退款金额 |
| Refund Rate | number | 退款率 |
| Ad Spend | number | 推广花费 |
| ROI | number | 推广 ROI |
| Summary | rich_text | 本周摘要 |
| Actions | rich_text | 下周动作 |

## 重复写入规则

建议以 `Week + Shop` 作为唯一键：

- 如果 Notion 中不存在该周报，则创建新记录。
- 如果已存在，则更新已有记录。
- 每次写入前先输出 dry-run 预览。

## 待确认

- 目标 Notion 数据库 ID。
- 是否已有周报数据库。
- 字段名称是否要中文化。
- 是否需要把完整 Markdown 周报写入页面正文。

