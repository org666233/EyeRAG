# EyeRAG Flutter App

`frontend_flutter/` 是 EyeRAG 的 Flutter 跨平台客户端，面向移动端使用场景开发，同时保留 Web、桌面平台工程骨架。移动端复用 FastAPI 后端 API，提供登录注册、流式问答、会话管理、检索历史、收藏、个人中心等功能，并扩展语音输入、生物识别登录、离线缓存和截图分享等移动端能力。

## 技术栈

| 类别 | 技术 |
| --- | --- |
| 框架 | Flutter 3, Dart |
| 状态管理 | flutter_riverpod, riverpod_annotation |
| 路由 | go_router |
| HTTP | Dio |
| 本地存储 | shared_preferences, sqflite |
| Markdown | flutter_markdown, markdown, flutter_highlight |
| 语音输入 | speech_to_text |
| 生物识别 | local_auth |
| 分享与截图 | share_plus, screenshot |
| 图片缓存 | cached_network_image |
| 代码生成 | build_runner, json_serializable |

## 目录结构

```text
frontend_flutter/
├── lib/
│   ├── app.dart                         # App 根组件
│   ├── main.dart                        # 启动入口
│   ├── core/
│   │   ├── constants/
│   │   │   ├── api_constants.dart       # API 路径和基础地址
│   │   │   └── app_constants.dart       # 应用常量
│   │   ├── network/
│   │   │   ├── dio_client.dart          # Dio 单例、拦截器
│   │   │   └── api_exception.dart       # 网络异常封装
│   │   ├── router/
│   │   │   └── app_router.dart          # go_router 路由
│   │   ├── storage/
│   │   │   ├── local_storage.dart       # SharedPreferences
│   │   │   └── local_db.dart            # sqflite 本地缓存
│   │   └── theme/
│   │       └── app_theme.dart           # Material 3 主题
│   ├── models/                          # 用户、消息、会话、收藏、历史模型
│   ├── pages/
│   │   ├── auth/                        # 登录、注册
│   │   ├── chat/                        # 会话列表、聊天详情
│   │   ├── favorites/                   # 收藏
│   │   ├── history/                     # 检索历史
│   │   ├── profile/                     # 个人中心、关于
│   │   ├── shell/                       # 主框架
│   │   ├── showcase/                    # RAG 展示页
│   │   └── splash/                      # 启动页
│   ├── providers/                       # Riverpod 状态管理
│   ├── services/                        # 后端 API 服务封装
│   └── widgets/                         # 通用组件和聊天组件
├── android/
├── ios/
├── web/
├── macos/
├── windows/
├── linux/
├── pubspec.yaml
└── README.md
```

## 功能说明

### 认证

- 登录。
- 注册。
- Token 本地持久化。
- 自动鉴权请求。
- 登录状态恢复。
- 生物识别登录扩展。

相关文件：

- `lib/pages/auth/login_page.dart`
- `lib/pages/auth/register_page.dart`
- `lib/providers/auth_provider.dart`
- `lib/services/auth_service.dart`
- `lib/core/storage/local_storage.dart`

### 流式问答

聊天服务通过 Dio 接收后端 SSE 流：

```dart
Stream<Map<String, dynamic>> sendMessageStream({
  required String question,
  String? conversationId,
  int topK = 10,
})
```

后端事件类型包括：

- `sources`：参考来源、会话 ID、检索决策、检索片段。
- `content`：LLM 生成的答案片段。
- `related`：相关问题推荐。
- `done`：流式回答结束。

流式回答完成后，移动端会调用保存接口，将问题、答案、来源、检索决策和耗时写入后端：

```dart
saveMessages(...)
```

相关文件：

- `lib/services/chat_service.dart`
- `lib/providers/chat_provider.dart`
- `lib/pages/chat/chat_detail_page.dart`
- `lib/widgets/chat/message_bubble.dart`
- `lib/widgets/chat/markdown_view.dart`
- `lib/widgets/chat/typing_animation.dart`

### 会话管理

- 获取会话列表。
- 获取会话详情。
- 新会话问答。
- 修改会话标题。
- 删除会话。
- 多轮上下文由后端维护。

### 收藏与历史

- 收藏问答。
- 取消收藏。
- 查看收藏列表。
- 本地收藏缓存。
- 查看检索历史。
- 历史详情展示检索决策和来源。

相关文件：

- `lib/services/favorite_service.dart`
- `lib/services/history_service.dart`
- `lib/providers/favorite_provider.dart`
- `lib/providers/history_provider.dart`
- `lib/pages/favorites/favorites_page.dart`
- `lib/pages/history/history_page.dart`

### 移动端增强

- `speech_to_text`：语音输入。
- `local_auth`：指纹/Face ID 等生物识别。
- `sqflite`：离线缓存。
- `share_plus` + `screenshot`：截图分享。
- `flutter_markdown`：医学回答 Markdown 渲染。
- `flutter_highlight`：代码块高亮，便于展示结构化内容。

## 环境要求

建议环境：

- Flutter 3.6+
- Dart SDK `^3.6.0`
- Android Studio 或 Xcode，可选，用于真机/模拟器调试
- 已启动的 EyeRAG 后端服务

检查 Flutter 环境：

```bash
flutter doctor
```

安装依赖：

```bash
cd frontend_flutter
flutter pub get
```

## 后端地址配置

API 常量位于：

```text
lib/core/constants/api_constants.dart
```

当前默认值为：

```dart
static const String baseUrl = 'http://localhost:8000/api';
```

不同平台访问本机后端的地址不同：

| 运行环境 | 推荐后端地址 |
| --- | --- |
| Flutter Web | `http://localhost:8000/api` |
| iOS 模拟器 | `http://localhost:8000/api` |
| Android 模拟器 | `http://10.0.2.2:8000/api` |
| 真机 | `http://<电脑局域网IP>:8000/api` |

真机调试时需要保证：

- 手机和电脑在同一局域网。
- 后端使用 `--host 0.0.0.0` 启动。
- 防火墙允许访问后端端口。
- 后端 CORS 允许当前来源。

后端启动示例：

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 运行

查看设备：

```bash
flutter devices
```

运行到默认设备：

```bash
flutter run
```

运行到指定设备：

```bash
flutter run -d chrome
flutter run -d ios
flutter run -d android
```

构建 Web：

```bash
flutter build web
```

构建 Android APK：

```bash
flutter build apk
```

构建 iOS：

```bash
flutter build ios
```

iOS 构建需要 macOS 和 Xcode 环境，并根据实际开发者账号配置签名。

## 测试与质量检查

静态分析：

```bash
flutter analyze
```

运行测试：

```bash
flutter test
```

格式化代码：

```bash
dart format lib test
```

如果后续启用 Riverpod 注解或 JSON 代码生成：

```bash
dart run build_runner build --delete-conflicting-outputs
```

## 与后端联调流程

推荐顺序：

1. 启动 MySQL 和 ChromaDB：

```bash
cd ..
docker-compose up -d
```

2. 启动后端：

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

3. 修改 Flutter API 地址，确保当前设备可以访问后端。

4. 启动 Flutter：

```bash
cd frontend_flutter
flutter run
```

5. 注册或登录账号，进入聊天页发送眼科问题。

如果流式问答没有内容，检查：

- 后端 `/api/health` 是否可访问。
- 移动端 API 地址是否正确。
- 登录 Token 是否有效。
- 后端 `.env` 是否配置 LLM API Key。
- ChromaDB Collection 是否已有文档块。
- Android 模拟器是否使用 `10.0.2.2` 而不是 `localhost`。

## 平台权限注意事项

### 语音输入

语音输入需要麦克风权限：

- Android：检查 `android/app/src/main/AndroidManifest.xml`。
- iOS：检查 `ios/Runner/Info.plist` 中的麦克风和语音识别权限描述。

### 生物识别

`local_auth` 需要平台配置：

- Android：启用 FragmentActivity，配置权限和主题。
- iOS：在 `Info.plist` 中配置 Face ID 使用说明。

### 分享与截图

`share_plus` 与 `screenshot` 在移动端通常可直接使用；桌面端和 Web 端能力可能受平台限制。

## 本地缓存

项目包含两类本地存储：

- `shared_preferences`：保存 Token、用户偏好、主题配置等轻量数据。
- `sqflite`：用于收藏等数据的离线缓存。

相关文件：

- `lib/core/storage/local_storage.dart`
- `lib/core/storage/local_db.dart`

## 开发规范

- 后端接口调用统一放在 `lib/services/`。
- 页面状态尽量通过 `providers/` 管理，避免页面内堆积复杂异步逻辑。
- 网络错误统一通过 `api_exception.dart` 和 Dio 拦截器处理。
- API 路径统一维护在 `api_constants.dart`。
- 页面导航统一走 `go_router`。
- 可复用 UI 放入 `widgets/`。
- 新增模型时保持 JSON 字段与后端 Pydantic Schema 对齐。

## 常见问题

### Android 模拟器连不上后端

Android 模拟器访问宿主机不能使用 `localhost`，应使用：

```text
http://10.0.2.2:8000/api
```

### 真机连不上后端

请使用电脑局域网 IP，例如：

```text
http://192.168.1.10:8000/api
```

并确认后端启动参数是：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### iOS 构建失败

执行：

```bash
cd ios
pod install
cd ..
flutter clean
flutter pub get
flutter run
```

如果仍失败，检查 Xcode、签名、最低 iOS 版本和插件权限配置。

### 修改 API 地址后没有生效

尝试清理构建缓存：

```bash
flutter clean
flutter pub get
flutter run
```

## GitHub 上传注意

以下内容不要提交：

- `.dart_tool/`
- `build/`
- `.flutter-plugins*`
- 平台构建产物
- `android/local.properties`
- `ios/Pods/`
- `macos/Pods/`
- 真机签名证书、私钥和 profile

根目录 `.gitignore` 已覆盖这些文件。
