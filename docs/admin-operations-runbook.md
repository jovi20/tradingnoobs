# Admin Operations Runbook

更新时间：2026-06-11
适用阶段：P17 Admin operations

P17 的目标是把高风险管理员操作收口到受 `get_current_admin` 保护的 API 和前端控制台中，减少临时 shell 操作。

---

## 1. 数据库备份

入口：
- 后端：`POST /api/admin/ops/backups`
- 前端：`/admin/ops`

SQLite 行为：
- 当前 V1 会复制当前 SQLAlchemy 连接指向的 SQLite 数据库文件。
- 默认备份目录是 `backend/backups`。
- 响应包含 `status`、`backup_id`、`path`、`database_backend`、`created_at`、`message`。
- 备份文件不会通过浏览器下载；需要恢复时由运维人员在服务器侧处理。

PostgreSQL 行为：
- 在未配置明确 backup provider/command 前，接口返回 `409 BACKUP_PROVIDER_NOT_CONFIGURED`。
- P17 不会隐式执行 shell 备份命令，避免把危险操作藏在 API 后面。

验证：

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_admin_operations_api.py
```

---

## 2. 管理员提升

入口：
- 后端：`POST /api/admin/users/{user_public_id}/promote`
- 前端：`/admin/ops`

流程：
- 输入目标用户的 `public_id`。
- 接口显式把目标用户 `role` 更新为 `admin`。
- P17 不提供降级、删除账户或批量权限变更。
- 成功和失败都会通过标准 admin API 权限边界处理；缺失用户返回 `404 USER_NOT_FOUND`。

审计：
- 后端记录结构化日志事件 `admin_user_promoted`。
- 日志只记录 actor/target public id，不记录敏感凭据。

---

## 3. 密码重置

入口：
- 后端：`POST /api/admin/users/{user_public_id}/reset-password`
- 前端：`/admin/ops`

流程：
- 系统生成长度至少 18 的临时密码。
- 同步更新 `User.hashed_password` 和 `UserCredential.password_hash`。
- 撤销目标用户现有 active `UserSession` 与未撤销 `AuthToken`。
- 临时密码只在本次响应中返回一次。

操作要求：
- 不要在日志、工单、群聊或截图中长期保存临时密码。
- 通过安全渠道交付临时密码。
- 要求用户登录后立即更换密码。

审计：
- 后端记录结构化日志事件 `admin_user_password_reset`。
- 日志包含 actor/target public id 与撤销 session/token 数量，不记录临时密码。

---

## 4. Stale Job 与恢复建议

入口：
- 后端：`GET /api/admin/jobs`、`GET /api/admin/jobs/{job_public_id}`
- 前端：`/admin/jobs`

解释字段：
- `stale_reason`：RUNNING job 的 `locked_at` 超过 job definition `timeout_seconds` 时返回原因。
- `recommended_action`：失败任务返回 `REQUEUE`；stale running 任务返回 `FORCE_CANCEL`；仍在合理时间内运行的任务返回 `WAIT`。
- `force_cancel_warning`：RUNNING job 展示强制取消风险。

超时规则：
- 优先使用 `JobDefinition.timeout_seconds`。
- 没有 timeout 配置时使用 30 分钟。

---

## 5. Force-Cancel 风险

前端要求：
- `/admin/jobs` 中 RUNNING job 必须输入 `FORCE CANCEL` 才能点击 Force。

后端行为：
- `POST /api/admin/jobs/{job_public_id}/force-cancel` 只允许 RUNNING job。
- 会释放该 job 拥有的 active business locks。
- 会记录 `JobRunEvent`，metadata 中包含 `force=true`、释放的 lock public id 和 warning。

风险：
- Force-cancel 可能留下部分完成的派生工作。
- 使用前应先查看 stale reason、business locks、payload 和事件历史。
- 非 stale RUNNING job 默认建议 `WAIT`。

---

## 6. 恢复演练 Outline

SQLite restore drill：
- 选择一个最新备份文件。
- 停止应用和 worker，避免恢复过程中继续写入。
- 复制当前数据库文件到隔离目录作为二次保护。
- 用备份文件替换当前 SQLite 数据库文件。
- 启动后端，执行健康检查与关键页面 smoke。
- 运行核心测试或至少验证登录、Timeline、Positions、Admin Jobs。

PostgreSQL restore drill：
- P17 还未提供 PostgreSQL backup provider。
- 在启用 PostgreSQL 备份前，需要先明确外部备份命令、凭据管理、存储位置和恢复流程。
- 不要通过当前 P17 API 尝试 PostgreSQL shell 备份或恢复。

回滚：
- 如果 admin operations 前端异常，可临时隐藏 `/admin/ops` 导航入口，但保留后端受 admin 鉴权保护的 API。
- 如果 backup provider 行为异常，优先禁用触发入口并保留已有备份文件，不要删除备份。
