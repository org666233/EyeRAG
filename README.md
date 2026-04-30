# EyeRAG: 基于 RAG 的眼科医疗知识问答系统

EyeRAG 是一个面向眼科医疗知识场景的检索增强生成（Retrieval-Augmented Generation, RAG）问答系统。本项目来自本科毕业论文《基于 RAG 的眼科医疗知识问答系统设计与实现》，围绕眼科专业文献、临床指南和中文医学百科资料构建知识库，并提供 Vue3 Web 管理端、Flutter 移动端与 FastAPI 后端服务。

系统目标不是替代医生诊疗，而是为普通用户、医学学生和知识库维护人员提供一个有来源引用、可追溯、可管理的眼科知识问答平台。

## 项目特点

- 自研 RAG 管线：不依赖 LangChain 等编排框架，完整实现文档加载、递归分块、向量化、混合检索、重排序、Prompt 构建和流式生成。
- 混合检索：结合 ChromaDB 向量语义检索与 BM25 关键词检索，并通过 RRF（Reciprocal Rank Fusion）融合排序。
- Self-RAG 决策：在生成前由 LLM 评估检索结果相关性和充分性，支持 `proceed`、`retry`、`fallback` 三类决策。
- 跨语言补偿：中文问题可被轻量翻译为英文，并在向量检索和 BM25 检索两条路径上进行双路补偿，以提升中英文混合知识库召回能力。
- 医疗安全检查：对诊断式表述、具体用药剂量、绝对化承诺等风险内容进行规则检测，并追加医疗免责声明。
- 流式问答体验：后端使用 SSE 输出生成片段，前端实时渲染答案、参考来源、检索决策和相关问题。
- 多端客户端：包含 Vue3 Web 端和 Flutter 跨平台移动端，两端共用同一套 FastAPI API。
- 完整工程配套：支持 Docker Compose 启动 MySQL 与 ChromaDB，提供数据采集、知识库入库、模型评测、RAGAs 评估和自动化测试脚本。

## 系统架构

```mermaid
flowchart LR
    U["用户 / 管理员"] --> W["Vue3 Web 端"]
    U --> M["Flutter 移动端"]
    W -->|"HTTP / SSE"| A["FastAPI API 层"]
    M -->|"HTTP / SSE"| A

    A --> R["RAG 业务层"]
    A --> B["认证、会话、收藏、反馈、统计"]

    R --> V["ChromaDB 向量库"]
    R --> BM["BM25 内存索引"]
    R --> L["DeepSeek / MiniMax LLM"]
    B --> D["SQLite / MySQL 关系数据库"]

    K["眼科文档知识库"] --> I["文档解析、分块、向量化脚本"]
    I --> V
```

后端采用分层结构：

- `backend/app/api/`：FastAPI 路由，包含认证、聊天、知识库、收藏、反馈、历史、统计、管理后台等接口。
- `backend/app/rag/`：RAG 核心模块，包含向量库、混合检索、Self-RAG、重排序、嵌入模型、Prompt、LLM 客户端和安全检查。
- `backend/app/models/`：SQLAlchemy 数据模型，管理用户、会话、消息、收藏、反馈、搜索历史等结构化数据。
- `backend/app/schemas/`：Pydantic 请求与响应模型。
- `backend/scripts/`：数据采集、知识库入库、向量库评测、RAGAs 评估和测试辅助脚本。
- `frontend/`：Vue3 + Vite + Element Plus Web 管理端。
- `frontend_flutter/`：Flutter 3 跨平台移动端。
- `毕业论文/thesis/`：论文正文与设计、实验、测试说明文档。

## 核心功能

### 普通用户

- 注册、登录和 JWT 鉴权。
- 眼科自然语言问答，支持 SSE 流式输出。
- 多轮对话，会话列表、会话切换、标题修改和删除。
- 查看参考来源、检索决策和相关问题推荐。
- 检索历史回顾，支持查看完整检索链路。
- 收藏问答、继续追问、复制内容。
- 对回答提交有用/无用反馈。

### 管理员

- 上传 PDF、TXT、Markdown 文档并自动入库。
- 查看知识库文档列表、文本块数量、命中次数和浏览次数。
- 预览、下载、删除知识库文档。
- 使用知识库检索测试接口调试召回效果。
- 查看系统统计看板、反馈趋势、热门查询和响应耗时。
- 管理用户账号，支持启用、禁用和删除用户。
- 在管理后台切换 LLM Provider 与模型配置。

### 移动端增强

Flutter 端在复用后端 API 的基础上，面向移动场景实现了：

- Material 3 主题与明暗模式。
- 语音输入。
- 生物识别登录。
- 收藏离线缓存。
- 截图分享。
- iOS、Android、Web、桌面平台工程骨架。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 后端 API | FastAPI, Uvicorn, Pydantic v2 |
| ORM / 数据库 | SQLAlchemy Async, SQLite, MySQL 8 |
| 认证 | JWT, bcrypt, passlib, python-jose |
| 向量数据库 | ChromaDB |
| 嵌入模型 | SentenceTransformers, BAAI/bge-m3, BGE ZH, text2vec, MiniLM 等 |
| 检索算法 | Dense Retrieval, BM25, RRF, Keyword Reranker, 可选 CrossEncoder |
| LLM | DeepSeek OpenAI-compatible API, MiniMax Anthropic-compatible API |
| Web 前端 | Vue3, Vite, Element Plus, Pinia, Vue Router, Axios, ECharts |
| 移动端 | Flutter 3, Riverpod, go_router, Dio, local_auth, speech_to_text, sqflite |
| 测试 | pytest, pytest-asyncio, Vitest, Locust |
| 部署 | Docker Compose, MySQL, ChromaDB |

## 知识库与实验

论文实验中使用的眼科知识库包含约 264 个原始文档，主要来源包括：

- PubMed Central 眼科综述文献。
- NICE / AAO 等临床指南。
- Wikipedia 眼科基础和扩展医学词条。
- 丁香园眼科疾病百科。
- 寻医问药网眼科疾病百科。

文档经过递归字符分块后形成约 28,000 个向量文本块。实验评估包括：

- 嵌入模型基准评测：MRR、Recall@K、NDCG@K、查询延迟。
- RAGAs 端到端评估：忠实性、答案相关性、上下文精确率、上下文召回率。
- 检索策略消融实验：混合检索、重排序、双语翻译、Self-RAG。
- 系统自动化测试：后端单元测试、集成测试、前端组件测试、压力测试。

根据论文记录，`BAAI/bge-m3` 在中英文混合眼科知识库场景中表现较好，适合作为生产环境嵌入模型。

## 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd RAG
```

### 2. 启动基础设施

`docker-compose.yml` 会启动 MySQL 和 ChromaDB：

```bash
docker-compose up -d
```

默认端口：

- MySQL：`localhost:3316`
- ChromaDB：`localhost:8011`

如果只想本地开发，也可以不设置 `CHROMA_HOST`，后端会使用 `backend/chroma_db` 本地持久化模式。

### 3. 配置后端环境变量

```bash
cd backend
cp .env.example .env
```

根据实际情况修改 `.env`：

```env
DEBUG=true
DATABASE_URL=sqlite+aiosqlite:///./data/ophtha_qa.db

JWT_SECRET_KEY=please-change-this-secret

LLM_PROVIDER=deepseek
LLM_API_KEY=your-deepseek-api-key
LLM_API_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL_NAME=deepseek-chat

# 如使用 Docker ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8011
CHROMA_COLLECTION_NAME=ophthalmology_docs

# 推荐生产模型示例，本地需准备对应模型文件或允许在线下载
EMBEDDING_MODEL_NAME=BAAI/bge-m3
EMBEDDING_MODEL_PATH=./model/bge-m3
```

如使用 MySQL，可将数据库连接改为：

```env
DATABASE_URL=mysql+aiomysql://eyerag:eyerag123@localhost:3316/eyerag
```

### 4. 启动后端

建议使用 Python 3.9+：

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端启动后可访问：

- API 健康检查：`http://localhost:8000/api/health`
- Swagger 文档：`http://localhost:8000/docs`
- ReDoc 文档：`http://localhost:8000/redoc`

### 5. 构建知识库

将文档放入 `backend/data/documents/`，支持 `.pdf`、`.txt`、`.md`、`.markdown`：

```bash
cd backend
python scripts/ingest.py --dir data/documents --chunk-size 512 --overlap 50
```

也可以启动系统后通过 Web 管理端上传文档，系统会自动解析、分块、向量化并写入 ChromaDB。

### 6. 启动 Vue Web 端

```bash
cd frontend
npm install
npm run dev
```

默认访问：

```text
http://localhost:5173
```

### 7. 启动 Flutter 端

```bash
cd frontend_flutter
flutter pub get
flutter run
```

移动端调试时，请确认后端 API 地址指向当前开发机器。模拟器、真机和 Web 平台对 `localhost` 的解析方式不同，必要时需要改为局域网 IP。

## 常用命令

### 后端

```bash
cd backend

# 启动开发服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 批量导入知识库
python scripts/ingest.py --dir data/documents

# 运行非 LLM 自动化测试
pip install -r requirements-test.txt
pytest

# 生成测试报告和覆盖率
python scripts/run_tests.py --coverage

# 运行 Locust 压力测试
locust -f tests/stress/locustfile.py
```

### Web 前端

```bash
cd frontend

npm run dev
npm run build
npm run test
npm run test:coverage
```

### Flutter 前端

```bash
cd frontend_flutter

flutter pub get
flutter analyze
flutter test
flutter run
```

## API 概览

所有业务接口默认以 `/api` 为前缀。

| 模块 | 主要接口 |
| --- | --- |
| 健康检查 | `GET /api/health` |
| 认证 | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| 问答 | `POST /api/chat/completions`, `POST /api/chat/messages` |
| 会话 | `GET /api/chat/conversations`, `GET /api/chat/conversations/{id}`, `PATCH /api/chat/conversations/{id}/title`, `DELETE /api/chat/conversations/{id}` |
| 知识库 | `GET /api/knowledge/stats`, `GET /api/knowledge/documents`, `POST /api/knowledge/upload`, `POST /api/knowledge/search`, `DELETE /api/knowledge/documents/{file_name}` |
| 收藏 | `GET /api/favorites`, `POST /api/favorites`, `DELETE /api/favorites/{id}` |
| 反馈 | `POST /api/feedback` |
| 历史 | `GET /api/search-history` |
| 统计 | `GET /api/stats/*` |
| 管理 | `GET /api/admin/*`, `PATCH /api/admin/*` |

详细字段以 FastAPI 自动生成的 `http://localhost:8000/docs` 为准。

## 环境变量说明

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `APP_NAME` | 应用名称 | `眼科医疗知识问答系统` |
| `DEBUG` | 是否开启调试模式 | `true` |
| `DATABASE_URL` | SQLAlchemy 数据库连接 | `sqlite+aiosqlite:///./data/ophtha_qa.db` |
| `JWT_SECRET_KEY` | JWT 签名密钥，生产环境必须修改 | `dev-secret-key-change-in-production` |
| `LLM_PROVIDER` | LLM 提供方，支持 `deepseek` / `minimax` | `deepseek` |
| `LLM_API_KEY` | DeepSeek API Key | 空 |
| `LLM_API_BASE_URL` | DeepSeek 兼容 API 地址 | `https://api.deepseek.com/v1` |
| `LLM_MODEL_NAME` | DeepSeek 模型名 | `deepseek-chat` |
| `MINIMAX_API_KEY` | MiniMax API Key | 空 |
| `MINIMAX_API_BASE_URL` | MiniMax Anthropic 兼容 API 地址 | `https://api.minimaxi.com/anthropic` |
| `MINIMAX_MODEL_NAME` | MiniMax 模型名 | `MiniMax-M2.7` |
| `EMBEDDING_MODEL_NAME` | SentenceTransformers 模型名 | `sentence-transformers/all-MiniLM-L6-v2` |
| `EMBEDDING_MODEL_PATH` | 本地嵌入模型路径，设置后优先使用 | 空 |
| `CHROMA_HOST` | ChromaDB HTTP Host；为空时使用本地持久化模式 | 空 |
| `CHROMA_PORT` | ChromaDB HTTP 端口 | `8011` |
| `CHROMA_PERSIST_DIR` | 本地 ChromaDB 持久化目录 | `./chroma_db` |
| `CHROMA_COLLECTION_NAME` | ChromaDB Collection 名称 | `ophthalmology_docs` |
| `CHUNK_SIZE` | 文本块大小 | `512` |
| `CHUNK_OVERLAP` | 文本块重叠字符数 | `50` |
| `RETRIEVAL_TOP_K` | 默认检索 Top-K | `5` |

## GitHub 上传注意事项

本仓库根目录已提供 `.gitignore`。建议上传 GitHub 前重点确认以下内容不会进入版本库：

- `.env`、API Key、JWT 密钥等敏感配置。
- `frontend/node_modules/`、`frontend/dist/`、`frontend/coverage/`。
- `frontend_flutter/.dart_tool/`、`frontend_flutter/build/`、平台构建产物。
- `backend/venv/`、`__pycache__/`、`.pytest_cache/`、覆盖率报告。
- `backend/chroma_db*/` 向量库目录。
- `backend/data/*.db`、SQLite 数据库、爬虫调试 HTML、checkpoint、RAGAs 原始结果。
- `backend/model/` 大模型权重。
- `backend/wandb/`、`backend/logs/`、测试报告。
- `.har` 抓包文件，可能包含 Cookie 或登录态。

如果需要公开知识库原始文档，请确认文档来源、版权许可和隐私风险。医学网站爬取数据尤其建议只保留说明文档或少量样例，不直接公开完整爬取结果。

### 发布到 GitHub 示例

当前项目目录如果还不是 Git 仓库，可以按下面流程初始化并推送：

```bash
git init
git add README.md .gitignore docker-compose.yml backend frontend frontend_flutter "毕业论文/thesis"
git status
git commit -m "Initial commit"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

如果你还想上传根目录下的其他论文资料或项目报告，可以在确认不含隐私、密钥和大文件后再单独 `git add`。若某些大文件曾经被加入暂存区，可用 `git reset <file>` 取消暂存；如果已经提交过，则需要用 `git rm --cached <file>` 从版本跟踪中移除。

## 目录结构

```text
.
├── backend/                 # FastAPI 后端与 RAG 管线
│   ├── app/
│   │   ├── api/             # REST / SSE API
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── rag/             # 检索、生成、向量库、Self-RAG
│   │   ├── schemas/         # Pydantic Schema
│   │   ├── services/        # 认证等业务服务
│   │   └── utils/           # 日志等工具
│   ├── scripts/             # 数据采集、入库、评估脚本
│   ├── tests/               # 单元、集成、压力测试
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # Vue3 Web 端
│   ├── src/
│   │   ├── api/
│   │   ├── router/
│   │   ├── stores/
│   │   └── views/
│   ├── package.json
│   └── vite.config.js
├── frontend_flutter/        # Flutter 移动端
│   ├── lib/
│   │   ├── models/
│   │   ├── providers/
│   │   └── services/
│   └── pubspec.yaml
├── 毕业论文/thesis/          # 论文正文、设计、实验和测试文档
├── docker-compose.yml       # MySQL + ChromaDB 基础设施
├── README.md
└── .gitignore
```

## 免责声明

本系统仅用于毕业设计、RAG 工程实践和眼科健康知识科普场景。生成内容仅供参考，不能替代专业眼科医生的诊断和治疗建议。如出现视力急剧下降、眼部剧痛、外伤、眼前黑影突然增多等紧急情况，请立即前往正规医院眼科就诊。
