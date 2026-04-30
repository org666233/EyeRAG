class ApiException implements Exception {
  final int? statusCode;
  final String message;

  const ApiException({this.statusCode, required this.message});

  factory ApiException.fromStatusCode(int code, String msg) {
    return switch (code) {
      401 => ApiException(statusCode: 401, message: '登录已过期，请重新登录'),
      403 => ApiException(statusCode: 403, message: '权限不足'),
      404 => ApiException(statusCode: 404, message: '资源不存在'),
      422 => ApiException(statusCode: 422, message: msg.isNotEmpty ? msg : '请求参数有误'),
      429 => ApiException(statusCode: 429, message: '请求过于频繁，请稍后重试'),
      500 => ApiException(statusCode: 500, message: '服务器内部错误'),
      _ => ApiException(statusCode: code, message: msg.isNotEmpty ? msg : '未知错误'),
    };
  }

  factory ApiException.network() =>
      const ApiException(message: '网络连接失败，请检查网络设置');

  factory ApiException.timeout() =>
      const ApiException(message: '请求超时，请稍后重试');

  @override
  String toString() => 'ApiException($statusCode): $message';
}
