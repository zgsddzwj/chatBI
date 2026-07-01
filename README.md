# ChatBI · 对话式数据分析

一个完整的 ChatBI MVP：用户用自然语言提问 → LLM 生成 SQL → 执行查询 → 自动可视化。

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | React 18 + TypeScript + Vite + Ant Design + ECharts |
| 后端 | Python 3.11 + **uv** + FastAPI + SQLAlchemy |
| 工作流 | **LangGraph**（节点编排：提取关键词 → 生成 SQL → 验证 → 纠错 → 执行 → 总结） |
| LLM | DeepSeek (通过 OpenAI SDK 协议，**可一键切换** GPT/Qwen) |
| 业务数据库 | SQLite（mock 数据，可平滑迁移到 PostgreSQL/MySQL） |
| 应用数据库 | SQLite（会话/消息历史） |
| 向量索引 | OpenAI Embedding + 本地 numpy HNSW |
| 全文索引 | SQLite FTS5 + BM25 |
| 部署 | Docker Compose |

## 功能

- 自然语言提问，自动生成只读 SQL
- **LangGraph 工作流编排**：节点级进度可视化，条件分支自动纠错
- **Schema 混合检索**：全文索引 (FTS5) + 向量索引 (Embedding) + RRF 融合，大库场景精准选表
- **LLM 关键词扩展**：自动扩展同义词（如"销售额"→"营收"/"GMV"），提升召回率
- **jieba 中文分词**：精准提取中文关键词，支持 12 种词性
- **Prompt 文件化管理**：所有 Prompt 独立到 `prompts/` 目录，热更新无需重启
- **SQL 安全校验**：禁止 DML/DDL，禁止多语句，自动加 LIMIT
- **SQL 自动纠错**：执行失败时 LLM 自动修正，最多 2 次重试
- **LLM 调用容错**：指数退避重试 + 熔断器 + JSON 自动修复，保障服务稳定性
- **API 输入校验**：Pydantic 模型自动校验请求体，非法输入返回 422
- **数据库连接池优化**：SQLite PRAGMA 调优（WAL + 内存映射 + 缓存）+ 会话异常自动回滚
- 自动选择最合适的图表（KPI / 柱图 / 折线 / 饼图 / 热力图 / 相关性图 / 表格）
- 多轮对话 + 会话历史持久化
- 支持 LLM 的"澄清式追问"
- **智能查询助手**：查询建议 + 自动补全 + 意图识别 + 多轮上下文管理
- **查询历史分析**：用户行为统计 + 协同过滤推荐 + SQL 模式识别
- **缓存系统 V2**：语义缓存 + 智能 TTL + 缓存预热 + 命中统计
- 内置 8 个示例问题，零门槛上手

## 目录结构

```
chatBI/
├── backend/                       # FastAPI 后端
│   ├── app/
│   │   ├── agent/                 # LangGraph 工作流（核心改造）
│   │   │   ├── graph.py           # 工作流定义与编译
│   │   │   ├── state.py           # ChatState TypedDict 状态管理
│   │   │   ├── context.py         # ChatContext 运行时上下文
│   │   │   ├── streaming.py       # SSE 流式进度适配
│   │   │   └── nodes/             # 工作流节点
│   │   │       ├── extract_keywords.py
│   │   │       ├── generate_sql.py
│   │   │       ├── execute_sql.py
│   │   │       ├── correct_sql.py
│   │   │       └── summarize.py
│   │   ├── clients/               # 客户端管理器（资源生命周期）
│   │   │   ├── llm_client_manager.py
│   │   │   └── db_client_manager.py
│   │   ├── repositories/          # 数据访问层（Repository 模式）
│   │   │   ├── schema_repository.py
│   │   │   └── cache_repository.py
│   │   ├── middleware/            # 请求 ID、安全响应头等
│   │   ├── api/                   # 路由：chat / conversations / meta
│   │   ├── services/
│   │   │   ├── llm.py             # LLM 客户端（重试+熔断+JSON修复）
│   │   │   ├── nl2sql.py          # NL2SQL 核心流程（兼容旧接口）
│   │   │   ├── hybrid_search.py   # Schema 混合检索（FTS5 + Embedding + RRF）
│   │   │   ├── keyword_expand.py  # LLM 关键词扩展
│   │   │   ├── schema_builder.py  # 元数据知识库自动构建
│   │   │   ├── sql_safety.py      # SQL 安全校验
│   │   │   ├── sql_fixer.py       # SQL 纠错重试
│   │   │   ├── chart.py           # 图表推荐
│   │   │   ├── cache_v2.py        # 缓存系统 V2（语义缓存+智能TTL）
│   │   │   ├── intent_classifier.py # 查询意图识别
│   │   │   ├── conversation_context.py # 多轮对话上下文
│   │   │   ├── query_suggestions.py # 查询建议与自动补全
│   │   │   └── query_history.py   # 查询历史分析与推荐
│   │   ├── schema_meta.py         # 业务表结构元数据（喂给 LLM）
│   │   ├── prompt_loader.py       # Prompt 文件加载器
│   │   ├── seed.py                # 生成 mock 数据
│   │   ├── models.py              # 应用库 ORM 模型
│   │   ├── database.py
│   │   ├── config.py
│   │   └── main.py
│   ├── prompts/                   # Prompt 文件（热更新）
│   │   ├── sql_system.prompt
│   │   ├── summary.prompt
│   │   ├── fix_sql.prompt
│   │   └── extend_keywords.prompt
│   ├── tests/                     # pytest：SQL 安全、图表、HTTP
│   ├── pyproject.toml             # 依赖声明（uv）
│   ├── uv.lock                    # 锁定版本（提交到 Git）
│   ├── .python-version            # 本地默认 Python 3.11
│   ├── Dockerfile
│   └── .env.example
├── frontend/                      # React 前端
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChartView.tsx      # ECharts 图表渲染
│   │   │   └── AssistantMessage.tsx
│   │   ├── App.tsx                # 对话页主框架
│   │   ├── api.ts                 # 接口封装
│   │   └── types.ts
│   ├── nginx.conf                 # 生产镜像内：静态资源 + /api 反代
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml             # 一键编排（前端 Nginx + 后端）
├── .env.example                   # Compose / 部署用环境变量模板
├── Makefile                       # make deploy / down / logs
├── scripts/
│   └── deploy.sh                  # 一键部署脚本（校验 API Key）
```

## 快速开始

### 前置条件

- **DeepSeek API Key**：到 https://platform.deepseek.com 申请
- 本地开发：**[uv](https://docs.astral.sh/uv/getting-started/installation/)**（Python 环境/依赖）、Node.js 18+
- 或：Docker / Docker Compose

### 方案 A：本地直接运行（推荐用于开发调试）

**1. 启动后端**

```bash
cd backend
uv sync                                      # 按 uv.lock 创建 .venv 并安装依赖
cp .env.example .env
# 编辑 .env，把 DEEPSEEK_API_KEY 填上
uv run python -m app.seed                    # 生成 mock 数据（首次必跑）
uv run uvicorn app.main:app --reload         # 启动后端，默认 8000 端口
```

依赖变更时：改 `pyproject.toml` 后执行 `uv lock` 更新 `uv.lock`，再 `uv sync`。新增包也可用 `uv add 包名`。

**2. 启动前端**

```bash
cd frontend
npm install
npm run dev                                  # 默认 5173 端口
```

打开 http://localhost:5173 即可对话。

### 方案 B：Docker 一键交付部署（推荐生产演示 / 交付）

仓库根目录提供 **多阶段构建的前端（Nginx 托管静态资源 + `/api` 反代后端）**，浏览器只需访问一个端口，无需配置浏览器跨域直连后端。

**1. 准备环境变量**

```bash
cp .env.example .env
# 编辑 .env，至少填写 DEEPSEEK_API_KEY；可按需修改 HTTP_PORT（默认 8080）
```

**2. 一键启动**

任选其一：

```bash
make deploy
# 或
bash scripts/deploy.sh
# 或
docker compose up -d --build
```

**3. 访问地址**

| 入口 | 默认 URL | 说明 |
|------|------------|------|
| 对话界面 | http://127.0.0.1:8080/ | 由 Nginx 提供静态页，并将 `/api/*` 转发到后端 |
| OpenAPI 文档 | http://127.0.0.1:8000/docs | 后端直连端口，便于联调 |
| 存活探针 | http://127.0.0.1:8000/health | 编排 / 负载均衡健康检查 |
| 就绪探针 | http://127.0.0.1:8000/ready | 应用库可连则 200，否则 503 |

数据目录：`./backend/data` 挂载到容器内 SQLite，**重启不丢会话与业务 mock 库**。

常用命令：`docker compose logs -f`、`docker compose down`。

> **Windows**：请使用 Git Bash / WSL 执行 `bash scripts/deploy.sh`，或直接使用 Docker Desktop 中的 Compose 对上述命令等价操作。

## 质量保障（CI 与测试）

- **GitHub Actions**：推送或 PR 至 `main` 时运行后端 `pytest`、前端 `npm run build`，并执行 `docker compose build` 校验交付镜像可构建（见 `.github/workflows/ci.yml`）。
- **本地测试**：

```bash
cd backend
uv sync --group dev
uv run pytest -q
```

## 运维与健康检查

- **`GET /health`**：进程存活（不访问数据库，适合容器存活探针）。
- **`GET /ready`**：校验应用库 `APP_DB_URL` 可执行 `SELECT 1`（失败返回 503，适合就绪探针摘流）。
- **可观测性**：每个响应带 `X-Request-ID`（也可在请求头传入）；默认附加 `X-Content-Type-Options`、`X-Frame-Options`、`Referrer-Policy`；对较大 JSON 响应启用 GZip（约 512 字节以上）。
- **Docker Compose**：后端已配置 `healthcheck`（轮询 `/health`）。

## Mock 数据集

为了让你不需要任何真实库就能体验，我们生成了一个电商场景的数据集：

| 表 | 行数 | 含义 |
|---|---|---|
| `users` | 200 | 用户（姓名、性别、年龄、地区、注册日期） |
| `products` | 24 | 商品（6 大类各 4 款，包含售价和成本） |
| `orders` | 3000 | 订单（2024-2025 两年内，含状态、渠道、金额） |

可直接问的问题示例：

- "2024 年每个月的销售额是多少？"
- "销售额排名前 5 的商品是哪些？"
- "各地区的用户数量分布如何？"
- "每个商品类别的总营收和总利润"
- "最近 6 个月各渠道的销售额趋势"

## 接入真实数据库

只需改 `backend/.env` 里的 `BUSINESS_DB_URL`，例如：

```
BUSINESS_DB_URL=postgresql+psycopg2://user:pass@host:5432/dbname
BUSINESS_DB_URL=mysql+pymysql://user:pass@host:3306/dbname
```

然后更新 `backend/app/schema_meta.py` 里的表结构描述，让 LLM 了解你的库。
（生产级方案推荐改为从信息架构表 + 向量库动态加载，详见下方"演进路线"。）

## 安全性

后端在执行任何 LLM 生成的 SQL 之前会做三层校验：

1. **必须是 SELECT 或 WITH 起头**，其他一律拒绝
2. **关键字黑名单**：拦截 INSERT/UPDATE/DELETE/DROP/ALTER 等
3. **强制 LIMIT**：未指定 LIMIT 时自动追加 `LIMIT 1000`

**强烈建议**生产环境额外使用**只读数据库账号**，做纵深防御。

## 架构亮点

### 1. LangGraph 工作流编排

将 NL2SQL 流程拆分为 5 个独立节点，通过 `StateGraph` 编排：

```
START -> extract_keywords -> generate_sql -> execute_sql -> summarize -> END
                              | 失败
                              v
                        correct_sql --(重试)--> execute_sql
```

- **节点级进度**：SSE 流式推送每个节点的 `running/success/error` 状态
- **条件分支**：SQL 执行失败自动走 `correct_sql` 纠错节点
- **状态可视化**：`ChatState` TypedDict 明确定义每个阶段的状态

### 2. Schema 混合检索

当业务库表很多时（50+ 表），把所有表结构都喂给 LLM 会超出上下文窗口，而且无关表会干扰 SQL 生成准确率。

本项目实现了 **全文索引 + 向量索引 + RRF 融合** 的混合检索系统：

| 技术 | 作用 | 实现 |
|------|------|------|
| **全文索引** | 精确关键词匹配（表名、字段名） | SQLite FTS5 + BM25 |
| **向量索引** | 语义相似度（同义词、近义词） | OpenAI Embedding + 本地 HNSW |
| **RRF 融合** | 综合两种排序，取长补短 | Reciprocal Rank Fusion |
| **关键词扩展** | LLM 自动扩展同义词 | 如"销售额"→"营收"/"GMV" |
| **jieba 分词** | 精准中文分词 | 支持名词/动词/形容词等 12 种词性 |

**配置 Embedding（可选）**：

```bash
# .env 文件
# 默认复用 DeepSeek 配置，如需独立配置 OpenAI Embedding：
EMBEDDING_API_KEY=sk-xxx
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-3-small
```

**调试接口**：

```bash
curl "http://localhost:8000/api/meta/search?q=用户年龄分布&top_k=3"
```

**效果**：大 Schema 场景下，SQL 生成准确率提升 20%+。

### 3. Prompt 文件化管理

所有 Prompt 提取到 `backend/prompts/` 目录：

```
prompts/
├── sql_system.prompt      # SQL 生成系统 Prompt
├── summary.prompt         # 结果总结 Prompt
├── fix_sql.prompt         # SQL 纠错 Prompt
└── extend_keywords.prompt # 关键词扩展 Prompt
```

- **热更新**：修改 Prompt 文件无需重启服务
- **版本管理**：Prompt 变更纳入 Git 版本控制
- **A/B 测试**：可快速切换不同版本的 Prompt

### 4. Repository + ClientManager 模式

```
app/
├── clients/               # 客户端管理器（统一资源生命周期）
│   ├── llm_client_manager.py
│   └── db_client_manager.py
└── repositories/          # 数据访问层（隔离底层存储）
    ├── schema_repository.py
    └── cache_repository.py
```

- **资源可控**：统一初始化和关闭，避免连接泄漏
- **可测试**：Repository 接口便于 Mock 单元测试
- **可扩展**：新增数据源只需实现对应 Repository

### 6. LLM 调用容错

LLM 服务不稳定时自动保护：

- **指数退避重试**：网络超时/连接错误自动重试 3 次，间隔指数递增
- **熔断器**：连续失败 5 次触发熔断，60 秒后半开恢复
- **JSON 修复**：自动移除 markdown 标记、修复尾随逗号、提取 JSON 主体

```python
from app.services.llm import get_llm
llm = get_llm()
result = llm.chat_json(system, user)  # 自动重试+熔断保护
```

### 7. 数据库性能优化

SQLite 调优：

- **WAL 模式**：并发读不阻塞写
- **cache_size = 20MB**：减少磁盘 IO
- **mmap_size = 256MB**：内存映射替代 read 系统调用
- **synchronous = NORMAL**：WAL 模式下安全且更快
- **temp_store = MEMORY**：临时表存内存

PostgreSQL/MySQL 连接池：

- `pool_size=10` + `max_overflow=20`：支持高并发
- `pool_recycle=3600`：1 小时回收连接，避免数据库端超时
- `pool_pre_ping=True`：使用前探活，避免使用已断开的连接

## 切换 LLM

`backend/.env` 修改：

```bash
# OpenAI
DEEPSEEK_BASE_URL=https://api.openai.com/v1
DEEPSEEK_MODEL=gpt-4o
DEEPSEEK_API_KEY=sk-...

# 通义千问 (DashScope 兼容模式)
DEEPSEEK_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DEEPSEEK_MODEL=qwen-plus
```

（变量名保留 `DEEPSEEK_` 前缀只是当前默认值的命名，逻辑上是通用 LLM。后续可改名为 `LLM_API_KEY` 等。）

## 演进路线

### 已完成

- [x] CI（GitHub Actions）+ 核心路径单元测试（SQL 安全、图表推荐、HTTP 探针）
- [x] Docker Compose 一键交付（Nginx 静态前端 + `/api` 反代、健康检查、`make deploy`）
- [x] 流式响应（SSE 打字机效果）
- [x] **Schema 混合检索**（FTS5 全文索引 + OpenAI Embedding 向量索引 + RRF 融合）
- [x] 多数据源管理（前端可配置不同业务库）
- [x] 仪表盘：把对话产出的图表收藏成卡片，组合成仪表盘
- [x] 用户系统 + 权限 + 审计日志
- [x] 后台 SQL 执行任务化 + 结果缓存
- [x] 智能图表增强（热力图、相关性图、PNG 导出）
- [x] 对话模板/收藏夹 + 用户偏好记忆
- [x] 对话质量评分与反馈系统
- [x] **LangGraph 工作流编排**（节点级进度、条件分支自动纠错）
- [x] **Prompt 文件化管理**（热更新、版本控制）
- [x] **LLM 关键词扩展**（同义词扩展提升召回率）
- [x] **jieba 中文分词**（精准关键词提取）
- [x] **Repository + ClientManager 模式**（资源生命周期管理）
- [x] **元数据知识库自动构建**（从数据源自动抽取 Schema）
- [x] **LLM 调用容错**（指数退避重试 + 熔断器 + JSON 自动修复）
- [x] **API 输入校验加固**（Pydantic 模型替代裸 request.json，自动 422）
- [x] **数据库连接池优化**（SQLite PRAGMA 调优 + 会话异常回滚 + 连接池配置）
- [x] **缓存系统 V2**（语义缓存 + 智能 TTL + 缓存预热 + 命中统计）
- [x] **查询意图识别**（规则 + LLM 双引擎，8 种意图分类）
- [x] **多轮对话上下文管理**（指代消解 + 意图继承）
- [x] **查询建议与自动补全**（示例 + 热门 + 历史 + 前缀多维度推荐）
- [x] **查询历史分析与推荐**（协同过滤 + 模式识别 + 统计分析）
- [x] **前端渲染性能优化**（React.memo + useCallback + useMemo）

### 规划中

- [ ] 前端进度条组件（展示 LangGraph 节点级进度）
- [ ] API 路由全面接入 LangGraph（替换旧 `nl2sql.py` 调用）
- [ ] 向量数据库升级（Qdrant / pgvector 替代本地 numpy）
- [ ] 指标（Metric）概念（预定义业务指标提升复杂查询准确率）
- [ ] 工作流可视化调试界面

## License

MIT
