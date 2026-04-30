# EyeRAG: 基于 RAG 的眼科医疗知识问答系统

EyeRAG 是一个面向眼科医疗知识场景的检索增强生成（Retrieval-Augmented Generation, RAG）问答系统，来自本科毕业论文《基于 RAG 的眼科医疗知识问答系统设计与实现》。项目围绕眼科专业文献、临床指南、英文百科和中文医学百科构建知识库，提供 FastAPI 后端、Vue3 Web 管理端和 Flutter 跨平台移动端。

系统的核心目标是让用户通过自然语言获得有来源引用、可追溯、可管理的眼科知识回答。它不是医疗诊断工具，也不能替代专业眼科医生，而是一个用于医学知识科普、RAG 工程实践和毕业设计展示的完整系统。

## 项目亮点

- **完整自研 RAG 管线**：不依赖 LangChain 等编排框架，独立实现文档加载、递归分块、嵌入向量化、检索融合、重排序、Prompt 构建、LLM 调用和流式输出。
- **混合检索策略**：同时使用 ChromaDB 向量检索和 BM25 关键词检索，并通过 RRF（Reciprocal Rank Fusion）融合排序，兼顾语义召回与精确术语匹配。
- **Self-RAG 自判断机制**：生成前由 LLM 评估检索结果相关性和充分性，自动选择 `proceed`、`retry` 或 `fallback`，降低低质量上下文导致的幻觉风险。
- **中英文混合知识库优化**：针对中文问题进行轻量英文翻译，并在向量检索和 BM25 检索两条路径上进行双路补偿，提升英文文献命中率。
- **医疗安全检查层**：对直接诊断、具体用药剂量、绝对化疗效承诺等风险表达进行规则检测，并追加安全提醒。
- **SSE 流式问答体验**：后端通过 Server-Sent Events 实时推送答案片段、参考来源、检索决策和相关问题，前端逐字渲染。
- **多端客户端**：Vue3 Web 端用于桌面问答和后台管理，Flutter 端用于移动场景，两端复用同一套后端 API。
- **可复现实验体系**：包含嵌入模型基准评测、RAGAs 端到端评估、消融实验、单元测试、集成测试和压力测试。

## 架构概览

```mermaid
flowchart LR
    User["普通用户 / 管理员"] --> Web["Vue3 Web 端"]
    User --> Mobile["Flutter 移动端"]

    Web -->|"HTTP / SSE"| API["FastAPI API 层"]
    Mobile -->|"HTTP / SSE"| API

    API --> Auth["认证 / 会话 / 收藏 / 反馈 / 统计"]
    API --> RAG["RAG 业务层"]

    Auth --> SQL["SQLite / MySQL"]
    RAG --> Vec["ChromaDB 向量库"]
    RAG --> BM25["BM25 内存索引"]
    RAG --> LLM["DeepSeek / MiniMax"]

    Corpus["眼科知识文档"] --> Ingest["解析 / 分块 / 向量化"]
    Ingest --> Vec
```

RAG 处理链路：

```mermaid
flowchart TD
    Q["用户问题"] --> T["中文问题英文翻译补偿"]
    T --> HR["混合检索: 向量 + BM25"]
    HR --> RRF["RRF 融合"]
    RRF --> ReRank["关键词 / CrossEncoder 重排序"]
    ReRank --> Eval["Self-RAG 检索质量评估"]
    Eval -->|"proceed"| Prompt["构建增强 Prompt"]
    Eval -->|"retry"| Retry["优化查询后二次检索"]
    Eval -->|"fallback"| Fallback["无参考资料降级回答"]
    Retry --> Prompt
    Prompt --> Gen["LLM 流式生成"]
    Fallback --> Gen
    Gen --> Safe["医疗安全检查"]
    Safe --> SSE["SSE 返回答案与来源"]
```

## 仓库结构

```text
.
├── backend/                 # FastAPI 后端与 RAG 核心
│   ├── app/
│   │   ├── api/             # 路由层：认证、聊天、知识库、管理等接口
│   │   ├── models/          # SQLAlchemy ORM 数据模型
│   │   ├── rag/             # RAG 管线、检索、向量库、LLM、安全检查
│   │   ├── schemas/         # Pydantic 请求/响应模型
│   │   ├── services/        # 认证等业务服务
│   │   └── utils/           # 日志等工具
│   ├── scripts/             # 数据采集、入库、评测、测试脚本
│   ├── tests/               # 单元测试、集成测试、压力测试
│   ├── requirements.txt
│   └── README.md
├── frontend/                # Vue3 Web 端
│   ├── src/
│   ├── package.json
│   └── README.md
├── frontend_flutter/        # Flutter 跨平台移动端
│   ├── lib/
│   ├── pubspec.yaml
│   └── README.md
├── 毕业论文/thesis/          # 论文正文、实验、测试与设计文档
├── docker-compose.yml       # MySQL + ChromaDB 基础设施
├── .gitignore
└── README.md
```

## 功能模块

### 普通用户

- 用户注册、登录、JWT 鉴权。
- 眼科自然语言问答，支持流式输出。
- 多轮对话，会话上下文保留最近 10 条消息。
- 查看参考来源、相似度分数和检索决策。
- 检索历史回顾，查看完整问题、答案、来源与检索片段。
- 收藏问答、取消收藏、继续追问。
- 对回答提交有用/无用反馈。

### 管理员

- 上传 PDF、TXT、Markdown 文档并自动解析入库。
- 查看知识库文档列表、文本块数量、浏览次数和命中次数。
- 预览、下载、删除知识库文档。
- 使用检索测试接口调试召回效果。
- 查看系统统计看板、反馈趋势、热门查询和响应耗时。
- 管理用户账号，支持启用、禁用、删除。
- 在管理后台切换 LLM Provider 和部分运行配置。

### 移动端能力

- Flutter Material 3 界面。
- 语音输入。
- 生物识别登录。
- 收藏离线缓存。
- Markdown 答案渲染。
- 截图分享。
- iOS、Android、Web、macOS、Windows、Linux 工程骨架。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 后端 API | FastAPI, Uvicorn, Pydantic v2 |
| 数据库 | SQLAlchemy Async, SQLite, MySQL 8 |
| 认证 | JWT, bcrypt, passlib, python-jose |
| 向量数据库 | ChromaDB |
| 文档处理 | PyPDF2, Markdown/TXT Loader, Recursive Character Splitter |
| 嵌入模型 | SentenceTransformers, BAAI/bge-m3, BGE-ZH, text2vec, MiniLM |
| 检索算法 | Dense Retrieval, BM25, RRF, Keyword Reranker, CrossEncoder 可选 |
| LLM | DeepSeek OpenAI-compatible API, MiniMax Anthropic-compatible API |
| Web 前端 | Vue3, Vite, Element Plus, Pinia, Vue Router, Axios, ECharts |
| 移动端 | Flutter 3, Riverpod, go_router, Dio, sqflite, local_auth, speech_to_text |
| 测试 | pytest, pytest-asyncio, pytest-cov, Vitest, Locust |
| 部署 | Docker Compose, MySQL, ChromaDB |

## 知识库与实验

论文实验使用的知识库覆盖多个眼科数据来源：

| 来源 | 语言 | 内容 |
| --- | --- | --- |
| PubMed Central | 英文 | 眼科综述文献，覆盖青光眼、白内障、AMD、糖尿病视网膜病变等 |
| NICE / AAO | 英文 | 临床指南与实践模式文档 |
| Wikipedia | 英文 | 眼科基础概念、检查技术、药物、手术和疾病词条 |
| 丁香园 | 中文 | 眼科疾病百科 |
| 寻医问药网 | 中文 | 眼科疾病概述、病因、症状、检查、治疗和预防 |

文档经递归字符分块后形成约 28,000 个向量文本块。论文中的实验体系包括：

- 嵌入模型基准评测：MRR、Recall@K、NDCG@K、查询延迟。
- RAGAs 端到端评估：忠实性、答案相关性、上下文精确率、上下文召回率。
- 消融实验：混合检索、重排序、双语翻译、Self-RAG。
- 系统测试：后端单元测试、集成测试、前端组件测试、压力测试。

根据论文记录，`BAAI/bge-m3` 在中英文混合眼科知识库场景下整体表现较好，适合作为生产环境嵌入模型。

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/org666233/EyeRAG.git
cd EyeRAG
```

### 2. 启动基础设施

项目根目录提供 `docker-compose.yml`，用于启动 MySQL 和 ChromaDB：

```bash
docker-compose up -d
```

默认端口：

- MySQL: `localhost:3316`
- ChromaDB: `localhost:8011`

### 3. 配置后端

```bash
cd backend
cp .env.example .env
```

开发环境可先使用 SQLite：

```env
DATABASE_URL=sqlite+aiosqlite:///./data/ophtha_qa.db
JWT_SECRET_KEY=please-change-this-secret

LLM_PROVIDER=deepseek
LLM_API_KEY=your-deepseek-api-key
LLM_API_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL_NAME=deepseek-chat

CHROMA_HOST=localhost
CHROMA_PORT=8011
CHROMA_COLLECTION_NAME=ophthalmology_docs
```

如需使用 Docker 中的 MySQL：

```env
DATABASE_URL=mysql+aiomysql://eyerag:eyerag123@localhost:3316/eyerag
```

### 4. 启动后端

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问：

- 健康检查：`http://localhost:8000/api/health`
- Swagger：`http://localhost:8000/docs`
- ReDoc：`http://localhost:8000/redoc`

### 5. 构建知识库

将文档放入 `backend/data/documents/` 后执行：

```bash
cd backend
python scripts/ingest.py --dir data/documents --chunk-size 512 --overlap 50
```

也可以登录 Web 管理端，通过知识库管理页面上传文档。

### 6. 启动 Web 端

```bash
cd frontend
npm install
npm run dev
```

访问：

```text
http://localhost:5173
```

Vue 开发服务器会将 `/api` 代理到 `http://localhost:8000`。

### 7. 启动 Flutter 端

```bash
cd frontend_flutter
flutter pub get
flutter run
```

真机调试时，后端地址不要使用模拟器无法访问的 `localhost`，需要在 Flutter 配置中改为电脑局域网 IP。

## 常用命令

### 后端

```bash
cd backend

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 导入知识库
python scripts/ingest.py --dir data/documents

# 运行测试
pip install -r requirements-test.txt
pytest

# 生成覆盖率与测试报告
python scripts/run_tests.py --coverage

# 运行压力测试，需要先启动后端
locust -f tests/stress/locustfile.py
```

### Vue Web 端

```bash
cd frontend

npm install
npm run dev
npm run build
npm run test
npm run test:coverage
```

### Flutter 端

```bash
cd frontend_flutter

flutter pub get
flutter analyze
flutter test
flutter run
```

## API 概览

所有接口默认以 `/api` 为前缀：

| 模块 | 接口 |
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

接口字段以 `http://localhost:8000/docs` 自动生成文档为准。

## 环境变量

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `APP_NAME` | 应用名称 | `眼科医疗知识问答系统` |
| `APP_VERSION` | 应用版本 | `1.0.0` |
| `DEBUG` | 调试模式 | `true` |
| `DATABASE_URL` | 关系数据库连接 | `sqlite+aiosqlite:///./data/ophtha_qa.db` |
| `JWT_SECRET_KEY` | JWT 签名密钥，生产必须修改 | `dev-secret-key-change-in-production` |
| `LLM_PROVIDER` | LLM 提供方，支持 `deepseek` / `minimax` | `deepseek` |
| `LLM_API_KEY` | DeepSeek API Key | 空 |
| `LLM_API_BASE_URL` | DeepSeek API 地址 | `https://api.deepseek.com/v1` |
| `LLM_MODEL_NAME` | DeepSeek 模型名 | `deepseek-chat` |
| `MINIMAX_API_KEY` | MiniMax API Key | 空 |
| `MINIMAX_API_BASE_URL` | MiniMax API 地址 | `https://api.minimaxi.com/anthropic` |
| `MINIMAX_MODEL_NAME` | MiniMax 模型名 | `MiniMax-M2.7` |
| `EMBEDDING_MODEL_NAME` | SentenceTransformer 模型名 | `sentence-transformers/all-MiniLM-L6-v2` |
| `EMBEDDING_MODEL_PATH` | 本地嵌入模型路径 | 空 |
| `USE_BIOBERT` | 是否启用 BioBERT 配置 | `false` |
| `CHROMA_HOST` | ChromaDB HTTP Host，为空则本地持久化 | 空 |
| `CHROMA_PORT` | ChromaDB HTTP 端口 | `8011` |
| `CHROMA_PERSIST_DIR` | 本地 ChromaDB 目录 | `./chroma_db` |
| `CHROMA_COLLECTION_NAME` | Collection 名称 | `ophthalmology_docs` |
| `CHUNK_SIZE` | 文本块大小 | `512` |
| `CHUNK_OVERLAP` | 文本块重叠 | `50` |
| `RETRIEVAL_TOP_K` | 默认召回数量 | `5` |

## GitHub 上传建议

本仓库已提供根目录 `.gitignore`。上传前请确认以下内容没有进入版本库：

- `.env`、API Key、JWT 密钥。
- `node_modules/`、`dist/`、`coverage/`。
- Python 虚拟环境、`__pycache__/`、`.pytest_cache/`。
- ChromaDB 向量库：`backend/chroma_db*/`。
- SQLite 数据库：`backend/data/*.db`。
- 本地模型权重：`backend/model/`、`.bin`、`.safetensors`。
- 日志、W&B 运行记录、测试报告。
- HAR 抓包文件，可能包含 Cookie 或登录态。
- 未确认版权和隐私风险的完整爬虫数据。

如果远端仓库创建时勾选了 `LICENSE` 或初始 README，本地首次推送前可执行：

```bash
git pull origin main --allow-unrelated-histories --no-rebase
git push -u origin main
```

如果出现冲突，先解决冲突后再提交和推送。

## 子项目文档

- [backend/README.md](backend/README.md)：后端服务、RAG 管线、环境变量、数据入库和测试说明。
- [frontend/README.md](frontend/README.md)：Vue3 Web 端页面、API 封装、开发构建和测试说明。
- [frontend_flutter/README.md](frontend_flutter/README.md)：Flutter 移动端架构、运行配置、平台注意事项和开发说明。

## 免责声明

本系统仅用于毕业设计、RAG 工程实践和眼科健康知识科普。生成内容仅供参考，不能替代专业眼科医生的诊断和治疗建议。如出现视力急剧下降、眼部剧痛、外伤、眼前黑影突然增多等紧急情况，请立即前往正规医院眼科就诊。

