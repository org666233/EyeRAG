import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../providers/auth_provider.dart';
import '../../providers/theme_provider.dart';
import '../../services/stats_service.dart';
import '../../services/admin_service.dart';
import '../../core/theme/app_theme.dart';

class ProfilePage extends ConsumerWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authStateProvider).valueOrNull;
    final themeMode = ref.watch(themeModeProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final isAdmin = user?.isAdmin == true;

    return Scaffold(
      body: CustomScrollView(
        slivers: [
          // ── 渐变 Hero ────────────────────────────────────────────────
          SliverAppBar(
            expandedHeight: 220,
            pinned: true,
            backgroundColor:
                isDark ? AppColors.primaryDark : AppColors.primary,
            flexibleSpace: FlexibleSpaceBar(
              background: _HeroSection(user: user),
            ),
            title: const Text('个人中心',
                style: TextStyle(color: Colors.white, fontSize: 17)),
            actions: [
              IconButton(
                icon: const Icon(Icons.logout_rounded,
                    color: Colors.white, size: 20),
                onPressed: () => _logout(context, ref),
              ),
            ],
          ),

          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 20, 16, 100),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                // ── 个人统计卡片 ────────────────────────────────────
                _PersonalStatsRow(isDark: isDark),
                const SizedBox(height: 24),

                // ── 外观主题 ────────────────────────────────────────
                _SectionCard(isDark: isDark, children: [
                  _SettingsTile(
                    isDark: isDark,
                    icon: Icons.palette_outlined,
                    iconColor: AppColors.accent,
                    title: '外观主题',
                    trailing: _ThemePicker(
                      current: themeMode,
                      onChanged: (mode) =>
                          ref.read(themeModeProvider.notifier).setMode(mode),
                    ),
                  ),
                ]),
                const SizedBox(height: 12),

                // ── 系统介绍 showcase ────────────────────────────────
                _ShowcaseBanner(isDark: isDark),
                const SizedBox(height: 12),

                // ── 关于 + 退出 ─────────────────────────────────────
                _SectionCard(isDark: isDark, children: [
                  _SettingsTile(
                    isDark: isDark,
                    icon: Icons.info_outline_rounded,
                    iconColor: AppColors.secondary,
                    title: '关于应用',
                    trailing: const Icon(Icons.chevron_right_rounded,
                        color: AppColors.textMuted, size: 20),
                    onTap: () => context.push('/profile/about'),
                  ),
                  _Divider(isDark: isDark),
                  _SettingsTile(
                    isDark: isDark,
                    icon: Icons.logout_rounded,
                    iconColor: AppColors.error,
                    title: '退出登录',
                    titleColor: AppColors.error,
                    onTap: () => _logout(context, ref),
                  ),
                ]),

                // ── 管理员专区 ──────────────────────────────────────
                if (isAdmin) ...[
                  const SizedBox(height: 28),
                  _AdminBadgeHeader(isDark: isDark),
                  const SizedBox(height: 16),

                  // 全站统计
                  _AdminStatsSection(isDark: isDark),
                  const SizedBox(height: 16),

                  // 模型配置
                  _ModelConfigSection(isDark: isDark),
                  const SizedBox(height: 16),

                  // 用户管理
                  _UserManagementSection(isDark: isDark),
                ],
              ]),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _logout(BuildContext context, WidgetRef ref) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape:
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('退出登录'),
        content: const Text('确定要退出当前账号吗？'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('取消')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style:
                FilledButton.styleFrom(backgroundColor: AppColors.error),
            child: const Text('退出'),
          ),
        ],
      ),
    );
    if (ok == true) {
      await ref.read(authStateProvider.notifier).logout();
      if (context.mounted) context.go('/login');
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Hero 区域
// ─────────────────────────────────────────────────────────────────────────────

class _HeroSection extends StatelessWidget {
  final dynamic user;
  const _HeroSection({this.user});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(gradient: AppGradients.hero),
      child: Stack(
        children: [
          Positioned(
            top: -40, right: -40,
            child: Container(
              width: 180, height: 180,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white.withAlpha(15),
              ),
            ),
          ),
          Positioned(
            bottom: -60, left: -60,
            child: Container(
              width: 220, height: 220,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white.withAlpha(10),
              ),
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(24, 56, 24, 24),
              child: Row(
                children: [
                  Container(
                    width: 72, height: 72,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: Colors.white.withAlpha(38),
                      border: Border.all(
                          color: Colors.white.withAlpha(77), width: 2),
                    ),
                    child: Center(
                      child: Text(
                        user?.username
                                .substring(0, 1)
                                .toUpperCase() ??
                            '?',
                        style: const TextStyle(
                          fontSize: 28,
                          fontWeight: FontWeight.w800,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          user?.username ?? '未知用户',
                          style: const TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                            letterSpacing: -0.3,
                          ),
                        ),
                        if (user?.email?.isNotEmpty == true) ...[
                          const SizedBox(height: 4),
                          Text(
                            user!.email,
                            style: TextStyle(
                              fontSize: 13,
                              color: Colors.white.withAlpha(179),
                            ),
                          ),
                        ],
                        const SizedBox(height: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            color: Colors.white.withAlpha(38),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                                color: Colors.white.withAlpha(51)),
                          ),
                          child: Text(
                            user?.isAdmin == true ? '✦  管理员' : '普通用户',
                            style: const TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: Colors.white),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 个人统计行（修正字段名）
// ─────────────────────────────────────────────────────────────────────────────

class _PersonalStatsRow extends StatelessWidget {
  final bool isDark;
  const _PersonalStatsRow({required this.isDark});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Map<String, dynamic>>(
      future: StatsService().getOverview(),
      builder: (_, snap) {
        final data = snap.data ?? {};
        return Row(
          children: [
            Expanded(
              child: _StatCard(
                label: '总提问',
                value: data['questions']?.toString() ?? '--',
                gradient: AppGradients.cardBlue,
                icon: Icons.chat_bubble_rounded,
                isDark: isDark,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _StatCard(
                label: '收藏数',
                value: data['favorites']?.toString() ?? '--',
                gradient: AppGradients.cardAmber,
                icon: Icons.bookmark_rounded,
                isDark: isDark,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _StatCard(
                label: '会话数',
                value: data['conversations']?.toString() ?? '--',
                gradient: AppGradients.cardGreen,
                icon: Icons.forum_rounded,
                isDark: isDark,
              ),
            ),
          ],
        );
      },
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 管理员专区分隔标题
// ─────────────────────────────────────────────────────────────────────────────

class _AdminBadgeHeader extends StatelessWidget {
  final bool isDark;
  const _AdminBadgeHeader({required this.isDark});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF7C3AED), Color(0xFFDB2777)],
            ),
            borderRadius: BorderRadius.circular(20),
          ),
          child: const Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.admin_panel_settings_rounded,
                  color: Colors.white, size: 14),
              SizedBox(width: 5),
              Text('管理员控制台',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w700)),
            ],
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Divider(
            color:
                isDark ? const Color(0xFF1E293B) : const Color(0xFFEEF2FF),
          ),
        ),
      ],
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 全站统计
// ─────────────────────────────────────────────────────────────────────────────

class _AdminStatsSection extends StatefulWidget {
  final bool isDark;
  const _AdminStatsSection({required this.isDark});

  @override
  State<_AdminStatsSection> createState() => _AdminStatsSectionState();
}

class _AdminStatsSectionState extends State<_AdminStatsSection> {
  Map<String, dynamic>? _data;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    AdminService().getStatsOverview().then((d) {
      if (mounted) setState(() { _data = d; _loading = false; });
    }).catchError((_) {
      if (mounted) setState(() => _loading = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    final d = _data ?? {};
    final kb = d['knowledge_base'] as Map? ?? {};
    final fb = d['feedback'] as Map? ?? {};

    return _SectionCard(isDark: widget.isDark, children: [
      _SectionHeader(
          icon: Icons.bar_chart_rounded,
          title: '系统总览',
          color: const Color(0xFF7C3AED)),
      if (_loading)
        const Padding(
          padding: EdgeInsets.all(20),
          child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
        )
      else ...[
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
          child: Column(
            children: [
              Row(children: [
                _AdminStatTile(
                    icon: Icons.people_rounded,
                    label: '注册用户',
                    value: d['total_users']?.toString() ?? '--',
                    color: const Color(0xFF7C3AED)),
                const SizedBox(width: 10),
                _AdminStatTile(
                    icon: Icons.chat_rounded,
                    label: '总提问',
                    value: d['total_questions']?.toString() ?? '--',
                    color: AppColors.primary),
              ]),
              const SizedBox(height: 10),
              Row(children: [
                _AdminStatTile(
                    icon: Icons.history_rounded,
                    label: '检索记录',
                    value: d['total_searches']?.toString() ?? '--',
                    color: const Color(0xFFF59E0B)),
                const SizedBox(width: 10),
                _AdminStatTile(
                    icon: Icons.bookmark_rounded,
                    label: '总收藏',
                    value: d['total_favorites']?.toString() ?? '--',
                    color: AppColors.success),
              ]),
              const SizedBox(height: 10),
              Row(children: [
                _AdminStatTile(
                    icon: Icons.description_rounded,
                    label: '文档数',
                    value: kb['document_count']?.toString() ?? '--',
                    color: const Color(0xFF0891B2)),
                const SizedBox(width: 10),
                _AdminStatTile(
                    icon: Icons.grid_view_rounded,
                    label: '向量块数',
                    value: kb['chunk_count']?.toString() ?? '--',
                    color: const Color(0xFF059669)),
              ]),
              if (fb['total'] != null && (fb['total'] as int) > 0) ...[
                const SizedBox(height: 10),
                _FeedbackBar(
                    helpful: fb['helpful'] as int? ?? 0,
                    total: fb['total'] as int? ?? 1,
                    rate: (fb['helpful_rate'] as num?)?.toDouble() ?? 0),
              ],
            ],
          ),
        ),
      ],
    ]);
  }
}

class _AdminStatTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;
  const _AdminStatTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: color.withAlpha(13),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withAlpha(40)),
        ),
        child: Row(
          children: [
            Icon(icon, size: 18, color: color),
            const SizedBox(width: 8),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(value,
                    style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w800,
                        color: color)),
                Text(label,
                    style: const TextStyle(
                        fontSize: 11, color: AppColors.textMuted)),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _FeedbackBar extends StatelessWidget {
  final int helpful;
  final int total;
  final double rate;
  const _FeedbackBar(
      {required this.helpful,
      required this.total,
      required this.rate});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.success.withAlpha(13),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.success.withAlpha(40)),
      ),
      child: Row(
        children: [
          const Icon(Icons.thumb_up_rounded,
              size: 16, color: AppColors.success),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('用户满意度',
                        style: const TextStyle(
                            fontSize: 12,
                            color: AppColors.textSecondary)),
                    Text('$helpful/$total  (${rate.toStringAsFixed(1)}%)',
                        style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: AppColors.success)),
                  ],
                ),
                const SizedBox(height: 4),
                ClipRRect(
                  borderRadius: BorderRadius.circular(3),
                  child: LinearProgressIndicator(
                    value: rate / 100,
                    minHeight: 4,
                    backgroundColor: const Color(0xFFE0E7FF),
                    valueColor: const AlwaysStoppedAnimation<Color>(
                        AppColors.success),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 模型配置
// ─────────────────────────────────────────────────────────────────────────────

class _ModelConfigSection extends StatefulWidget {
  final bool isDark;
  const _ModelConfigSection({required this.isDark});

  @override
  State<_ModelConfigSection> createState() => _ModelConfigSectionState();
}

class _ModelConfigSectionState extends State<_ModelConfigSection> {
  Map<String, dynamic>? _data;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    AdminService().getModelConfig().then((d) {
      if (mounted) setState(() { _data = d; _loading = false; });
    }).catchError((_) {
      if (mounted) setState(() => _loading = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    final d = _data ?? {};
    final embed = d['embedding_model'] as Map? ?? {};
    final overrides = d['overrides'] as Map? ?? {};
    final available =
        (d['available_embedding_models'] as List?)?.cast<String>() ?? [];

    // 后端字段名: model_name / embedding_dim
    final rawEmbedName = embed['model_name']?.toString() ?? '';
    // model_name 可能是路径 (model/bge-m3)，只取最后一段
    final embedName = rawEmbedName.isNotEmpty
        ? rawEmbedName.split('/').last.split('\\').last
        : '--';
    final embedDim = embed['embedding_dim'];
    final embedType = embed['model_type']?.toString() ?? '';
    final isLoaded = embed['is_loaded'] as bool? ?? false;

    String llmDisplay() {
      final provider = d['llm_provider'] ?? '';
      if (provider == 'minimax') {
        return 'MiniMax / ${d['minimax_model_name'] ?? ''}';
      }
      return '${provider.toString().toUpperCase()} / ${d['llm_model_name'] ?? ''}';
    }

    return _SectionCard(isDark: widget.isDark, children: [
      _SectionHeader(
          icon: Icons.memory_rounded,
          title: '模型配置',
          color: const Color(0xFF0891B2)),
      if (_loading)
        const Padding(
          padding: EdgeInsets.all(20),
          child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
        )
      else
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // LLM 配置
              _ConfigGroup(
                title: '语言模型',
                isDark: widget.isDark,
                children: [
                  _ConfigRow(
                    icon: Icons.smart_toy_rounded,
                    label: 'LLM 模型',
                    value: llmDisplay(),
                    color: AppColors.primary,
                    isOverridden: overrides.containsKey('llm_provider') ||
                        overrides.containsKey('llm_model_name'),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              // 嵌入模型配置
              _ConfigGroup(
                title: '嵌入模型',
                isDark: widget.isDark,
                children: [
                  _ConfigRow(
                    icon: Icons.blur_on_rounded,
                    label: '模型名称',
                    value: embedName,
                    color: const Color(0xFF0891B2),
                    badge: isLoaded ? '已加载' : null,
                    badgeColor: AppColors.success,
                  ),
                  if (embedType.isNotEmpty)
                    _ConfigRow(
                      icon: Icons.category_outlined,
                      label: '模型类型',
                      value: embedType == 'sentence_transformers'
                          ? 'SentenceTransformer'
                          : embedType,
                      color: const Color(0xFF7C3AED),
                    ),
                  if (embedDim != null)
                    _ConfigRow(
                      icon: Icons.straighten_rounded,
                      label: '向量维度',
                      value: '$embedDim 维',
                      color: const Color(0xFF059669),
                    ),
                  _ConfigRow(
                    icon: Icons.storage_rounded,
                    label: 'ChromaDB 集合',
                    value: d['chroma_collection']?.toString() ?? '--',
                    color: const Color(0xFFF59E0B),
                  ),
                ],
              ),
              if (available.isNotEmpty) ...[
                const SizedBox(height: 12),
                _AvailableModels(models: available),
              ],
            ],
          ),
        ),
    ]);
  }
}

/// 分组容器，带标题分隔线
class _ConfigGroup extends StatelessWidget {
  final String title;
  final List<Widget> children;
  final bool isDark;
  const _ConfigGroup(
      {required this.title,
      required this.children,
      required this.isDark});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Text(
            title,
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: isDark
                  ? Colors.white54
                  : AppColors.textMuted,
              letterSpacing: 0.5,
            ),
          ),
        ),
        ...children.indexed.map((entry) {
          final idx = entry.$1;
          final child = entry.$2;
          // 相邻行之间 1px 间隔，靠圆角+border实现视觉分隔
          final isFirst = idx == 0;
          final isLast = idx == children.length - 1;
          return Padding(
            padding: EdgeInsets.only(bottom: isLast ? 0 : 2),
            child: _GroupedRowWrapper(
              child: child,
              isFirst: isFirst,
              isLast: isLast,
              isDark: isDark,
            ),
          );
        }),
      ],
    );
  }
}

class _GroupedRowWrapper extends StatelessWidget {
  final Widget child;
  final bool isFirst;
  final bool isLast;
  final bool isDark;
  const _GroupedRowWrapper(
      {required this.child,
      required this.isFirst,
      required this.isLast,
      required this.isDark});

  @override
  Widget build(BuildContext context) {
    final bg = isDark
        ? const Color(0xFF1E293B)
        : const Color(0xFFF8FAFC);
    return Container(
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.vertical(
          top: isFirst ? const Radius.circular(10) : Radius.zero,
          bottom: isLast ? const Radius.circular(10) : Radius.zero,
        ),
        border: Border(
          top: isFirst
              ? BorderSide(
                  color: isDark
                      ? Colors.white12
                      : const Color(0xFFE2E8F0))
              : BorderSide.none,
          bottom: BorderSide(
              color: isDark
                  ? Colors.white12
                  : const Color(0xFFE2E8F0)),
          left: BorderSide(
              color: isDark
                  ? Colors.white12
                  : const Color(0xFFE2E8F0)),
          right: BorderSide(
              color: isDark
                  ? Colors.white12
                  : const Color(0xFFE2E8F0)),
        ),
      ),
      child: child,
    );
  }
}

class _ConfigRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;
  final bool isOverridden;
  final String? badge;
  final Color? badgeColor;
  const _ConfigRow({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
    this.isOverridden = false,
    this.badge,
    this.badgeColor,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 8),
          // 标签固定左侧，不伸展
          Text(label,
              style: const TextStyle(
                  fontSize: 12, color: AppColors.textMuted)),
          // 右侧整体 Expanded：值文字 + 徽章，统一靠右对齐
          Expanded(
            child: Row(
              mainAxisAlignment: MainAxisAlignment.end,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Flexible(
                  child: Text(
                    value,
                    textAlign: TextAlign.end,
                    style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: color),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (isOverridden) ...[
                  const SizedBox(width: 6),
                  _BadgeChip(
                      label: '覆盖', color: const Color(0xFFF59E0B)),
                ],
                if (badge != null) ...[
                  const SizedBox(width: 6),
                  _BadgeChip(
                      label: badge!,
                      color: badgeColor ?? AppColors.success),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _BadgeChip extends StatelessWidget {
  final String label;
  final Color color;
  const _BadgeChip({required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withAlpha(26),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withAlpha(60)),
      ),
      child: Text(
        label,
        style: TextStyle(
            fontSize: 9, color: color, fontWeight: FontWeight.w700),
      ),
    );
  }
}

class _AvailableModels extends StatelessWidget {
  final List<String> models;
  const _AvailableModels({required this.models});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('本地可用嵌入模型',
            style: TextStyle(
                fontSize: 11,
                color: AppColors.textMuted,
                fontWeight: FontWeight.w600)),
        const SizedBox(height: 6),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: models
              .map((m) => Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF1F5F9),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                          color: const Color(0xFFE2E8F0)),
                    ),
                    child: Text(m,
                        style: const TextStyle(
                            fontSize: 11,
                            color: AppColors.textSecondary)),
                  ))
              .toList(),
        ),
      ],
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 用户管理
// ─────────────────────────────────────────────────────────────────────────────

class _UserManagementSection extends StatefulWidget {
  final bool isDark;
  const _UserManagementSection({required this.isDark});

  @override
  State<_UserManagementSection> createState() =>
      _UserManagementSectionState();
}

class _UserManagementSectionState extends State<_UserManagementSection> {
  List<Map<String, dynamic>> _users = [];
  int _total = 0;
  bool _loading = true;
  final _searchCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  Future<void> _load({String keyword = ''}) async {
    setState(() => _loading = true);
    try {
      final resp = await AdminService()
          .getUsers(keyword: keyword, pageSize: 10);
      final items =
          (resp['items'] as List?)?.cast<Map<String, dynamic>>() ?? [];
      if (mounted) {
        setState(() {
          _users = items;
          _total = resp['total'] as int? ?? 0;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _toggle(String userId, bool currentActive) async {
    await AdminService().toggleUserActive(userId);
    _load(keyword: _searchCtrl.text);
  }

  Future<void> _delete(BuildContext context, String userId, String name) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape:
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('删除用户'),
        content: Text('确定要删除用户「$name」吗？此操作不可撤销。'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('取消')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style:
                FilledButton.styleFrom(backgroundColor: AppColors.error),
            child: const Text('删除'),
          ),
        ],
      ),
    );
    if (ok == true) {
      await AdminService().deleteUser(userId);
      if (mounted) _load(keyword: _searchCtrl.text);
    }
  }

  @override
  Widget build(BuildContext context) {
    return _SectionCard(isDark: widget.isDark, children: [
      _SectionHeader(
          icon: Icons.manage_accounts_rounded,
          title: '用户管理  ($_total 人)',
          color: const Color(0xFFDB2777)),
      // 搜索框
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
        child: TextField(
          controller: _searchCtrl,
          onChanged: (v) => _load(keyword: v),
          style: const TextStyle(fontSize: 13),
          decoration: InputDecoration(
            hintText: '搜索用户名…',
            hintStyle: const TextStyle(fontSize: 13),
            prefixIcon: const Icon(Icons.search_rounded,
                size: 18, color: AppColors.textMuted),
            filled: true,
            fillColor: widget.isDark
                ? AppColors.surfaceVariantDark
                : const Color(0xFFF8FAFF),
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide.none,
            ),
          ),
        ),
      ),
      if (_loading)
        const Padding(
          padding: EdgeInsets.all(20),
          child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
        )
      else if (_users.isEmpty)
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 20),
          child: Center(
              child: Text('暂无用户',
                  style: TextStyle(color: AppColors.textMuted))),
        )
      else
        ListView.separated(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: _users.length,
          separatorBuilder: (_, __) => Divider(
            height: 1,
            indent: 16,
            endIndent: 16,
            color: widget.isDark
                ? const Color(0xFF1E293B)
                : const Color(0xFFEEF2FF),
          ),
          itemBuilder: (ctx, i) {
            final u = _users[i];
            final isActive = u['is_active'] as bool? ?? true;
            final role = u['role'] as String? ?? 'user';
            final createdAt = u['created_at'] as String?;
            final qCount = u['question_count'] as int? ?? 0;
            final fCount = u['favorite_count'] as int? ?? 0;
            return ListTile(
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              leading: CircleAvatar(
                radius: 18,
                backgroundColor:
                    (role == 'admin' ? const Color(0xFF7C3AED) : AppColors.primary)
                        .withAlpha(26),
                child: Text(
                  (u['username'] as String? ?? '?')
                      .substring(0, 1)
                      .toUpperCase(),
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: role == 'admin'
                        ? const Color(0xFF7C3AED)
                        : AppColors.primary,
                  ),
                ),
              ),
              title: Row(
                children: [
                  Expanded(
                    child: Text(
                      u['username'] as String? ?? '',
                      style: const TextStyle(
                          fontSize: 13, fontWeight: FontWeight.w600),
                    ),
                  ),
                  if (role == 'admin')
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFF7C3AED).withAlpha(26),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Text('管理员',
                          style: TextStyle(
                              fontSize: 9,
                              color: Color(0xFF7C3AED),
                              fontWeight: FontWeight.w700)),
                    ),
                ],
              ),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '提问 $qCount  收藏 $fCount${createdAt != null ? '  注册 ${_fmtDate(createdAt)}' : ''}',
                    style: const TextStyle(
                        fontSize: 11, color: AppColors.textMuted),
                  ),
                ],
              ),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // 启用/禁用
                  GestureDetector(
                    onTap: () => _toggle(
                        u['id'].toString(), isActive),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: isActive
                            ? AppColors.success.withAlpha(26)
                            : AppColors.error.withAlpha(26),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        isActive ? '正常' : '禁用',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: isActive
                              ? AppColors.success
                              : AppColors.error,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  // 删除
                  GestureDetector(
                    onTap: () => _delete(ctx, u['id'].toString(),
                        u['username']?.toString() ?? ''),
                    child: const Icon(Icons.delete_outline_rounded,
                        size: 18, color: AppColors.error),
                  ),
                ],
              ),
            );
          },
        ),
      if (_total > 10)
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
          child: Text('显示前 10 条，共 $_total 人',
              style: const TextStyle(
                  fontSize: 11, color: AppColors.textMuted)),
        ),
      const SizedBox(height: 4),
    ]);
  }

  String _fmtDate(String iso) {
    try {
      return DateFormat('yy/MM/dd').format(DateTime.parse(iso));
    } catch (_) {
      return iso;
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 通用子组件
// ─────────────────────────────────────────────────────────────────────────────

class _SectionHeader extends StatelessWidget {
  final IconData icon;
  final String title;
  final Color color;
  const _SectionHeader(
      {required this.icon, required this.title, required this.color});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: color.withAlpha(26),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, size: 14, color: color),
          ),
          const SizedBox(width: 8),
          Text(title,
              style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: color)),
        ],
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final LinearGradient gradient;
  final IconData icon;
  final bool isDark;

  const _StatCard({
    required this.label,
    required this.value,
    required this.gradient,
    required this.icon,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 12),
      decoration: BoxDecoration(
        color: isDark ? AppColors.surfaceDark : Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isDark
              ? const Color(0xFF1E293B)
              : const Color(0xFFEEF2FF),
        ),
        boxShadow: isDark
            ? null
            : [
                BoxShadow(
                  color: AppColors.primary.withAlpha(13),
                  blurRadius: 16,
                  offset: const Offset(0, 4),
                )
              ],
      ),
      child: Column(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              gradient: gradient,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: Colors.white, size: 20),
          ),
          const SizedBox(height: 10),
          Text(
            value,
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w800,
              color: isDark
                  ? const Color(0xFFF1F5F9)
                  : AppColors.textPrimary,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 2),
          Text(label,
              style: const TextStyle(
                  fontSize: 12, color: AppColors.textMuted)),
        ],
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  final bool isDark;
  final List<Widget> children;

  const _SectionCard({required this.isDark, required this.children});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: isDark ? AppColors.surfaceDark : Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isDark
              ? const Color(0xFF1E293B)
              : const Color(0xFFEEF2FF),
        ),
        boxShadow: isDark
            ? null
            : [
                BoxShadow(
                  color: AppColors.primary.withAlpha(10),
                  blurRadius: 16,
                  offset: const Offset(0, 3),
                )
              ],
      ),
      child: Column(children: children),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  final bool isDark;
  final IconData icon;
  final Color iconColor;
  final String title;
  final Color? titleColor;
  final Widget? trailing;
  final VoidCallback? onTap;

  const _SettingsTile({
    required this.isDark,
    required this.icon,
    required this.iconColor,
    required this.title,
    this.titleColor,
    this.trailing,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      onTap: onTap,
      shape:
          RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      contentPadding:
          const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      leading: Container(
        width: 36,
        height: 36,
        decoration: BoxDecoration(
          color: iconColor.withAlpha(26),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Icon(icon, color: iconColor, size: 18),
      ),
      title: Text(
        title,
        style: TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.w500,
          color: titleColor ??
              (isDark
                  ? const Color(0xFFF1F5F9)
                  : AppColors.textPrimary),
        ),
      ),
      trailing: trailing,
    );
  }
}

// ── Showcase 横幅入口 ────────────────────────────────────────────────────────

class _ShowcaseBanner extends StatelessWidget {
  final bool isDark;
  const _ShowcaseBanner({required this.isDark});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => context.push('/profile/showcase'),
      child: Container(
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF1D4ED8), Color(0xFF7C3AED)],
          ),
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: AppColors.primary.withAlpha(60),
              blurRadius: 16,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        padding: const EdgeInsets.all(16),
        child: Row(children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: Colors.white.withAlpha(25),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.auto_awesome_rounded,
                color: Colors.white, size: 22),
          ),
          const SizedBox(width: 14),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('系统技术亮点 & RAG 架构',
                    style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                        fontSize: 14)),
                SizedBox(height: 3),
                Text('Self-RAG · 混合检索 · 流式回答 · RAGAS 评估',
                    style: TextStyle(
                        color: Colors.white70,
                        fontSize: 11)),
              ],
            ),
          ),
          const Icon(Icons.arrow_forward_ios_rounded,
              color: Colors.white54, size: 14),
        ]),
      ),
    );
  }
}

class _Divider extends StatelessWidget {
  final bool isDark;
  const _Divider({required this.isDark});

  @override
  Widget build(BuildContext context) => Divider(
        height: 1,
        color: isDark
            ? const Color(0xFF1E293B)
            : const Color(0xFFEEF2FF),
        indent: 56,
      );
}

// ─────────────────────────────────────────────────────────────────────────────
// 主题选择器
// ─────────────────────────────────────────────────────────────────────────────

class _ThemePicker extends StatelessWidget {
  final ThemeMode current;
  final ValueChanged<ThemeMode> onChanged;

  const _ThemePicker({required this.current, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        _ThemeBtn(
          icon: Icons.brightness_auto_rounded,
          selected: current == ThemeMode.system,
          tooltip: '跟随系统',
          onTap: () => onChanged(ThemeMode.system),
        ),
        const SizedBox(width: 4),
        _ThemeBtn(
          icon: Icons.light_mode_rounded,
          selected: current == ThemeMode.light,
          tooltip: '亮色',
          onTap: () => onChanged(ThemeMode.light),
        ),
        const SizedBox(width: 4),
        _ThemeBtn(
          icon: Icons.dark_mode_rounded,
          selected: current == ThemeMode.dark,
          tooltip: '暗色',
          onTap: () => onChanged(ThemeMode.dark),
        ),
      ],
    );
  }
}

class _ThemeBtn extends StatelessWidget {
  final IconData icon;
  final bool selected;
  final String tooltip;
  final VoidCallback onTap;

  const _ThemeBtn({
    required this.icon,
    required this.selected,
    required this.tooltip,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          width: 34,
          height: 34,
          decoration: BoxDecoration(
            color: selected ? AppColors.primary : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
            border: selected
                ? null
                : Border.all(color: AppColors.textMuted.withAlpha(51)),
          ),
          child: Icon(
            icon,
            size: 17,
            color: selected ? Colors.white : AppColors.textMuted,
          ),
        ),
      ),
    );
  }
}
