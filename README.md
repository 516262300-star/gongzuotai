# 个人工作台

这个目录用来集中管理所有自动化、数据同步、报表、上架和后续项目。目标是让每个项目都有独立边界、统一入口、统一凭据约定、统一运行说明，后续新增项目时直接复制模板即可。

## 当前项目

| 项目 | 目录 | 状态 | 说明 |
| --- | --- | --- | --- |
| ERP 自动上架 | `projects/erp-auto-listing/` | 规划中 | 从 ERP 或商品资料源读取商品信息，生成或执行平台上架流程。 |
| Notion 拼多多周报 | `projects/pdd-weekly-notion-report/` | 规划中 | 汇总拼多多经营数据，生成周报并写入 Notion。 |
| 拼多多自动上架 | `projects/pdd-auto-listing/` | 规划中 | 针对拼多多平台的商品发布、更新、校验和失败重试。 |
| 广告数据自动读取到 Notion | `projects/ads-to-notion/` | 规划中 | 定期读取广告平台数据，清洗后同步到 Notion 数据库。 |

## 目录说明

```text
.
├── docs/                 # 工作台规范、自动化标准、项目模板
├── registry/             # 项目登记表和后续可机器读取的配置
├── projects/             # 每个项目一个独立目录
└── AGENTS.md             # Codex/协作规则
```

每个项目目录建议保持一致：

```text
project-name/
├── README.md             # 项目入口说明
├── automation/           # 脚本、定时任务、同步任务
├── config/               # 示例配置，真实密钥不要提交
├── data/                 # 本地样例数据、导入导出文件
└── docs/                 # 运行手册、Notion/外部文档同步说明
```

## 新增项目流程

1. 在 `projects/` 下创建项目目录。
2. 复制 `docs/project-template.md` 的结构。
3. 在 `registry/projects.yml` 登记项目名称、负责人、状态、入口和文档。
4. 如果新增或修改自动化脚本，同步更新该项目 `README.md` 和 `docs/runbook.md`。
5. 涉及密钥时，只提交 `.env.example`，真实值放本地 `.env` 或系统环境变量。

## 下一步

优先推进 `projects/pdd-weekly-notion-report/`，已创建第一版只读 dry-run 周报脚本。执行清单见 `docs/next-actions.md`。

## 凭据约定

- 不提交真实账号、密码、cookie、token、API key。
- 每个项目只保留 `config/.env.example`。
- 通用凭据命名参考 `docs/automation-standards.md`。
