# EyeRAG Backend

`backend/` 是 EyeRAG 项目的后端服务与 RAG 核心实现，基于 FastAPI 构建，负责用户认证、会话管理、知识库管理、流式问答、统计分析和 RAG 检索生成流程。

本后端重点强调可解释、可替换和可评估：RAG 管线没有依赖 LangChain 等高层编排框架，而是直接实现文档解析、文本分块、向量存储、混合检索、重排序、Self-RAG 决策、Prompt 构建、LLM 调用和医疗安全检查。

## 目录结构

```text
backend/
├── app/
│   ├── api/                 # FastAPI 路由
│   │   ├── auth.py          # 注册、登录、当前用户
│   │   ├── chat.py          # SSE 问答、会话、消息保存
│   │   ├── knowledge.py     # 文档上传、入库、检索、预览、删除
│   │   ├── favorites.py     # 收藏
│   │   ├── feedback.py      # 用户反馈
│   │   ├── search_history.py# 检索历史
│   │   ├── stats.py         # 数据看板
│   │   ├── admin.py         # 管理后台
│   │   └── router.py        # 路由聚合
│   ├── models/              # SQLAlchemy ORM 模型
│   ├── rag/                 # RAG 核心
│   │   ├── document_loader.py
│   │   ├── text_splitter.py
│   │   ├── embeddings.py
│   │   ├── vector_store.py
│   │   ├── hybrid_retrieval.py
│   │   ├── reranker.py
│   │   ├── prompts.py
│   │   ├── llm_client.py
│   │   ├── pipeline.py
│   │   ├── self_rag.py
│   │   └── safety_checker.py
│   ├── schemas/             # Pydantic 请求/响应模型
│   ├── services/            # 认证服务等业务逻辑
│   ├── utils/               # 日志工具
│   ├── config.py            # 环境变量配置
│   ├── database.py          # 异步数据库连接
│   └── main.py              # FastAPI 入口
├── scripts/                 # 数据采集、入库、评测、测试脚本
├── tests/                   # 单元测试、集成测试、压力测试
├── requirements.txt
├── requirements-test.txt
├── pytest.ini
└── Dockerfile
```

## 核心职责

### API 服务

后端对外提供 RESTful API 和 SSE 流式接口：

- `/api/auth/*`：注册、登录、获取当前用户。
- `/api/chat/completions`：核心问答接口，支持 `stream=true` 的 SSE 流式输出。
- `/api/chat/messages`：流式回答完成后显式保存消息，避免流式接口重复写入。
- `/api/chat/conversations/*`：会话列表、会话详情、标题修改、删除。
- `/api/knowledge/*`：知识库统计、文档列表、上传、预览、下载、删除、检索测试。
- `/api/favorites/*`：收藏管理。
- `/api/feedback/*`：用户反馈。
- `/api/search-history/*`：检索历史。
- `/api/stats/*`：系统统计。
- `/api/admin/*`：用户和系统配置管理。

### RAG 管线

主要实现位于 `app/rag/`：

1. `DocumentLoader` 加载 PDF、TXT、Markdown 文档。
2. `RecursiveCharacterTextSplitter` 按章节、段落、句子等分隔符递归切分文本。
3. `embeddings.py` 加载 SentenceTransformer 或本地 BERT 类模型并生成向量。
4. `vector_store.py` 封装 ChromaDB，本地持久化和 HTTP Server 两种模式都支持。
5. `hybrid_retrieval.py` 同时执行向量检索和 BM25 检索，并用 RRF 融合排序。
6. `reranker.py` 对候选文档进行关键词重排序，可扩展 CrossEncoder。
7. `self_rag.py` 使用 LLM 评估检索质量，选择直接生成、二次检索或降级回答。
8. `prompts.py` 构建眼科场景专用 Prompt。
9. `llm_client.py` 统一封装 DeepSeek 和 MiniMax 调用，并处理重试。
10. `safety_checker.py` 对医疗风险表达追加安全提示。

### 数据持久化

后端使用两类数据库：

- **关系数据库**：SQLite 或 MySQL，存储用户、会话、消息、收藏、反馈、检索历史、文档统计等结构化数据。
- **向量数据库**：ChromaDB，存储文档块、嵌入向量和来源元数据。

开发环境默认使用 SQLite：

```env
DATABASE_URL=sqlite+aiosqlite:///./data/ophtha_qa.db
```

生产或演示环境可切换到 MySQL：

```env
DATABASE_URL=mysql+aiomysql://eyerag:eyerag123@localhost:3316/eyerag
```

## 环境准备

建议环境：

- Python 3.9+
- Docker / Docker Compose，可选，用于启动 MySQL 和 ChromaDB
- 可访问的 LLM API Key，如 DeepSeek 或 MiniMax
- 足够磁盘空间用于本地模型和 ChromaDB 向量库

创建虚拟环境并安装依赖：

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

测试依赖：

```bash
pip install -r requirements-test.txt
```

## 配置说明

复制配置模板：

```bash
cp .env.example .env
```

常用配置：

```env
APP_NAME="眼科医疗知识问答系统"
APP_VERSION="1.0.0"
DEBUG=true

DATABASE_URL=sqlite+aiosqlite:///./data/ophtha_qa.db

JWT_SECRET_KEY=please-change-this-secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

LLM_PROVIDER=deepseek
LLM_API_KEY=your-deepseek-api-key
LLM_API_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL_NAME=deepseek-chat

MINIMAX_API_KEY=your-minimax-api-key
MINIMAX_API_BASE_URL=https://api.minimaxi.com/anthropic
MINIMAX_MODEL_NAME=MiniMax-M2.7

EMBEDDING_MODEL_NAME=BAAI/bge-m3
EMBEDDING_MODEL_PATH=./model/bge-m3
USE_BIOBERT=false

CHROMA_HOST=localhost
CHROMA_PORT=8011
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION_NAME=ophthalmology_docs

CHUNK_SIZE=512
CHUNK_OVERLAP=50
RETRIEVAL_TOP_K=5
```

ChromaDB 有两种使用方式：

- 设置 `CHROMA_HOST=localhost`：连接 Docker 中的 ChromaDB HTTP 服务。
- 不设置 `CHROMA_HOST`：使用本地 `PersistentClient`，数据存储在 `CHROMA_PERSIST_DIR`。

## 启动服务

如果使用 Docker 基础设施，先在项目根目录启动：

```bash
docker-compose up -d
```

然后启动后端：

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问：

- 健康检查：`http://localhost:8000/api/health`
- Swagger 文档：`http://localhost:8000/docs`
- ReDoc 文档：`http://localhost:8000/redoc`

应用启动时会自动创建数据目录和关系数据库表：

- `data/`
- `logs/`
- `chroma_db/`
- `data/documents/`

## 知识库入库

支持文档类型：

- `.pdf`
- `.txt`
- `.md`
- `.markdown`

将文档放入 `data/documents/` 后执行：

```bash
python scripts/ingest.py --dir data/documents --chunk-size 512 --overlap 50
```

脚本会完成：

1. 递归读取目录中的支持文档。
2. 解析文本和元数据。
3. 按 `CHUNK_SIZE` 与 `CHUNK_OVERLAP` 切分文本。
4. 调用嵌入模型生成向量。
5. 写入 ChromaDB Collection。

也可以通过 Web 管理端上传文档，后端接口会同步执行解析、分块和入库。

## 多模型入库与评测

`scripts/ingest.py` 内置了多个候选模型配置，例如：

- `sentence-transformers/all-MiniLM-L6-v2`
- `BAAI/bge-base-zh-v1.5`
- `BAAI/bge-large-zh-v1.5`
- `BAAI/bge-m3`
- `shibing624/text2vec-base-chinese`
- `sentence-transformers/gtr-t5-xl`

相关评测脚本：

```bash
python scripts/benchmark_embeddings.py
python scripts/evaluate.py
python scripts/evaluate_ragas.py
python scripts/eval_vector_store.py
```

这些脚本用于复现论文中的模型检索性能对比、RAGAs 端到端评估和向量库质量分析。部分脚本需要 LLM API Key、完整知识库和本地模型文件。

## 测试

运行全部非 LLM 测试：

```bash
pytest
```

使用项目测试脚本：

```bash
python scripts/run_tests.py
```

常用选项：

```bash
python scripts/run_tests.py --unit-only
python scripts/run_tests.py --integration-only
python scripts/run_tests.py --with-llm
python scripts/run_tests.py --coverage
python scripts/run_tests.py --stress
```

测试目录：

```text
tests/
├── unit/                    # 配置、认证、BM25、重排序、安全检查、Prompt
├── integration/             # 认证 API、聊天 API、会话 API、知识库 API
└── stress/                  # Locust 压力测试
```

压力测试需要后端服务已经启动：

```bash
locust -f tests/stress/locustfile.py --host http://localhost:8000
```

## 日志与运行产物

常见运行产物：

- `logs/`：应用日志和评测日志。
- `data/*.db`：SQLite 数据库。
- `chroma_db*/`：ChromaDB 本地向量库。
- `wandb/`：实验记录。
- `test_reports/`：测试报告。
- `model/`：本地嵌入模型权重。

这些内容通常不应上传 GitHub，根目录 `.gitignore` 已做过滤。

## 开发注意事项

- 生产环境必须修改 `JWT_SECRET_KEY`。
- `.env` 不要提交到 GitHub。
- LLM API Key 不要写死在源码中。
- 如果使用本地模型路径，确保 `EMBEDDING_MODEL_PATH` 与模型维度对应的 ChromaDB Collection 一致。
- 切换嵌入模型后需要重新入库，否则查询向量维度可能与旧 Collection 不匹配。
- ChromaDB HTTP 模式下，确保 `CHROMA_HOST` 和 `CHROMA_PORT` 指向正确服务。
- 医疗问答结果仅供参考，不能作为诊断或处方依据。

