# ChatBI · 对话式数据分析

一个完整的 ChatBI MVP：用户用自然语言提问 → LLM 生成 SQL → 执行查询 → 自动可视化。

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | React 18 + TypeScript + Vite + Ant Design + ECharts |
| 后端 | Python 3.11 + **uv** + FastAPI + SQLAlchemy |
| LLM | DeepSeek (通过 OpenAI SDK 协议，**可一键切换** GPT/Qwen) |
| 业务数据库 | SQLite（mock 数据，可平滑迁移到 PostgreSQL/MySQL） |
| 应用数据库 | SQLite（会话/消息历史） |
| 部署 | Docker Compose |

## 功能

- 自然语言提问，自动生成只读 SQL
- **SQL 安全校验**：禁止 DML/DDL，禁止多语句，自动加 LIMIT
- 自动选择最合适的图表（KPI / 柱图 / 折线 / 饼图 / 表格）
- 多轮对话 + 会话历史持久化
- 支持 LLM 的"澄清式追问"
- 内置 8 个示例问题，零门槛上手

## 目录结构

```
chatBI/
├── backend/                       # FastAPI 后端
│   ├── app/
│   │   ├── api/                   # 路由：chat / conversations / meta
│   │   ├── services/
│   │   │   ├── llm.py             # DeepSeek 客户端
│   │   │   ├── nl2sql.py          # NL2SQL 核心流程
│   │   │   ├── sql_safety.py      # SQL 安全校验
│   │   │   └── chart.py           # 图表推荐
│   │   ├── schema_meta.py         # 业务表结构元数据（喂给 LLM）
│   │   ├── seed.py                # 生成 mock 数据
│   │   ├── models.py              # 应用库 ORM 模型
│   │   ├── database.py
│   │   ├── config.py
│   │   └── main.py
│   ├── pyproject.toml               # 依赖声明（uv）
│   ├── uv.lock                      # 锁定版本（提交到 Git）
│   ├── .python-version              # 本地默认 Python 3.11
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
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml
└── README.md
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

### 方案 B：Docker Compose 一键启动

```bash
# 在仓库根目录创建 .env 文件
echo "DEEPSEEK_API_KEY=sk-xxxxxxxx" > .env

docker compose up --build
```

- 前端：http://localhost:5173
- 后端：http://localhost:8000  ·  API 文档：http://localhost:8000/docs

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

- [ ] 流式响应（SSE 打字机效果）
- [ ] Schema 向量检索（pgvector）：大库场景下提升 SQL 准确率
- [ ] 多数据源管理（前端可配置不同业务库）
- [ ] 仪表盘：把对话产出的图表收藏成卡片，组合成仪表盘
- [ ] 用户系统 + 权限 + 审计日志
- [ ] 后台 SQL 执行任务化 + 结果缓存

## License

MIT
