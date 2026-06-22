# ERP 数据同步到 Notion 运行手册

## 当前状态

暂无自动化脚本。

## 第一版目标

先做 dry-run，不写入 Notion：

```powershell
python automation/sync_erp_to_notion.py --dry-run
```

## 上线前必须补充

- ERP 连接方式：接口、导出文件或数据库读取。
- ERP 字段说明。
- Notion 明细数据库 ID。
- 唯一键规则。
- dry-run 命令。
- 写入命令。
- 重复同步时的更新规则。
- 失败恢复步骤。

