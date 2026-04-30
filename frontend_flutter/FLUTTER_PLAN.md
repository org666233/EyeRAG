# Flutter 眼科医疗问答 App — 开发方案

> 项目：基于 RAG 的眼科医疗知识问答系统（移动端）  
> 共用后端：FastAPI `/api/*`  
> 三端覆盖：iOS / Android / Web  
> 作者：鞠明轩 · 云南大学软件学院软件工程 2022 级

---

## 一、技术栈

| 用途 | 选型 | 说明 |
|------|------|------|
| 状态管理 | `flutter_riverpod ^2.x` | 比 Provider 更现代，编译时安全 |
| 路由 | `go_router ^14.x` | 声明式路由，支持登录守卫 & 深链接 |
| 网络 | `dio ^5.x` | 拦截器自动注入 JWT token |
| 本地存储 | `shared_preferences` | token / 主题 / 设置持久化 |
| 离线缓存 | `sqflite` | 收藏内容本地数据库 |
| Markdown | `flutter_markdown` | 渲染后端返回的 Markdown 答案 |
| 语音输入 | `speech_to_text` | 语音转文字，移动端专属 |
| 生物识别 | `local_auth` | Face ID / Touch ID 快速登录 |
| 分享 | `share_plus` + `screenshot` | 将答案截图分享到其他 App |
| UI | Material 3 | Flutter 最新设计语言，亮/暗双主题 |
| 代码生成 | `json_serializable` + `build_runner` | Model 自动生成 fromJson/toJson |

---

## 二、目录结构

```
lib/
├── main.dart                    # App 入口
├── app.dart                     # MaterialApp + 主题 + Router
│
├── core/                        # 基础设施层
│   ├── constants/
│   │   ├── api_constants.dart   # 后端 base URL、路径常量
│   │   └── app_constants.dart   # 分页大小、超时等
│   ├── network/
│   │   ├── dio_client.dart      # Dio 实例 + 拦截器
│   │   └── api_exception.dart   # 统一错误类型
│   ├── storage/
│   │   ├── secure_storage.dart  # token 存取
│   │   └── local_db.dart        # sqflite 收藏缓存
│   ├── router/
│   │   └── app_router.dart      # go_router 路由表 + 守卫
│   └── theme/
│       ├── app_theme.dart       # 亮色主题
│       └── dark_theme.dart      # 暗色主题
│
├── models/                      # 数据模型（json_serializable）
│   ├── user.dart
│   ├── conversation.dart
│   ├── message.dart
│   ├── favorite.dart
│   └── search_history.dart
│
├── services/                    # API 调用层
│   ├── auth_service.dart
│   ├── chat_service.dart
│   ├── favorite_service.dart
│   ├── history_service.dart
│   └── stats_service.dart
│
├── providers/                   # Riverpod Providers
│   ├── auth_provider.dart
│   ├── chat_provider.dart
│   ├── favorite_provider.dart
│   ├── history_provider.dart
│   ├── theme_provider.dart
│   └── stats_provider.dart
│
├── pages/                       # 页面
│   ├── splash/
│   │   └── splash_page.dart
│   ├── auth/
│   │   ├── login_page.dart
│   │   └── register_page.dart
│   ├── shell/
│   │   └── main_shell.dart      # 底部导航 Shell
│   ├── chat/
│   │   ├── chat_list_page.dart  # 对话列表
│   │   └── chat_detail_page.dart# 聊天详情
│   ├── history/
│   │   └── history_page.dart
│   ├── favorites/
│   │   └── favorites_page.dart
│   └── profile/
│       ├── profile_page.dart
│       └── about_page.dart
│
└── widgets/                     # 通用组件
    ├── common/
    │   ├── app_loading.dart     # 骨架屏
    │   ├── app_empty.dart       # 空状态
    │   ├── app_error.dart       # 错误状态
    │   └── app_toast.dart       # Toast 封装
    └── chat/
        ├── message_bubble.dart  # 消息气泡
        ├── markdown_view.dart   # Markdown 渲染
        ├── typing_animation.dart# 打字机效果
        └── voice_input_btn.dart # 语音输入按钮
```

---

## 三、模块清单与实现方案

### A. 基础架构层

#### A1 路由系统
- 使用 `go_router`，定义 `AppRouter` 单例
- 路由守卫：读取 `AuthProvider` 状态，未登录跳转 `/login`
- 路由表：`/splash` → `/login` → `/register` → `/shell`（含子路由 `/chat`、`/chat/:id`、`/history`、`/favorites`、`/profile`）

#### A2 网络层
- `DioClient` 单例，`baseUrl` 从 `ApiConstants` 读取
- `RequestInterceptor`：每次请求自动从 `SecureStorage` 读 token，注入 `Authorization: Bearer xxx`
- `ResponseInterceptor`：401 → 清除 token → 跳转登录；统一错误转为 `ApiException`

#### A3 状态管理
- 全局使用 `ProviderScope` 包裹
- 每个业务模块一个 Provider 文件，`AsyncNotifier` 处理异步状态
- `authProvider` 全局监听，登出时清理所有状态

#### A4 主题系统
- `themeProvider`：`ThemeMode`（system / light / dark），存入 SharedPreferences
- Material 3 ColorScheme，主色调：蓝绿色（医疗感）
- 字体：Noto Sans SC（中文优化）

#### A5 本地存储
- `SharedPreferences`：token、userId、themeMode、biometricEnabled
- `sqflite`：`favorites` 表（id, question, answer, created_at），支持离线读取

#### A6 API Client
- 每个 Service 对应后端一个模块，方法命名与接口语义一致
- 统一返回 `Future<T>`，错误通过 `ApiException` 传递

---

### B. 用户认证模块

#### B1 登录页
- 邮箱 + 密码表单，FormKey 校验
- 记住密码（SharedPreferences 存邮箱）
- 登录成功 → 存 token → 跳转 Shell

#### B2 注册页
- 用户名 / 邮箱 / 密码 + 确认密码
- 实时校验密码强度

#### B3 Token 管理
- 登录时存储 token
- Dio 拦截器自动携带
- 401 时清除并重定向

#### B4 ⭐ 生物识别登录
- 使用 `local_auth`
- 首次登录后，提示"是否开启 Face ID/指纹登录"
- 开启后，下次进入 App 显示生物识别解锁按钮
- 实现：调用 `LocalAuthentication.authenticate()`，成功后直接用缓存 token 进入

#### B5 ⭐ 启动页 Splash
- App Logo + 项目名渐入动画（500ms FadeIn）
- 检查本地 token → 有效跳主页，无效跳登录
- 耗时 ≤ 1.5s

---

### C. 智能问答模块（核心）

#### C1 对话列表页
- 展示所有对话（标题 + 最后消息时间）
- 下拉刷新（`RefreshIndicator`）
- 左滑删除（`Dismissible`）
- 右上角"+"新建对话

#### C2 聊天详情页
- 气泡式消息列表（用户右对齐蓝色，AI 左对齐灰色）
- 底部输入框 + 发送按钮 + 语音按钮
- 自动滚动到最新消息

#### C3 ⭐ Markdown 渲染
- 使用 `flutter_markdown`
- 支持：**加粗**、*斜体*、`代码`、列表、表格、分隔线
- 代码块语法高亮（`markdown` + `highlight` 主题）
- AI 回答全部通过 `MarkdownView` widget 展示

#### C4 ⭐ 打字机动画效果
- AI 回答逐字符显示，速度：约 30 字符/秒
- 实现：`StreamController<String>` + `Timer.periodic`，每次 tick 追加一个字符
- 显示完毕后固定，不重复播放

#### C5 ⭐ 语音输入
- 底部输入区右侧"麦克风"图标按钮
- 长按：开始录音（图标变红，显示波形动画）
- 松开：停止识别，文字填入输入框，可编辑后发送
- 实现：`speech_to_text` 包，语言设为 `zh_CN`

#### C6 ⭐ 长按消息操作菜单
- 长按任意气泡 → 弹出 `ModalBottomSheet`
- 选项：📋 复制文本 / ⭐ 收藏 / 📤 分享
- 收藏调用 `POST /api/favorites`，同步写本地 sqflite

#### C7 ⭐ 分享答案为图片
- 使用 `screenshot` 包将消息气泡截图为 PNG
- 调用 `share_plus` 的 `ShareXFiles` 分享到系统分享菜单

#### C8 对话管理
- 新建对话：`POST /api/chat/conversations`
- 修改标题：`PATCH /api/chat/conversations/:id/title`（长按对话列表项）
- 删除：`DELETE /api/chat/conversations/:id`

---

### D. 历史记录模块

#### D1 历史列表页
- 调用 `GET /api/search-history`，展示问题 + 时间
- 顶部搜索框，关键词过滤（本地 filter）
- 下拉刷新

#### D2 历史详情页
- 展示该条检索记录的完整问题和回答
- 支持从详情页直接收藏

#### D3 多选删除
- 长按进入多选模式，复选框出现
- 顶部 AppBar 变为"已选 N 项"+ 删除按钮

#### D4 ⭐ 按日期分组展示
- 列表按日期分组：今天 / 昨天 / 本周 / 更早
- 使用 `SliverList` + `SliverPersistentHeader` 实现粘性分组标题

---

### E. 收藏模块

#### E1 收藏列表页
- 调用 `GET /api/favorites`，展示收藏的问题 + 简短答案预览
- 顶部搜索框（关键词过滤）

#### E2 取消收藏
- 右滑删除（`Dismissible`），调用 `DELETE /api/favorites/:id`
- 同步删除本地 sqflite 缓存

#### E3 ⭐ 离线缓存
- 每次加载收藏列表，同步写入 sqflite
- 无网络时从本地读取，页面顶部显示"离线模式，数据可能不是最新"横幅

#### E4 ⭐ 收藏内容搜索
- 搜索框实时过滤（debounce 300ms）
- 支持按问题内容和答案内容同时搜索

---

### F. 个人中心模块

#### F1 个人信息页
- 头像（首字母 Avatar）、用户名、邮箱、角色标签
- 使用卡片式布局

#### F2 退出登录
- 二次确认弹窗
- 清除 token + 清除 Riverpod 状态 + 跳转登录页

#### F3 ⭐ 深色模式
- 三选一切换卡：跟随系统 / 亮色 / 暗色
- 即时生效，存入 SharedPreferences

#### F4 ⭐ 我的统计小卡片
- 调用 `GET /api/stats/overview`
- 展示：总提问数 / 收藏数 / 本月活跃天数
- 3 个彩色小卡片横排展示

#### F5 关于页
- App 名称、版本号（`package_info_plus`）
- 技术栈说明、后端地址
- 作者信息（论文截图亮点）

---

### G. 通用 UI 组件

| 组件 | 实现方式 |
|------|----------|
| `AppLoading` | `Shimmer` 骨架屏，比转圈更现代 |
| `AppEmpty` | 自定义插画 SVG + 说明文字 + 可选操作按钮 |
| `AppError` | 错误图标 + 错误信息 + "重试"按钮（回调刷新）|
| `AppToast` | 封装 `ScaffoldMessenger.showSnackBar`，全局可调用 |
| 确认弹窗 | `showDialog` 封装，标题/内容/确认回调参数化 |
| 底部导航 | `NavigationBar`（Material 3），4 Tab |

---

## 四、开发顺序

```
Week 1
  Day 1：A 层基础架构（路由/网络/主题/存储）
  Day 2：B 层认证（登录/注册/Splash/生物识别）
  Day 3-4：C 层对话列表 + 聊天详情 + Markdown + 打字机

Week 2
  Day 5：C 层语音输入 + 长按菜单 + 分享
  Day 6：D 层历史记录（含日期分组）
  Day 7：E 层收藏（含离线缓存）
  Day 8：F 层个人中心 + 深色模式 + 统计卡片
  Day 9：G 层通用组件补全 + Web 布局适配
  Day 10：整体 UI 打磨 + 真机测试
```

---

## 五、后端接口对照表（无需改动）

| Flutter 模块 | 使用的后端接口 |
|-------------|--------------|
| 登录/注册 | `POST /api/auth/login`、`POST /api/auth/register` |
| 用户信息 | `GET /api/auth/me` |
| 对话列表 | `GET /api/chat/conversations` |
| 聊天 | `POST /api/chat/completions`、`GET /api/chat/conversations/:id` |
| 删除/重命名对话 | `DELETE`、`PATCH /api/chat/conversations/:id` |
| 历史记录 | `GET /api/search-history`、`DELETE /api/search-history/:id` |
| 收藏 | `GET/POST/DELETE /api/favorites` |
| 统计 | `GET /api/stats/overview` |

---

*文档生成时间：2026-04-23*
