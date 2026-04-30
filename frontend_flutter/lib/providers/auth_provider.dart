import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/user.dart';
import '../services/auth_service.dart';
import '../core/storage/local_storage.dart';

final authServiceProvider = Provider((_) => AuthService());

final authStateProvider = AsyncNotifierProvider<AuthNotifier, User?>(() {
  return AuthNotifier();
});

class AuthNotifier extends AsyncNotifier<User?> {
  @override
  Future<User?> build() async {
    final token = LocalStorage.instance.token;
    if (token == null || token.isEmpty) return null;
    try {
      return await ref.read(authServiceProvider).getMe();
    } catch (_) {
      return null;
    }
  }

  Future<void> login(String username, String password) async {
    state = const AsyncLoading();
    try {
      await ref.read(authServiceProvider).login(username, password);
      final user = await ref.read(authServiceProvider).getMe();
      state = AsyncData(user);
    } catch (e) {
      state = const AsyncData(null); // 重置为未登录
      rethrow;                        // 让 UI 层 catch 并展示错误
    }
  }

  Future<void> register(String username, String email, String password) async {
    state = const AsyncLoading();
    try {
      await ref.read(authServiceProvider).register(username, email, password);
      await ref.read(authServiceProvider).login(username, password);
      final user = await ref.read(authServiceProvider).getMe();
      state = AsyncData(user);
    } catch (e) {
      state = const AsyncData(null);
      rethrow;
    }
  }

  Future<void> logout() async {
    await ref.read(authServiceProvider).logout();
    state = const AsyncData(null);
  }

  Future<void> refresh() async {
    state = await AsyncValue.guard(
      () => ref.read(authServiceProvider).getMe(),
    );
  }
}
