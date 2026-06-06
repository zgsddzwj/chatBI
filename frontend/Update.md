阶段一：安全与数据隔离（P0，1-2 周）

目标：堵住可被直接利用的安全漏洞，建立多用户数据边界。

1.1 认证体系加固

关键文件：[backend/app/services/auth.py](backend/app/services/auth.py)、[backend/app/config.py](backend/app/config.py)





新增独立 JWT_SECRET 环境变量（禁止从 DEEPSEEK_API_KEY 派生）



将 HMAC-SHA256 密码哈希替换为 bcrypt（passlib[bcrypt] 或 bcrypt）



生产环境禁止默认 admin/admin123：首次启动强制改密或要求 ADMIN_PASSWORD 环境变量



Token 增加 exp 校验与 refresh 策略（可选）

1.2 会话归属与权限

关键文件：[backend/app/models.py](backend/app/models.py)、[backend/app/api/conversations.py](backend/app/api/conversations.py)、[backend/app/api/chat.py](backend/app/api/chat.py)、[backend/app/api/export.py](backend/app/api/export.py)





Conversation 表增加 user_id（nullable，兼容匿名；登录用户强制绑定）



所有会话 CRUD / 导出 / 分享接口校验 conversation.user_id == current_user.id



修复流式接口：chat_stream 补充 Request 参数、用户提取、log_audit（与非流式 chat 对齐）



前端修复：[frontend/src/api.ts](frontend/src/api.ts) 的 sendChatStream 附加 Authorization header

1.3 API 防护





添加速率限制（slowapi 或自定义中间件）：/api/chat* 按 IP/用户限流



注册接口增加验证码或管理员审批开关（ALLOW_PUBLIC_REGISTER=false）



错误响应避免泄露内部堆栈（生产环境 APP_ENV=production 时统一消息）

1.4 SQL 安全增强

关键文件：[backend/app/services/sql_safety.py](backend/app/services/sql_safety.py)





补充测试：子查询中的危险关键字、注释注入、UNION SELECT 变体



业务库连接强制只读模式（SQLite mode=ro 或 PG default_transaction_read_only=on）



增加查询超时（statement_timeout / 应用层 timer）

验收标准：登录用户只能看到自己的会话；流式请求带 token 可审计；渗透测试无法通过 LLM 注入执行写操作。



阶段二：工程质量与测试体系（P0，1-2 周）

目标：每次 PR 有自动化质量门禁，核心路径有回归保护。

2.1 静态检查与格式化

新增配置文件（当前完全缺失）：







工具



范围



文件





ruff



Python lint + format



backend/pyproject.toml





mypy（可选）



类型检查



backend/pyproject.toml





ESLint + Prettier



前端



frontend/eslint.config.js





pre-commit



提交前钩子



.pre-commit-config.yaml

2.2 测试扩展

后端 [backend/tests/](backend/tests/)：





集成测试：TestClient 覆盖 chat 全流程（mock LLM）



认证测试：登录、token 过期、角色权限



会话隔离测试：用户 A 无法访问用户 B 的 conversation



流式测试：SSE 事件序列断言

前端 [frontend/](frontend/)：





引入 Vitest + React Testing Library



覆盖：api.ts 拦截器、AssistantMessage 渲染、LoginModal 表单



可选 Playwright E2E：发送问题 → 收到 chart 事件

2.3 CI 升级

关键文件：[.github/workflows/ci.yml](.github/workflows/ci.yml)

# 新增步骤示意
- ruff check + ruff format --check
- pytest --cov=app --cov-fail-under=70
- npm run lint
- npm run test





添加 coverage 报告上传（Codecov 或 artifact）



Docker build 后增加 docker compose up smoke test（curl /health + /ready）

验收标准：CI 全绿包含 lint + test + build；核心 NL2SQL 路径覆盖率 ≥ 70%。



阶段三：前端架构与产品完善（P1，2-3 周）

目标：代码可维护、长对话性能达标、后端已实现功能在前端可见可用。

3.1 前端重构

关键文件：[frontend/src/App.tsx](frontend/src/App.tsx)（~600 行单体）

拆分建议：

frontend/src/
├── pages/ChatPage.tsx          # 主聊天页
├── hooks/useChat.ts            # 流式状态机
├── hooks/useConversations.ts   # 会话列表
├── contexts/AuthContext.tsx    # 替代 auth.ts 裸 localStorage
├── components/ConversationSidebar.tsx
├── components/ChatInput.tsx
└── components/VirtualMessageList.tsx  # 启用已有实现





启用 [VirtualMessageList](frontend/src/components/VirtualMessageList.tsx) + [useVirtualList](frontend/src/hooks/useVirtualList.ts)（消息 > 50 条时切换）



React.memo 包裹 AssistantMessage、ChartView；流式更新时只重渲染最后一条



懒加载：React.lazy 拆分 ECharts 和 Ant Design 重型模块



删除未使用依赖：react-markdown、dayjs

3.2 类型安全

关键文件：[frontend/src/types.ts](frontend/src/types.ts)、[frontend/src/api.ts](frontend/src/api.ts)





StreamEvent.type 改为 discriminated union



QueryResult.rows 使用 unknown[][] 替代 any



开启 noUnusedLocals / noUnusedParameters

3.3 补齐产品 UI

后端 API 已存在但前端未接线（[frontend/src/api.ts](frontend/src/api.ts)）：







功能



后端



前端待做





仪表盘



/api/dashboards/*



仪表盘列表页 + 卡片网格





多数据源



/api/datasources/*



数据源配置页（管理员）





异步任务



/api/tasks/*



长查询进度条 + 结果通知





审计日志



/api/auth/audit



管理员审计页





引入 react-router：路由 /（聊天）、/dashboards、/settings



Pin 图表后跳转到仪表盘查看

3.4 无障碍与 UX





可点击 div 改为 button 或加 role="button" + 键盘事件



流式输出区域加 aria-live="polite"



恢复 input focus ring（移除 outline: none）

验收标准：100+ 条消息对话流畅滚动；仪表盘/数据源可在 UI 操作；TypeScript 无 any 逃逸。



阶段四：NL2SQL 智能化与数据层升级（P1-P2，3-4 周）

目标：大 Schema 场景准确率提升，支持真实生产数据库。

4.1 Schema 动态化

关键文件：[backend/app/schema_meta.py](backend/app/schema_meta.py)、[backend/app/services/schema_search.py](backend/app/services/schema_search.py)





从 information_schema / PRAGMA table_info 自动拉取表结构



保留 schema_meta.py 作为业务注释/别名 overlay



向量检索（pgvector 或本地 faiss）替换纯关键词匹配：





表/字段 embedding 入库



用户问题 top-k 检索后注入 prompt

4.2 多数据源贯通

关键文件：[backend/app/services/datasource.py](backend/app/services/datasource.py)、[backend/app/services/nl2sql.py](backend/app/services/nl2sql.py)





NL2SQLService 按 datasource_id 选择 business_engine（连接池 per datasource）



SQL 方言适配：SQLite / PostgreSQL / MySQL prompt 分支



数据源连接测试接口 + 加密存储连接串

4.3 查询执行优化

关键文件：[backend/app/services/cache.py](backend/app/services/cache.py)、[backend/app/services/tasks.py](backend/app/services/tasks.py)





缓存 TTL 可配置；增加 cache hit/miss metrics



大结果集（>5000 行）自动走异步任务队列，前端轮询 /api/tasks/{id}



定时清理过期缓存（lifespan 或 cron）

4.4 数据库迁移





应用库从 SQLite 迁移到 PostgreSQL（Alembic 管理迁移）



统一 ORM：将 auth/dashboard/cache/tasks 的 raw SQL CREATE TABLE 迁入 Alembic migrations



docker-compose.yml 增加 postgres 服务

验收标准：50+ 表 Schema 下 SQL 生成准确率可量化提升；支持 PG 业务库；多数据源可切换。



阶段五：可观测性与生产部署（P2，2-3 周）

目标：可监控、可扩展、可灾备。

5.1 结构化日志与指标

关键文件：[backend/app/main.py](backend/app/main.py)





结构化 JSON 日志（structlog），字段：request_id, user_id, latency_ms, sql_hash



Prometheus metrics：/metrics 端点





chat_requests_total{status}



llm_latency_seconds



sql_execution_seconds



cache_hit_ratio



可选：OpenTelemetry tracing（LLM 调用 → SQL 执行全链路）

5.2 部署加固

关键文件：[docker-compose.yml](docker-compose.yml)、[frontend/nginx.conf](frontend/nginx.conf)





后端多 worker：uvicorn --workers 4（需 PG 替代 SQLite WAL 争用）



Nginx：rate limit、client_max_body_size、安全头补齐



密钥管理：.env 不入镜像，Compose secrets 或 K8s Secret



备份策略：PG 定时 dump + backend/data volume 快照

5.3 文档同步

关键文件：[README.md](README.md)





更新演进路线（SSE/Auth/Dashboard/Cache 已完成的勾选）



版本号统一（main.py 0.3.0 vs pyproject.toml 0.1.0）



新增 docs/ARCHITECTURE.md（数据流、安全模型、部署拓扑）



新增 docs/CONTRIBUTING.md（开发规范、测试要求）

验收标准：Grafana 可看 QPS/延迟/错误率；双实例部署无 SQLite 锁冲突；文档与代码一致。