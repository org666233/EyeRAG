import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/auth_provider.dart';
import '../../core/theme/app_theme.dart';

class SplashPage extends ConsumerStatefulWidget {
  const SplashPage({super.key});
  @override
  ConsumerState<SplashPage> createState() => _SplashPageState();
}

class _SplashPageState extends ConsumerState<SplashPage>
    with TickerProviderStateMixin {
  late AnimationController _bgCtrl;
  late AnimationController _logoCtrl;
  late AnimationController _textCtrl;
  late AnimationController _pulseCtrl;

  late Animation<double> _bgFade;
  late Animation<double> _logoScale;
  late Animation<double> _logoFade;
  late Animation<double> _textFade;
  late Animation<Offset> _textSlide;
  late Animation<double> _pulse;

  @override
  void initState() {
    super.initState();
    _bgCtrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 600));
    _logoCtrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 800));
    _textCtrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 600));
    _pulseCtrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 2000))
      ..repeat(reverse: true);

    _bgFade = Tween(begin: 0.0, end: 1.0)
        .animate(CurvedAnimation(parent: _bgCtrl, curve: Curves.easeOut));

    _logoScale = Tween(begin: 0.6, end: 1.0)
        .animate(CurvedAnimation(parent: _logoCtrl, curve: Curves.elasticOut));
    _logoFade = Tween(begin: 0.0, end: 1.0)
        .animate(CurvedAnimation(parent: _logoCtrl, curve: Curves.easeOut));

    _textFade = Tween(begin: 0.0, end: 1.0)
        .animate(CurvedAnimation(parent: _textCtrl, curve: Curves.easeOut));
    _textSlide =
        Tween(begin: const Offset(0, 0.5), end: Offset.zero).animate(
      CurvedAnimation(parent: _textCtrl, curve: Curves.easeOutCubic),
    );
    _pulse = Tween(begin: 0.95, end: 1.05)
        .animate(CurvedAnimation(parent: _pulseCtrl, curve: Curves.easeInOut));

    _runSequence();
  }

  Future<void> _runSequence() async {
    await _bgCtrl.forward();
    await _logoCtrl.forward();
    await _textCtrl.forward();
    await Future.delayed(const Duration(milliseconds: 800));
    if (!mounted) return;
    final user = ref.read(authStateProvider).valueOrNull;
    context.go(user != null ? '/chat' : '/login');
  }

  @override
  void dispose() {
    _bgCtrl.dispose();
    _logoCtrl.dispose();
    _textCtrl.dispose();
    _pulseCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: FadeTransition(
        opacity: _bgFade,
        child: Container(
          decoration: const BoxDecoration(gradient: AppGradients.heroDeep),
          child: Stack(
            children: [
              // 背景装饰圆
              Positioned(
                top: -80,
                right: -80,
                child: _GlowCircle(radius: 240, opacity: 0.08),
              ),
              Positioned(
                bottom: -120,
                left: -100,
                child: _GlowCircle(radius: 320, opacity: 0.06),
              ),
              Positioned(
                top: MediaQuery.of(context).size.height * 0.35,
                right: -60,
                child: _GlowCircle(radius: 160, opacity: 0.05),
              ),
              // 主内容
              Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Logo
                    FadeTransition(
                      opacity: _logoFade,
                      child: ScaleTransition(
                        scale: _logoScale,
                        child: AnimatedBuilder(
                          animation: _pulse,
                          builder: (_, child) => Transform.scale(
                            scale: _pulse.value,
                            child: child,
                          ),
                          child: _EyeLogo(),
                        ),
                      ),
                    ),
                    const SizedBox(height: 36),
                    // 文字
                    SlideTransition(
                      position: _textSlide,
                      child: FadeTransition(
                        opacity: _textFade,
                        child: Column(
                          children: [
                            const Text(
                              '眼科智能问答',
                              style: TextStyle(
                                fontSize: 28,
                                fontWeight: FontWeight.w800,
                                color: Colors.white,
                                letterSpacing: 2,
                              ),
                            ),
                            const SizedBox(height: 10),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 16, vertical: 6),
                              decoration: BoxDecoration(
                                color: Colors.white.withAlpha(25),
                                borderRadius: BorderRadius.circular(20),
                                border: Border.all(
                                    color: Colors.white.withAlpha(51)),
                              ),
                              child: const Text(
                                'RAG · 检索增强生成 · 眼科医疗',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.white70,
                                  letterSpacing: 1,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              // 底部版权
              Positioned(
                bottom: 48,
                left: 0,
                right: 0,
                child: FadeTransition(
                  opacity: _textFade,
                  child: const Text(
                    '© 2026  云南大学软件学院',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Colors.white38,
                      fontSize: 12,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _EyeLogo extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 110,
      height: 110,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: const RadialGradient(
          colors: [Color(0xFF3B82F6), Color(0xFF1D4ED8)],
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF3B82F6).withAlpha(102),
            blurRadius: 40,
            spreadRadius: 8,
          ),
        ],
      ),
      child: const Icon(Icons.visibility_rounded, size: 54, color: Colors.white),
    );
  }
}

class _GlowCircle extends StatelessWidget {
  final double radius;
  final double opacity;
  const _GlowCircle({required this.radius, required this.opacity});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: radius,
      height: radius,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [
            Colors.white.withValues(alpha: opacity),
            Colors.transparent,
          ],
        ),
      ),
    );
  }
}
