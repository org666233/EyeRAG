import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';

class MainShell extends StatelessWidget {
  final Widget child;
  const MainShell({super.key, required this.child});

  static const _tabs = [
    (path: '/chat', icon: Icons.chat_bubble_outline_rounded, activeIcon: Icons.chat_bubble_rounded, label: '问答'),
    (path: '/history', icon: Icons.history_rounded, activeIcon: Icons.history_rounded, label: '历史'),
    (path: '/favorites', icon: Icons.bookmark_outline_rounded, activeIcon: Icons.bookmark_rounded, label: '收藏'),
    (path: '/profile', icon: Icons.person_outline_rounded, activeIcon: Icons.person_rounded, label: '我的'),
  ];

  int _currentIndex(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    for (int i = 0; i < _tabs.length; i++) {
      if (location.startsWith(_tabs[i].path)) return i;
    }
    return 0;
  }

  @override
  Widget build(BuildContext context) {
    final index = _currentIndex(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      extendBody: true,
      body: child,
      bottomNavigationBar: _FrostedNavBar(
        index: index,
        isDark: isDark,
        onTap: (i) => context.go(_tabs[i].path),
        tabs: _tabs
            .map((t) =>
                _NavItem(icon: t.icon, activeIcon: t.activeIcon, label: t.label))
            .toList(),
      ),
    );
  }
}

class _FrostedNavBar extends StatelessWidget {
  final int index;
  final bool isDark;
  final ValueChanged<int> onTap;
  final List<_NavItem> tabs;

  const _FrostedNavBar({
    required this.index,
    required this.isDark,
    required this.onTap,
    required this.tabs,
  });

  @override
  Widget build(BuildContext context) {
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          decoration: BoxDecoration(
            color: isDark
                ? Colors.black.withAlpha(179)
                : Colors.white.withAlpha(230),
            border: Border(
              top: BorderSide(
                color: isDark
                    ? Colors.white.withAlpha(20)
                    : Colors.black.withAlpha(15),
              ),
            ),
          ),
          child: SafeArea(
            top: false,
            child: SizedBox(
              height: 64,
              child: Row(
                children: List.generate(tabs.length, (i) {
                  final selected = i == index;
                  final tab = tabs[i];
                  return Expanded(
                    child: InkWell(
                      onTap: () => onTap(i),
                      borderRadius: BorderRadius.circular(16),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 250),
                        curve: Curves.easeOutCubic,
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            AnimatedContainer(
                              duration: const Duration(milliseconds: 250),
                              curve: Curves.easeOutBack,
                              transform: Matrix4.diagonal3Values(
                                selected ? 1.15 : 1.0,
                                selected ? 1.15 : 1.0,
                                1.0,
                              ),
                              child: Icon(
                                selected ? tab.activeIcon : tab.icon,
                                size: 24,
                                color: selected
                                    ? AppColors.primary
                                    : isDark
                                        ? Colors.white38
                                        : AppColors.textMuted,
                              ),
                            ),
                            const SizedBox(height: 4),
                            AnimatedDefaultTextStyle(
                              duration: const Duration(milliseconds: 200),
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: selected
                                    ? FontWeight.w600
                                    : FontWeight.w400,
                                color: selected
                                    ? AppColors.primary
                                    : isDark
                                        ? Colors.white38
                                        : AppColors.textMuted,
                              ),
                              child: Text(tab.label),
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                }),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _NavItem {
  final IconData icon;
  final IconData activeIcon;
  final String label;
  const _NavItem(
      {required this.icon, required this.activeIcon, required this.label});
}
