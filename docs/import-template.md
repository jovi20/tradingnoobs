# 通用交易导入模板、Preview 与 Confirm

更新时间：2026-07-25

`JRN-011/012` 已实现 owner-bound、持久化的 `GENERIC_BOOTSTRAP` upload/preview 与一次性 canonical confirm。Preview 只校验并保存 normalized rows，不写入 position、event 或 ledger；只有 confirm 会在一笔事务中写入 canonical facts。

## 当前接口

- `GET /api/positions/import/template`：下载 UTF-8 CSV canonical 模板。
- `POST /api/positions/import/upload`：上传 CSV/XLSX，必须提供目标账户和 `Idempotency-Key`。
- `GET /api/positions/import/sessions/{session_public_id}`：仅 owner 可重新读取持久 preview。
- `POST /api/positions/import/confirm`：提交最终选中的有效行和 `Idempotency-Key`，原子 replay canonical lifecycle。

上传限制为 10 MiB、5,000 行，preview TTL 为 24 小时。到期判断不依赖后台 worker；`now == expires_at` 即返回 `410 IMPORT_SESSION_EXPIRED`。终态 normalized rows 保留 30 天后由限批 maintenance command 清理，ImportSession audit shell 永久保留。

任一 ImportSession 一经创建，目标账户永久失去 hard-delete 资格；删除操作只会 archive 账户。普通文件声明的 `external_trade_id`、`source_id` 或类似字段不会获得可信来源身份，只会产生 warning。

Generic confirm 只接受活跃、`CLEAN` 且除 opening balance 外没有交易或资金事实的账户。非空成功 confirm 会原子执行 `CLEAN -> MANUAL`，以后不能再次使用 generic bootstrap；void、archive 或 preview cleanup 都不会恢复资格。空选择会以 `COMPLETED_NOOP` 消费当前 session、写入 0 条事实并保持 `CLEAN`，之后可以创建新的 bootstrap session。

选中行按完整 instrument identity 和 direction 分组，组内按 UTC 时间及原文件 row number 稳定 replay。每组必须从 `OPEN` 开始；`ADD/REDUCE/CLOSE` 必须形成合法 quantity prefix，full close 后可以开始新的 `OPEN`，多空方向互不 net。任一行失败会回滚 position、event、posting、账户状态、session 完成状态和 confirm 幂等记录。成功响应及 confirm 幂等记录永久保留；同 key/hash 可重放原响应，其他 key/hash 不能二次消费 session。

该 adapter 不是月度增量导入。未来同一 IBKR 账户的重复、重叠和只应用新增 execution 由 `IBKR_FLEX_XML_V1` source-bound 路径承担。

## Canonical 模板列

| 列名 | 必填 | 当前 preview 规则 |
|------|------|------------------|
| `asset_type` | 是 | `STOCK`、`FUND`、`CRYPTO`；`EQUITY`、`ETF`、`SPOT_CRYPTO` 会显式规范化。 |
| `market` | 是 | `US` 或 `CRYPTO`，并与 asset/instrument 组合一致。 |
| `exchange_code` | 是 | 1-32 位 ASCII 交易场所代码。 |
| `symbol` | 是 | 1-50 位 canonical symbol。 |
| `instrument_type` | 是 | Beta 只允许 `SPOT`。 |
| `direction` | 是 | `LONG` / `SHORT`；`BUY` / `SELL` 与 `L` / `S` 是输入别名。 |
| `action` | 是 | 明确的 `OPEN` / `ADD` / `REDUCE` / `CLOSE`；`ENTRY` 规范化为 `OPEN`。 |
| `timestamp` | 是 | ISO-8601；带 offset 时使用该 offset，无 offset 时使用用户 IANA 时区。DST fold/gap 返回 422。 |
| `price` | 是 | 大于 0 的 decimal。 |
| `quantity` | 是 | 大于 0 的 decimal。 |
| `currency` | 是 | 当前 release 只允许 `USD`，且必须等于账户币种。 |
| `commission` | 否 | 非负、单 event 聚合 fee；confirm 写入 canonical `TRADE_FEE` posting。 |
| `fee_currency` | 否 | 省略时使用账户币种；提供时必须等于账户币种。 |
| `reason` | 否 | 交易理由。 |
| `note` | 否 | 附加备注。 |

完全相同的 normalized row 不会被静默去重；后续重复行显示 `DUPLICATE_ROW` warning，选中后仍逐行参与完整 lifecycle 校验。同一时间的行保留原文件 row number，confirm 按该顺序稳定 replay。合法但尚未建档的 instrument 显示 `CREATE_ON_CONFIRM`，preview 本身不会创建 instrument。

## 临时文件与维护

原始文件只进入权限为 `0700` 的临时目录，单个临时文件权限为 `0600`。成功、失败、取消和异常路径都会 close 并 unlink；应用启动和以下独立命令清除崩溃遗留文件：

```bash
PYTHONPATH=backend backend/venv/bin/python backend/ops/maintain_import_sessions.py
```

该命令同时限批执行 session expiry 和 30 天 normalized-row cleanup。清理失败可安全重跑，不删除 audit shell、账户或任何财务事实。

## Historical unregistered legacy parser reference

仓库仍保留 `backend/services/import_service.py` 作为未注册的历史实现参考。它使用进程内 cache、legacy `Position/TradeBatch` 写入和不完整的 identity/fee 语义；当前路由不导入或调用该 service。

旧 parser 曾使用 `Time (YYYY-MM-DD HH:MM)`、`Symbol`、`Direction`、`Action`、`Price`、`Quantity`、`Planned Entry`、`Planned SL`、`Asset Type`、`Strategy`、`Emotion`、`Confidence`、`Reason` 和 `Commission`。这些旧字段和错误字符串不构成当前接口合同；当前合同只以上述 canonical 模板、OpenAPI 和机器 release contract 为准。

`IBKR_FLEX_XML_V1` source-bound 本地文件 adapter 仍由 `JRN-013` 至 `JRN-015` 实现。它将用稳定 execution identity 支持同一账户的重复、重叠、增量文件和 correction replay；它不是在线 Broker Sync，也不读取 Token/Query ID。
