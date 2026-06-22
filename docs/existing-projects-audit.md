# 现有四个项目读取结果

本文件记录从现有目录读取到的真实项目结构，后续工作台设计必须以这里为准，不能假设数据源。

## 1. 拼多多广告数据同步到 Notion

源目录：

```text
D:\desktop\codex\guanggao
```

真实用途：

- 从公司 ERP `ldswj.net` 抓取拼多多一到七店广告数据。
- 写入对应 Notion 数据库。
- 默认日期是昨天，默认店铺是 `--store all`。
- 判重规则是 `日期 + plan_id + 店铺`。

主要入口：

```powershell
python main.py --store all
python main.py --date 2026-06-03 --store all
python main.py --range 2026-05-25~2026-05-31 --store all
python main.py --date 2026-06-03 --store all --dry-run
python catchup_daily.py --store all
```

桌面入口：

```text
启动拼多多广告同步.bat
```

定时任务：

```text
Windows 任务计划：拼多多广告数据同步到 Notion
执行脚本：D:\desktop\codex\guanggao\run_daily.ps1
时间：每天 9 点
```

日志：

```text
D:\desktop\codex\guanggao\debug
task_YYYYMMDD_HHMMSS.log
```

敏感文件：

```text
.env
.auth/session.json
```

工作台注意事项：

- 这个项目已经完成“ERP -> Notion 广告明细”的链路。
- 不要要求用户从拼多多后台导出广告 CSV。
- 后续工作台应优先接入它的状态、日志和启动入口。

## 2. Notion 拼多多周报

源目录：

```text
D:\desktop\codex\notion拼多多周报\pdd_weekly_report
```

真实用途：

- 使用 Notion 官方 API 生成「拼多多2026周报」页面。
- 从 7 个店铺每日广告数据数据库读取上周数据。
- 在周报页的“广告情况”下创建 7 个店铺的内嵌数据库。
- 稳定成本按商品 ID 聚合，全店托管单独汇总。

主要入口：

```powershell
python test_connection.py
python main.py
```

桌面入口：

```text
启动拼多多周报生成器.vbs
```

Notion 配置：

```text
NOTION_TOKEN
PARENT_PAGE_ID
MAIN_IMAGE_DB_ID
SHOP_1_DB_ID 到 SHOP_7_DB_ID
NOTIFY_USER_ID
ALERT_PAGE_ID
```

定时任务建议：

```text
Windows 任务计划：拼多多周报生成
时间：每周一 10:00
命令：python main.py
```

日志：

```text
logs/weekly_report_YYYYMMDD.log
```

工作台注意事项：

- 周报不是从拼多多后台导 CSV 生成。
- 周报读取 Notion 中已有的 7 个店铺广告数据库。
- 周报依赖广告同步项目先把 ERP 广告数据写入 Notion。

## 3. 拼多多自动上架工具

源目录：

```text
D:\desktop\codex\拼多多自动上架
```

真实用途：

- 本地网页工作台，辅助拼多多后台自动上架。
- 从 ERP 价格册读取优质价。
- 根据图片空间路径生成上架包。
- Chrome 插件辅助填充拼多多发布页。
- 保存草稿后记录历史。

主要入口：

```powershell
.\start_pdd_publisher.ps1
python desktop_tool.py
python main.py <商品目录> --price-multiplier 1.6
```

桌面入口：

```text
start_pdd_publisher.bat
```

本地服务：

```text
http://127.0.0.1:8765/
```

配置：

```text
config.example.yaml -> config.yaml
ERP_USERNAME / ERP_PASSWORD 环境变量
states/*.json 登录态
```

运行记录：

```text
.tmp_tool/saved_draft_history.json
```

工作台注意事项：

- 这个项目不是“直接发布”，主要流程是生成上架包并填充后台，保存草稿后记录。
- 需要 ERP 优质价、图片空间路径、规格/尺寸图命名共同配合。
- 不要把它和 ERP 自研后台小程序上架混成同一个项目。

## 4. 小程序 ERP 自动上架商品工具

源目录：

```text
D:\desktop\codex\小程序自动上架\erp_auto_upload
```

真实用途：

- 本地 Python + Playwright 工具。
- 用于公司自研 ERP 后台新建商品并上传素材。
- 所有 ERP 页面元素定位集中在 `selectors.py`。
- 默认不会自动保存，除非命令带 `--save`。

主要入口：

```powershell
python main.py parse --material-root "素材目录"
python main.py login
python main.py price-query --material-root "素材目录"
python main.py form-test --material-root "素材目录"
python main.py upload-test --material-root "素材目录"
python main.py upload --material-root "素材目录"
python main.py upload --material-root "素材目录" --save
```

桌面入口：

```text
启动桌面软件.bat
```

配置：

```text
.env.example -> .env
ERP_LOGIN_URL
ERP_USERNAME
ERP_PASSWORD
ERP_HOME_URL
BROWSER_CHANNEL
MATERIAL_ROOT
```

日志：

```text
logs/run_YYYYMMDD.log
logs/screenshots/
```

工作台注意事项：

- 这是“ERP 自研后台新建商品”，不是拼多多后台上架。
- 安全测试命令优先用 `parse`、`form-test`、`upload-test`。
- 真正保存必须显式加 `--save`。

## 工作台真实依赖关系

```text
广告数据链路：
ERP 广告数据 -> guanggao -> Notion 7 店每日广告数据库 -> notion拼多多周报 -> Notion 周报页

拼多多上架链路：
ERP 优质价 + 图片空间素材 -> 拼多多自动上架 -> 拼多多后台草稿/保存历史

ERP 小程序上架链路：
本地素材目录 -> 小程序自动上架 -> ERP 自研后台新建商品
```

## 工作台状态查看

当前已提供只读状态面板：

```powershell
cd D:\desktop\codex\工作台
python tools\workbench_external_status.py
```

这个命令只读取四个项目的日志和历史文件，不执行同步、不写 Notion、不打开浏览器、不保存商品。

## 工作台统一启动

当前已提供统一启动入口：

```powershell
cd D:\desktop\codex\工作台
python tools\workbench_run.py --list
python tools\workbench_run.py status
python tools\workbench_run.py pdd-ads-catchup --dry-run
python tools\workbench_run.py pdd-ads-catchup --execute
```

除 `status` 外，真实启动都必须显式添加 `--execute`，防止误触发写入 Notion、打开浏览器或启动上架工具。
