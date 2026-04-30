import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../constants/api_constants.dart';
import '../constants/app_constants.dart';
import 'api_exception.dart';

class DioClient {
  DioClient._();
  static final DioClient instance = DioClient._();

  late final Dio _dio;
  bool _initialized = false;

  void init() {
    if (_initialized) return;
    _dio = Dio(
      BaseOptions(
        baseUrl: ApiConstants.baseUrl,
        connectTimeout: const Duration(milliseconds: AppConstants.connectTimeout),
        receiveTimeout: const Duration(milliseconds: AppConstants.receiveTimeout),
        headers: {'Content-Type': 'application/json'},
      ),
    );
    _dio.interceptors.add(_AuthInterceptor());
    _dio.interceptors.add(_ErrorInterceptor());
    _initialized = true;
  }

  Dio get dio => _dio;
}

class _AuthInterceptor extends Interceptor {
  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(AppConstants.tokenKey);
    if (token != null && token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }
}

class _ErrorInterceptor extends Interceptor {
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    ApiException exception;
    if (err.type == DioExceptionType.connectionTimeout ||
        err.type == DioExceptionType.receiveTimeout) {
      exception = ApiException.timeout();
    } else if (err.type == DioExceptionType.connectionError) {
      exception = ApiException.network();
    } else if (err.response != null) {
      final code = err.response!.statusCode ?? 0;
      final data = err.response!.data;
      String msg = '';
      if (data is Map) {
        msg = data['detail']?.toString() ??
            data['message']?.toString() ??
            '';
      }
      exception = ApiException.fromStatusCode(code, msg);
    } else {
      exception = ApiException(message: err.message ?? '未知网络错误');
    }
    handler.reject(
      DioException(
        requestOptions: err.requestOptions,
        error: exception,
        message: exception.message,
      ),
    );
  }
}
