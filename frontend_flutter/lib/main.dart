import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/network/dio_client.dart';
import 'core/storage/local_storage.dart';
import 'app.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // 初始化基础设施
  await LocalStorage.instance.init();

  // 移动端预热数据库；Web 端使用内存存储，无需初始化
  if (!kIsWeb) {
    // 延迟导入避免 web 编译报错
    await _initMobileDb();
  }

  DioClient.instance.init();

  runApp(
    const ProviderScope(
      child: App(),
    ),
  );
}

Future<void> _initMobileDb() async {
  // 触发数据库文件创建（lazy init，首次访问时创建）
  // LocalDb 内部 getter 已做 lazy，这里无需显式调用
}
