# EyeRAG Frontend Web

`frontend/` 是 EyeRAG 的 Vue3 Web 客户端，面向桌面浏览器使用，提供智能问答、会话管理、知识库管理、检索历史、收藏、数据看板和管理后台等功能。

Web 端定位为系统的主操作界面：普通用户在这里进行眼科知识问答，管理员在这里维护知识库、查看统计数据并管理用户。

## 技术栈

| 类别 | 技术 |
| --- | --- |
| 框架 | Vue 3 |
| 构建工具 | Vite |
| UI 组件 | Element Plus, @element-plus/icons-vue |
| 路由 | Vue Router |
| 状态管理 | Pinia |
| HTTP 客户端 | Axios |
| 图表 | ECharts, vue-echarts |
| Markdown | markdown-it, highlight.js |
| 测试 | Vitest, Vue Test Utils, jsdom |

## 目录结构

```text
frontend/
├── src/
│   ├── api/                 # 后端 API 封装
│   │   ├── auth.js
│   │   ├── chat.js
│   │   ├── knowledge.js
│   │   ├── favorites.js
│   │   ├── feedback.js
│   │   ├── searchHistory.js
│   │   └── stats.js
│   ├── router/
│   │   └── index.js         # 路由与鉴权守卫
│   ├── stores/              # Pinia store
│   ├── styles/
│   │   └── index.css        # 全局样式
│   ├── utils/
│   │   └── request.js       # Axios 实例、Token 注入、错误处理
│   ├── views/
│   │   ├── LoginView.vue
│   │   ├── ChatView.vue
│   │   ├── KnowledgeView.vue
│   │   ├── HistoryView.vue
│   │   ├── FavoritesView.vue
│   │   ├── StatsView.vue
│   │   ├── AdminView.vue
│   │   └── SystemView.vue
│   ├── App.vue
│   └── main.js
├── tests/                   # Vitest 组件测试
├── public/
├── package.json
├── vite.config.js
├── vitest.config.js
├── nginx.conf
└── Dockerfile
```

## 页面说明

### `LoginView.vue`

认证入口，提供登录和注册表单。登录成功后保存 JWT Token 和用户信息，路由跳转到问答页。

### `ChatView.vue`

核心问答页面，包含：

- 会话列表。
- 新建会话和会话切换。
- 用户消息和 AI 消息气泡。
- SSE 流式答案渲染。
- Markdown 渲染和代码高亮。
- 参考来源展示。
- `proceed` / `retry` / `fallback` 检索决策标签。
- 相关问题推荐。
- 消息收藏和反馈。
- 流式结束后调用 `/api/chat/messages` 显式保存消息。

### `KnowledgeView.vue`

知识库管理页面，面向管理员或具备权限的用户：

- 查看 ChromaDB Collection 统计。
- 查看文档列表、文本块数量、命中次数和浏览次数。
- 上传 PDF、TXT、Markdown 文档。
- 文档预览、下载、删除。
- 检索测试。

### `HistoryView.vue`

检索历史页面：

- 按时间查看历史问答。
- 查看问题、答案、检索决策、来源和检索片段。
- 支持筛选、详情弹窗、删除等操作。

### `FavoritesView.vue`

收藏回顾页面：

- 查看收藏问答。
- 搜索收藏。
- 复制内容。
- 继续追问。
- 取消收藏。

### `StatsView.vue`

系统数据看板：

- 问答数量。
- 满意率。
- 检索决策分布。
- 反馈趋势。
- 响应耗时。
- 热门查询。

### `AdminView.vue`

管理后台：

- 用户列表。
- 用户角色和状态管理。
- 启用、禁用、删除用户。
- 运行配置管理。

### `SystemView.vue`

系统介绍页，用于展示项目架构、RAG 流程和系统说明。

## 后端通信

Axios 封装位于 `src/utils/request.js`：

- `baseURL` 固定为 `/api`。
- 请求拦截器自动附加 `Authorization: Bearer <token>`。
- 响应拦截器统一处理 `401`、`403`、`422` 和普通错误。
- `401` 时清除本地认证信息并跳转登录页。

开发环境代理在 `vite.config.js` 中配置：

```js
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

因此开发时前端请求 `/api/chat/completions` 会被代理到 `http://localhost:8000/api/chat/completions`。

## 路由与权限

路由配置位于 `src/router/index.js`。

主要路由：

| 路径 | 页面 | 权限 |
| --- | --- | --- |
| `/login` | 登录/注册 | 公开 |
| `/chat` | 智能问答 | 登录 |
| `/knowledge` | 知识库管理 | 登录 |
| `/favorites` | 我的收藏 | 登录 |
| `/history` | 检索历史 | 登录 |
| `/stats` | 数据看板 | 登录 |
| `/admin` | 管理后台 | 管理员 |
| `/system` | 系统介绍 | 登录 |

路由守卫会检查：

- 未登录访问受保护页面时跳转 `/login`。
- 非管理员访问 `/admin` 时跳转 `/chat`。
- 已登录用户访问 `/login` 时跳转 `/chat`。

## 开发环境

建议环境：

- Node.js `^20.19.0 || >=22.12.0`
- npm
- 后端服务运行在 `http://localhost:8000`

安装依赖：

```bash
cd frontend
npm install
```

启动开发服务器：

```bash
npm run dev
```

默认访问：

```text
http://localhost:5173
```

## 构建与预览

生产构建：

```bash
npm run build
```

构建产物输出到：

```text
dist/
```

本地预览：

```bash
npm run preview
```

## 测试

运行组件测试：

```bash
npm run test
```

监听模式：

```bash
npm run test:watch
```

覆盖率：

```bash
npm run test:coverage
```

CI JSON 输出：

```bash
npm run test:ci
```

当前测试覆盖：

- `LoginView`：登录/注册模式切换、表单提交、成功/失败流程。
- `KnowledgeView`：页面渲染、搜索、上传回调、删除、预览、对话框状态。

## 与后端联调

启动顺序建议：

1. 在项目根目录启动基础设施：

```bash
docker-compose up -d
```

2. 启动后端：

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

3. 启动前端：

```bash
cd frontend
npm run dev
```

4. 打开浏览器：

```text
http://localhost:5173
```

如果接口报错，先检查：

- 后端是否运行在 `localhost:8000`。
- `.env` 中 LLM API Key 是否配置。
- ChromaDB 是否可连接。
- 浏览器 Network 面板中请求是否进入 `/api` 代理。
- 登录后 localStorage 中是否存在 token。

## 部署说明

项目包含 `Dockerfile` 和 `nginx.conf`，可用于将 Vite 构建产物交给 Nginx 托管。

典型流程：

```bash
npm install
npm run build
```

然后将 `dist/` 交给 Nginx 或对象存储/CDN。生产环境需要确保：

- `/api` 正确反向代理到 FastAPI 后端。
- 后端 CORS 配置包含实际前端域名。
- HTTPS 证书配置正确。
- 不将 `.env`、测试报告、覆盖率报告、`node_modules/` 和 `dist/` 提交到 GitHub。

## 开发规范

- API 请求统一写在 `src/api/`，不要在页面中散落裸 Axios 调用。
- 页面内只处理视图状态和交互逻辑，复杂请求逻辑尽量封装到 API 层。
- 登录态统一通过 `auth.js` 和路由守卫管理。
- 需要鉴权的接口必须依赖 `request.js`，以确保自动附加 Token。
- 新增页面时同步添加路由 `meta.title`，浏览器标题会自动更新。
- 组件测试尽量 mock 后端 API，避免依赖真实 LLM 调用。

