class AppConstants {
  AppConstants._();

  static const String appName = '眼科智能问答';
  static const String tokenKey = 'auth_token';
  static const String userIdKey = 'user_id';
  static const String themeModeKey = 'theme_mode';
  static const String biometricEnabledKey = 'biometric_enabled';
  static const String savedUsernameKey = 'saved_username';

  static const int pageSize = 20;
  static const int connectTimeout = 15000;
  // RAG 查询耗时因 MiniMax 529 重试可能超过 2 分钟，设为 5 分钟
  static const int receiveTimeout = 300000;
  static const int typingSpeedMs = 30; // 打字机每字符间隔（毫秒）

  static const String dbName = 'ophthalmology_rag.db';
  static const int dbVersion = 1;
}
