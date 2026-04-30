import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:local_auth/local_auth.dart';
import '../../providers/auth_provider.dart';
import '../../core/storage/local_storage.dart';
import '../../core/network/api_exception.dart';
import '../../core/theme/app_theme.dart';

class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});
  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage>
    with SingleTickerProviderStateMixin {
  final _formKey = GlobalKey<FormState>();
  final _usernameCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  bool _obscure = true;
  bool _loading = false;
  bool _biometricAvailable = false;
  final _localAuth = LocalAuthentication();
  late AnimationController _animCtrl;
  late Animation<double> _slideAnim;

  @override
  void initState() {
    super.initState();
    _usernameCtrl.text = LocalStorage.instance.savedUsername ?? '';
    _animCtrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 700));
    _slideAnim =
        CurvedAnimation(parent: _animCtrl, curve: Curves.easeOutCubic);
    _animCtrl.forward();
    _checkBiometric();
  }

  Future<void> _checkBiometric() async {
    if (!LocalStorage.instance.biometricEnabled) return;
    final canCheck = await _localAuth.canCheckBiometrics;
    if (mounted) setState(() => _biometricAvailable = canCheck);
    if (canCheck) _tryBiometric();
  }

  Future<void> _tryBiometric() async {
    try {
      final ok = await _localAuth.authenticate(
        localizedReason: '请验证身份以快速登录',
        options: const AuthenticationOptions(biometricOnly: true),
      );
      if (ok && mounted) {
        final token = LocalStorage.instance.token;
        if (token != null && token.isNotEmpty) {
          await ref.read(authStateProvider.notifier).refresh();
          if (mounted) context.go('/chat');
        }
      }
    } catch (_) {}
  }

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);
    try {
      await ref
          .read(authStateProvider.notifier)
          .login(_usernameCtrl.text.trim(), _passCtrl.text);
      await LocalStorage.instance.setSavedUsername(_usernameCtrl.text.trim());
      if (mounted) context.go('/chat');
    } catch (e) {
      if (mounted) {
        final msg = _friendlyError(e);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(msg),
            backgroundColor: AppColors.error,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12)),
            margin: const EdgeInsets.all(16),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  /// 从各种异常类型中提取用户友好的错误信息
  String _friendlyError(Object e) {
    if (e is DioException) {
      final inner = e.error;
      if (inner is ApiException) return inner.message;
      if (e.message != null && e.message!.isNotEmpty) return e.message!;
      return '网络请求失败，请检查后端服务是否启动';
    }
    if (e is ApiException) return e.message;
    final s = e.toString();
    // 过滤掉 JS 底层报错，统一提示
    if (s.contains('TypeError') || s.contains('undefined')) {
      return '网络连接失败，请确认后端服务已启动且 CORS 已配置';
    }
    return s;
  }

  @override
  void dispose() {
    _animCtrl.dispose();
    _usernameCtrl.dispose();
    _passCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // 通过 app.dart 的 _MobileFrame 已将宽屏限制在 430px
    // 这里只需要按移动端逻辑布局
    final screenHeight = MediaQuery.of(context).size.height;
    final heroHeight = screenHeight * 0.40;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: Stack(
        fit: StackFit.expand, // 确保 Stack 撑满父容器
        children: [
          // ── 顶部渐变 Hero ──────────────────────────
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            height: heroHeight,
            child: Container(
              decoration: const BoxDecoration(gradient: AppGradients.hero),
              child: Stack(
                children: [
                  Positioned(
                    top: -60,
                    right: -60,
                    child: Container(
                      width: 200,
                      height: 200,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.white.withAlpha(20),
                      ),
                    ),
                  ),
                  Positioned(
                    bottom: 40,
                    left: -40,
                    child: Container(
                      width: 160,
                      height: 160,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.white.withAlpha(13),
                      ),
                    ),
                  ),
                  SafeArea(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(28, 40, 28, 0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            width: 52,
                            height: 52,
                            decoration: BoxDecoration(
                              color: Colors.white.withAlpha(38),
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(
                                  color: Colors.white.withAlpha(77)),
                            ),
                            child: const Icon(Icons.visibility_rounded,
                                color: Colors.white, size: 28),
                          ),
                          const SizedBox(height: 20),
                          const Text(
                            '欢迎回来',
                            style: TextStyle(
                              fontSize: 30,
                              fontWeight: FontWeight.w800,
                              color: Colors.white,
                              letterSpacing: -0.5,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            '眼科智能问答助手',
                            style: TextStyle(
                              fontSize: 16,
                              color: Colors.white.withAlpha(179),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // ── 底部表单卡片 ───────────────────────────
          Positioned(
            top: heroHeight - 32, // 与 Hero 区叠压 32px，营造层叠感
            left: 0,
            right: 0,
            bottom: 0,
            child: SlideTransition(
              position: Tween<Offset>(
                begin: const Offset(0, 0.3),
                end: Offset.zero,
              ).animate(_slideAnim),
              child: FadeTransition(
                opacity: _slideAnim,
                child: Container(
                  decoration: const BoxDecoration(
                    color: AppColors.background,
                    borderRadius:
                        BorderRadius.vertical(top: Radius.circular(32)),
                  ),
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.fromLTRB(24, 32, 24, 32),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            '账号登录',
                            style: TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.w700,
                              color: AppColors.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 4),
                          const Text(
                            '请输入您的邮箱和密码',
                            style: TextStyle(
                                fontSize: 13, color: AppColors.textMuted),
                          ),
                          const SizedBox(height: 28),
                          _FieldLabel('用户名'),
                          const SizedBox(height: 8),
                          TextFormField(
                            controller: _usernameCtrl,
                            keyboardType: TextInputType.text,
                            decoration: const InputDecoration(
                              hintText: '请输入用户名',
                              prefixIcon: Icon(Icons.person_outline_rounded),
                            ),
                            validator: (v) =>
                                v == null || v.isEmpty ? '请输入用户名' : null,
                          ),
                          const SizedBox(height: 20),
                          _FieldLabel('密码'),
                          const SizedBox(height: 8),
                          TextFormField(
                            controller: _passCtrl,
                            obscureText: _obscure,
                            decoration: InputDecoration(
                              hintText: '请输入密码',
                              prefixIcon: const Icon(Icons.lock_outline),
                              suffixIcon: IconButton(
                                icon: Icon(
                                  _obscure
                                      ? Icons.visibility_outlined
                                      : Icons.visibility_off_outlined,
                                ),
                                onPressed: () =>
                                    setState(() => _obscure = !_obscure),
                              ),
                            ),
                            validator: (v) => v == null || v.length < 6
                                ? '密码至少 6 位'
                                : null,
                          ),
                          const SizedBox(height: 32),
                          _GradientButton(
                            text: '登录',
                            loading: _loading,
                            onTap: _login,
                          ),
                          if (_biometricAvailable) ...[
                            const SizedBox(height: 12),
                            OutlinedButton.icon(
                              onPressed: _tryBiometric,
                              icon: const Icon(Icons.fingerprint, size: 20),
                              label: const Text('指纹 / Face ID 快速登录'),
                              style: OutlinedButton.styleFrom(
                                minimumSize:
                                    const Size(double.infinity, 52),
                                shape: RoundedRectangleBorder(
                                    borderRadius:
                                        BorderRadius.circular(14)),
                                side: const BorderSide(
                                    color: AppColors.primary),
                                foregroundColor: AppColors.primary,
                              ),
                            ),
                          ],
                          const SizedBox(height: 24),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Text(
                                '还没有账号？',
                                style: TextStyle(
                                    color: AppColors.textMuted,
                                    fontSize: 14),
                              ),
                              TextButton(
                                onPressed: () =>
                                    context.push('/login/register'),
                                style: TextButton.styleFrom(
                                  foregroundColor: AppColors.primary,
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 8),
                                ),
                                child: const Text(
                                  '立即注册',
                                  style: TextStyle(
                                      fontWeight: FontWeight.w600,
                                      fontSize: 14),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── 辅助组件 ──────────────────────────────────────────────────────────────────
class _FieldLabel extends StatelessWidget {
  final String text;
  const _FieldLabel(this.text);
  @override
  Widget build(BuildContext context) => Text(
        text,
        style: const TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w600,
          color: AppColors.textPrimary,
          letterSpacing: 0.2,
        ),
      );
}

class _GradientButton extends StatelessWidget {
  final String text;
  final bool loading;
  final VoidCallback? onTap;
  const _GradientButton(
      {required this.text, required this.loading, this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: loading ? null : onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        height: 52,
        decoration: BoxDecoration(
          gradient: loading
              ? const LinearGradient(
                  colors: [Color(0xFF93C5FD), Color(0xFF67E8F9)])
              : const LinearGradient(
                  begin: Alignment.centerLeft,
                  end: Alignment.centerRight,
                  colors: [AppColors.primary, AppColors.secondary]),
          borderRadius: BorderRadius.circular(14),
          boxShadow: loading
              ? []
              : [
                  BoxShadow(
                    color: AppColors.primary.withAlpha(77),
                    blurRadius: 16,
                    offset: const Offset(0, 6),
                  ),
                ],
        ),
        child: Center(
          child: loading
              ? const SizedBox(
                  width: 22,
                  height: 22,
                  child: CircularProgressIndicator(
                      strokeWidth: 2.5, color: Colors.white),
                )
              : Text(
                  text,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.5,
                  ),
                ),
        ),
      ),
    );
  }
}
