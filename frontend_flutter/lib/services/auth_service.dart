import '../core/network/dio_client.dart';
import '../core/constants/api_constants.dart';
import '../core/storage/local_storage.dart';
import '../models/user.dart';

class AuthService {
  final _dio = DioClient.instance.dio;

  Future<String> login(String username, String password) async {
    final resp = await _dio.post(ApiConstants.login, data: {
      'username': username,
      'password': password,
    });
    final token = resp.data['access_token'] as String;
    await LocalStorage.instance.setToken(token);
    return token;
  }

  Future<void> register(String username, String email, String password) async {
    await _dio.post(ApiConstants.register, data: {
      'username': username,
      'email': email,
      'password': password,
    });
  }

  Future<User> getMe() async {
    final resp = await _dio.get(ApiConstants.me);
    return User.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<void> logout() async {
    await LocalStorage.instance.clearToken();
    await LocalStorage.instance.clearAll();
  }
}
