import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../../models/search_history.dart';
import '../../providers/history_provider.dart';
import '../../services/history_service.dart';
import '../../widgets/common/app_loading.dart';
import '../../widgets/common/app_empty.dart';
import '../../widgets/common/app_error.dart';
import '../../core/theme/app_theme.dart';

// ── 检索决策过滤选项 ──────────────────────────────────────────────────────────
const _kFilters = [
  (value: '', label: '全部', icon: Icons.all_inclusive_rounded),
  (value: 'proceed', label: '正常检索', icon: Icons.check_circle_outline_rounded),
  (value: 'retry', label: '二次检索', icon: Icons.refresh_rounded),
  (value: 'fallback', label: '降级回答', icon: Icons.warning_amber_rounded),
];

Color _decisionColor(String decision) {
  switch (decision) {
    case 'proceed':
      return AppColors.success;
    case 'retry':
      return const Color(0xFFF59E0B);
    case 'fallback':
      return AppColors.error;
    default:
      return AppColors.textMuted;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 主页面
// ─────────────────────────────────────────────────────────────────────────────

class HistoryPage extends ConsumerStatefulWidget {
  const HistoryPage({super.key});

  @override
  ConsumerState<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends ConsumerState<HistoryPage> {
  final _searchCtrl = TextEditingController();

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  void _applyFilter({String? keyword, String? decision}) {
    final current = ref.read(historyFilterProvider);
    ref.read(historyFilterProvider.notifier).state = (
      keyword: keyword ?? current.keyword,
      decision: decision ?? current.decision,
    );
    ref.read(historyProvider.notifier).refresh();
  }

  String _groupLabel(DateTime dt) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final d = DateTime(dt.year, dt.month, dt.day);
    if (d == today) return '今天';
    if (d == today.subtract(const Duration(days: 1))) return '昨天';
    if (today.difference(d).inDays < 7) return '本周';
    return DateFormat('yyyy年 MM月').format(dt);
  }

  @override
  Widget build(BuildContext context) {
    final historyState = ref.watch(historyProvider);
    final filter = ref.watch(historyFilterProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('历史记录'),
        actions: [
          TextButton.icon(
            onPressed: () => _clearAll(context),
            icon: const Icon(Icons.delete_sweep_rounded, size: 18),
            label: const Text('清空'),
            style: TextButton.styleFrom(
              foregroundColor: AppColors.error,
              padding: const EdgeInsets.symmetric(horizontal: 12),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          // ── 搜索框 ─────────────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
            child: Container(
              decoration: BoxDecoration(
                color: isDark ? AppColors.surfaceVariantDark : Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: isDark
                      ? const Color(0xFF1E293B)
                      : const Color(0xFFE0E7FF),
                ),
                boxShadow: isDark
                    ? null
                    : [
                        BoxShadow(
                          color: AppColors.primary.withAlpha(10),
                          blurRadius: 12,
                          offset: const Offset(0, 2),
                        ),
                      ],
              ),
              child: TextField(
                controller: _searchCtrl,
                onChanged: (v) => _applyFilter(keyword: v),
                decoration: InputDecoration(
                  hintText: '搜索历史记录…',
                  prefixIcon: const Icon(Icons.search_rounded,
                      color: AppColors.textMuted),
                  suffixIcon: filter.keyword.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear_rounded,
                              size: 18, color: AppColors.textMuted),
                          onPressed: () {
                            _searchCtrl.clear();
                            _applyFilter(keyword: '');
                          },
                        )
                      : null,
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  contentPadding: const EdgeInsets.symmetric(
                      horizontal: 16, vertical: 14),
                ),
              ),
            ),
          ),

          // ── 检索决策过滤芯片 ──────────────────────────────────────────
          SizedBox(
            height: 52,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              itemCount: _kFilters.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (_, i) {
                final f = _kFilters[i];
                final selected = filter.decision == f.value;
                return GestureDetector(
                  onTap: () => _applyFilter(decision: f.value),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 6),
                    decoration: BoxDecoration(
                      gradient: selected
                          ? const LinearGradient(
                              colors: [AppColors.primary, AppColors.secondary],
                            )
                          : null,
                      color: selected
                          ? null
                          : (isDark
                              ? AppColors.surfaceVariantDark
                              : Colors.white),
                      borderRadius: BorderRadius.circular(20),
                      border: selected
                          ? null
                          : Border.all(
                              color: isDark
                                  ? const Color(0xFF1E293B)
                                  : const Color(0xFFE0E7FF),
                            ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(f.icon,
                            size: 14,
                            color: selected
                                ? Colors.white
                                : AppColors.textMuted),
                        const SizedBox(width: 4),
                        Text(
                          f.label,
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: selected
                                ? FontWeight.w600
                                : FontWeight.w400,
                            color: selected
                                ? Colors.white
                                : AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),

          // ── 统计栏 ─────────────────────────────────────────────────────
          if (historyState.valueOrNull?.isNotEmpty == true)
            _StatsBar(records: historyState.value!, isDark: isDark),

          // ── 列表 ───────────────────────────────────────────────────────
          Expanded(
            child: historyState.when(
              loading: () => const AppLoading(),
              error: (e, _) => AppError(
                message: e.toString(),
                onRetry: () =>
                    ref.read(historyProvider.notifier).refresh(),
              ),
              data: (history) {
                if (history.isEmpty) {
                  return const AppEmpty(
                    title: '暂无历史记录',
                    icon: Icons.history_rounded,
                    subtitle: '您的问答记录将显示在这里',
                  );
                }
                // 按日期分组
                final groups = <String, List<SearchHistory>>{};
                for (final h in history) {
                  final label = _groupLabel(h.createdAt);
                  groups.putIfAbsent(label, () => []).add(h);
                }
                return RefreshIndicator(
                  onRefresh: () =>
                      ref.read(historyProvider.notifier).refresh(),
                  child: ListView(
                    padding:
                        const EdgeInsets.fromLTRB(16, 0, 16, 100),
                    children: groups.entries.expand((entry) sync* {
                      yield _GroupHeader(label: entry.key);
                      for (final h in entry.value) {
                        yield Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: _HistoryCard(
                            history: h,
                            isDark: isDark,
                            onDelete: () => ref
                                .read(historyProvider.notifier)
                                .deleteRecord(h.id),
                            onRate: (r) => ref
                                .read(historyProvider.notifier)
                                .rateRecord(h.id, r),
                            onTap: () =>
                                _showDetail(context, h.id),
                          ),
                        );
                      }
                    }).toList(),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _showDetail(BuildContext context, String id) async {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _DetailSheet(id: id),
    );
  }

  Future<void> _clearAll(BuildContext context) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape:
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('清空历史'),
        content: const Text('确定要清空所有历史记录吗？此操作不可撤销。'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('取消')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style:
                FilledButton.styleFrom(backgroundColor: AppColors.error),
            child: const Text('清空'),
          ),
        ],
      ),
    );
    if (ok == true && mounted) {
      await ref.read(historyProvider.notifier).clearAll();
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 统计栏
// ─────────────────────────────────────────────────────────────────────────────

class _StatsBar extends StatelessWidget {
  final List<SearchHistory> records;
  final bool isDark;
  const _StatsBar({required this.records, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final total = records.length;
    final proceeds =
        records.where((r) => r.retrievalDecision == 'proceed').length;
    final retries =
        records.where((r) => r.retrievalDecision == 'retry').length;
    final fallbacks =
        records.where((r) => r.retrievalDecision == 'fallback').length;
    final avgMs = records
            .where((r) => r.responseTimeMs != null)
            .map((r) => r.responseTimeMs!)
            .fold<double>(0, (a, b) => a + b) /
        (records.where((r) => r.responseTimeMs != null).length
            .clamp(1, double.infinity));

    return Container(
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 4),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: isDark ? AppColors.surfaceVariantDark : const Color(0xFFF0F4FF),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _StatItem(value: '$total', label: '总记录', color: AppColors.primary),
          _StatItem(
              value: '$proceeds',
              label: '正常检索',
              color: AppColors.success),
          _StatItem(
              value: '$retries',
              label: '二次检索',
              color: const Color(0xFFF59E0B)),
          _StatItem(
              value: '$fallbacks',
              label: '降级回答',
              color: AppColors.error),
          _StatItem(
              value: '${(avgMs / 1000).toStringAsFixed(1)}s',
              label: '均耗时',
              color: AppColors.secondary),
        ],
      ),
    );
  }
}

class _StatItem extends StatelessWidget {
  final String value;
  final String label;
  final Color color;
  const _StatItem(
      {required this.value, required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(value,
            style: TextStyle(
                fontSize: 16, fontWeight: FontWeight.w800, color: color)),
        const SizedBox(height: 2),
        Text(label,
            style: const TextStyle(
                fontSize: 10, color: AppColors.textMuted)),
      ],
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 分组标题
// ─────────────────────────────────────────────────────────────────────────────

class _GroupHeader extends StatelessWidget {
  final String label;
  const _GroupHeader({required this.label});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 16, bottom: 8),
      child: Row(
        children: [
          Container(
            width: 4,
            height: 14,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [AppColors.primary, AppColors.secondary],
              ),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(width: 8),
          Text(label,
              style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: AppColors.primary,
                  letterSpacing: 0.3)),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 历史记录卡片
// ─────────────────────────────────────────────────────────────────────────────

class _HistoryCard extends StatelessWidget {
  final SearchHistory history;
  final bool isDark;
  final VoidCallback onDelete;
  final ValueChanged<int> onRate;
  final VoidCallback onTap;

  const _HistoryCard({
    required this.history,
    required this.isDark,
    required this.onDelete,
    required this.onRate,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final decisionColor = _decisionColor(history.retrievalDecision);

    return Dismissible(
      key: Key(history.id),
      direction: DismissDirection.endToStart,
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        decoration: BoxDecoration(
          color: AppColors.error.withAlpha(26),
          borderRadius: BorderRadius.circular(16),
        ),
        child: const Icon(Icons.delete_rounded, color: AppColors.error),
      ),
      onDismissed: (_) => onDelete(),
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: isDark ? AppColors.surfaceDark : Colors.white,
            borderRadius: BorderRadius.circular(16),
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
                      blurRadius: 10,
                      offset: const Offset(0, 2),
                    ),
                  ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 问题行 + 时间
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 28,
                    height: 28,
                    decoration: BoxDecoration(
                      color: AppColors.primary.withAlpha(26),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.help_outline_rounded,
                        size: 15, color: AppColors.primary),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      history.question,
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: isDark
                            ? const Color(0xFFF1F5F9)
                            : AppColors.textPrimary,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    DateFormat('HH:mm').format(history.createdAt),
                    style: const TextStyle(
                        fontSize: 11, color: AppColors.textMuted),
                  ),
                ],
              ),

              // 回答预览
              if (history.answer.isNotEmpty) ...[
                const SizedBox(height: 8),
                Padding(
                  padding: const EdgeInsets.only(left: 38),
                  child: Text(
                    history.answer,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 13,
                      color: AppColors.textSecondary,
                      height: 1.5,
                    ),
                  ),
                ),
              ],

              const SizedBox(height: 10),

              // 元信息行
              Padding(
                padding: const EdgeInsets.only(left: 38),
                child: Row(
                  children: [
                    // 检索决策徽标
                    _DecisionBadge(
                        label: history.decisionLabel,
                        color: decisionColor),
                    const SizedBox(width: 8),
                    // 文档块数
                    if (history.contextCount > 0) ...[
                      Icon(Icons.description_outlined,
                          size: 12, color: AppColors.textMuted),
                      const SizedBox(width: 3),
                      Text('${history.contextCount} 块',
                          style: const TextStyle(
                              fontSize: 11,
                              color: AppColors.textMuted)),
                      const SizedBox(width: 8),
                    ],
                    // 耗时
                    if (history.responseTimeMs != null) ...[
                      Icon(Icons.timer_outlined,
                          size: 12, color: AppColors.textMuted),
                      const SizedBox(width: 3),
                      Text(
                          '${(history.responseTimeMs! / 1000).toStringAsFixed(1)}s',
                          style: const TextStyle(
                              fontSize: 11,
                              color: AppColors.textMuted)),
                    ],
                    const Spacer(),
                    // 评分按钮
                    _RatingButtons(
                      rating: history.rating,
                      onRate: onRate,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DecisionBadge extends StatelessWidget {
  final String label;
  final Color color;
  const _DecisionBadge({required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withAlpha(26),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withAlpha(77)),
      ),
      child: Text(label,
          style: TextStyle(
              fontSize: 11, color: color, fontWeight: FontWeight.w600)),
    );
  }
}

class _RatingButtons extends StatelessWidget {
  final int? rating;
  final ValueChanged<int> onRate;
  const _RatingButtons({required this.rating, required this.onRate});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        GestureDetector(
          onTap: () => onRate(1),
          child: Icon(
            rating == 1
                ? Icons.thumb_up_rounded
                : Icons.thumb_up_outlined,
            size: 16,
            color: rating == 1 ? AppColors.success : AppColors.textMuted,
          ),
        ),
        const SizedBox(width: 10),
        GestureDetector(
          onTap: () => onRate(0),
          child: Icon(
            rating == 0
                ? Icons.thumb_down_rounded
                : Icons.thumb_down_outlined,
            size: 16,
            color: rating == 0 ? AppColors.error : AppColors.textMuted,
          ),
        ),
      ],
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 详情底部面板
// ─────────────────────────────────────────────────────────────────────────────

class _DetailSheet extends StatefulWidget {
  final String id;
  const _DetailSheet({required this.id});

  @override
  State<_DetailSheet> createState() => _DetailSheetState();
}

class _DetailSheetState extends State<_DetailSheet> {
  SearchHistory? _detail;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadDetail();
  }

  Future<void> _loadDetail() async {
    try {
      final detail = await HistoryService().getDetail(widget.id);
      if (mounted) setState(() { _detail = detail; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.85,
      minChildSize: 0.4,
      maxChildSize: 0.95,
      builder: (_, ctrl) => Container(
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: Column(
          children: [
            // 拖拽把手
            Container(
              margin: const EdgeInsets.only(top: 12, bottom: 8),
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: const Color(0xFFCBD5E1),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            // 标题栏
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 12, 8),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [AppColors.primary, AppColors.secondary],
                      ),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.analytics_rounded,
                        color: Colors.white, size: 16),
                  ),
                  const SizedBox(width: 10),
                  const Text('检索详情',
                      style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                          color: AppColors.textPrimary)),
                  const Spacer(),
                  IconButton(
                    icon: const Icon(Icons.close_rounded),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            // 内容
            Expanded(
              child: _loading
                  ? const AppLoading()
                  : _error != null
                      ? Center(
                          child: Text(_error!,
                              style: const TextStyle(
                                  color: AppColors.textMuted)))
                      : _DetailContent(
                          detail: _detail!, controller: ctrl),
            ),
          ],
        ),
      ),
    );
  }
}

class _DetailContent extends StatelessWidget {
  final SearchHistory detail;
  final ScrollController controller;
  const _DetailContent(
      {required this.detail, required this.controller});

  @override
  Widget build(BuildContext context) {
    final decisionColor = _decisionColor(detail.retrievalDecision);

    return ListView(
      controller: controller,
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 40),
      children: [
        // ── 用户问题 ────────────────────────────────────────────────
        _SectionTitle(icon: Icons.help_outline_rounded, title: '用户问题'),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: const Color(0xFFF0F4FF),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(detail.question,
              style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                  height: 1.5)),
        ),

        const SizedBox(height: 20),

        // ── 检索决策 ────────────────────────────────────────────────
        _SectionTitle(
            icon: Icons.policy_outlined, title: '检索决策'),
        const SizedBox(height: 8),
        Row(
          children: [
            _DecisionBadge(
                label: detail.decisionLabel, color: decisionColor),
            const SizedBox(width: 10),
            if (detail.contextCount > 0)
              _MetaChip(
                  icon: Icons.description_outlined,
                  label: '${detail.contextCount} 个文档块'),
            const SizedBox(width: 8),
            if (detail.responseTimeMs != null)
              _MetaChip(
                  icon: Icons.timer_outlined,
                  label:
                      '${(detail.responseTimeMs! / 1000).toStringAsFixed(2)}s'),
          ],
        ),
        if (detail.decisionReason != null &&
            detail.decisionReason!.isNotEmpty) ...[
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: decisionColor.withAlpha(15),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: decisionColor.withAlpha(50)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.info_outline_rounded,
                    size: 14, color: decisionColor),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    detail.decisionReason!,
                    style: TextStyle(
                        fontSize: 12,
                        color: decisionColor,
                        height: 1.5),
                  ),
                ),
              ],
            ),
          ),
        ],

        // ── 检索到的文档块 ──────────────────────────────────────────
        if (detail.searchResults != null &&
            detail.searchResults!.isNotEmpty) ...[
          const SizedBox(height: 20),
          _SectionTitle(
              icon: Icons.search_rounded,
              title: '检索文档块（${detail.searchResults!.length} 个）'),
          const SizedBox(height: 8),
          ...detail.searchResults!.asMap().entries.map((entry) {
            final i = entry.key;
            final sr = entry.value as Map<String, dynamic>;
            final meta = sr['metadata'] as Map<String, dynamic>? ?? {};
            final title = meta['title'] as String? ??
                meta['file_name'] as String? ??
                '未知来源';
            final score = (sr['rrf_score'] as num?)?.toDouble() ?? 0;
            final rtype = sr['retrieval_type'] as String? ?? '';
            final content = sr['content'] as String? ?? '';
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: _DocChunk(
                index: i + 1,
                title: title,
                score: score,
                retrievalType: rtype,
                content: content,
              ),
            );
          }),
        ],

        // ── 引用来源 ────────────────────────────────────────────────
        if (detail.sources.isNotEmpty) ...[
          const SizedBox(height: 20),
          _SectionTitle(
              icon: Icons.link_rounded,
              title: '引用来源（${detail.sources.length} 个）'),
          const SizedBox(height: 8),
          ...detail.sources.asMap().entries.map((entry) {
            final i = entry.key;
            final src = entry.value as Map<String, dynamic>;
            final title = src['title'] as String? ?? '未知来源';
            final score = (src['score'] as num?)?.toDouble() ?? 0;
            return Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: _SourceItem(
                  index: i + 1, title: title, score: score),
            );
          }),
        ],

        // ── AI 回答 ─────────────────────────────────────────────────
        const SizedBox(height: 20),
        _SectionTitle(
            icon: Icons.smart_toy_outlined, title: 'AI 回答'),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: const Color(0xFFF8FAFF),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFFE0E7FF)),
          ),
          child: MarkdownBody(
            data: detail.answer,
            styleSheet: MarkdownStyleSheet(
              p: const TextStyle(
                  fontSize: 14,
                  color: AppColors.textPrimary,
                  height: 1.6),
              h2: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary),
              h3: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary),
              strong: const TextStyle(fontWeight: FontWeight.w700),
              code: const TextStyle(
                  fontSize: 12,
                  fontFamily: 'monospace',
                  backgroundColor: Color(0xFFEEF2FF)),
            ),
          ),
        ),
      ],
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 详情子组件
// ─────────────────────────────────────────────────────────────────────────────

class _SectionTitle extends StatelessWidget {
  final IconData icon;
  final String title;
  const _SectionTitle({required this.icon, required this.title});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 15, color: AppColors.primary),
        const SizedBox(width: 6),
        Text(title,
            style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w700,
                color: AppColors.primary)),
      ],
    );
  }
}

class _MetaChip extends StatelessWidget {
  final IconData icon;
  final String label;
  const _MetaChip({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 11, color: AppColors.textMuted),
        const SizedBox(width: 4),
        Text(label,
            style: const TextStyle(
                fontSize: 11, color: AppColors.textSecondary)),
      ]),
    );
  }
}

class _DocChunk extends StatefulWidget {
  final int index;
  final String title;
  final double score;
  final String retrievalType;
  final String content;
  const _DocChunk({
    required this.index,
    required this.title,
    required this.score,
    required this.retrievalType,
    required this.content,
  });

  @override
  State<_DocChunk> createState() => _DocChunkState();
}

class _DocChunkState extends State<_DocChunk> {
  bool _expanded = false;

  String get _typeLabel {
    switch (widget.retrievalType) {
      case 'hybrid':
        return '混合';
      case 'vector':
        return '向量';
      case 'bm25':
        return 'BM25';
      default:
        return widget.retrievalType;
    }
  }

  @override
  Widget build(BuildContext context) {
    final scorePercent = (widget.score * 100).clamp(0, 100);

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFF),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE0E7FF)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 标题行
          InkWell(
            onTap: () => setState(() => _expanded = !_expanded),
            borderRadius: BorderRadius.circular(12),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
              child: Row(
                children: [
                  Container(
                    width: 20,
                    height: 20,
                    decoration: BoxDecoration(
                      color: AppColors.primary.withAlpha(26),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Center(
                      child: Text('${widget.index}',
                          style: const TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: AppColors.primary)),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(widget.title,
                            style: const TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: AppColors.textPrimary),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis),
                        const SizedBox(height: 4),
                        Row(children: [
                          // 分数进度条
                          Expanded(
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(2),
                              child: LinearProgressIndicator(
                                value: scorePercent / 100,
                                minHeight: 3,
                                backgroundColor:
                                    const Color(0xFFE0E7FF),
                                valueColor:
                                    const AlwaysStoppedAnimation<Color>(
                                        AppColors.primary),
                              ),
                            ),
                          ),
                          const SizedBox(width: 6),
                          Text('${scorePercent.toStringAsFixed(1)}%',
                              style: const TextStyle(
                                  fontSize: 10,
                                  color: AppColors.primary,
                                  fontWeight: FontWeight.w600)),
                          if (_typeLabel.isNotEmpty) ...[
                            const SizedBox(width: 6),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 6, vertical: 1),
                              decoration: BoxDecoration(
                                color: AppColors.secondary.withAlpha(26),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(_typeLabel,
                                  style: const TextStyle(
                                      fontSize: 9,
                                      color: AppColors.secondary,
                                      fontWeight: FontWeight.w600)),
                            ),
                          ],
                        ]),
                      ],
                    ),
                  ),
                  Icon(
                    _expanded
                        ? Icons.expand_less_rounded
                        : Icons.expand_more_rounded,
                    size: 16,
                    color: AppColors.textMuted,
                  ),
                ],
              ),
            ),
          ),
          // 展开内容
          if (_expanded && widget.content.isNotEmpty)
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
              child: Text(
                widget.content,
                style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.textSecondary,
                    height: 1.5),
              ),
            ),
        ],
      ),
    );
  }
}

class _SourceItem extends StatelessWidget {
  final int index;
  final String title;
  final double score;
  const _SourceItem(
      {required this.index, required this.title, required this.score});

  @override
  Widget build(BuildContext context) {
    final scorePercent = (score * 100).clamp(0, 100);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.success.withAlpha(10),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.success.withAlpha(40)),
      ),
      child: Row(
        children: [
          Text('$index',
              style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: AppColors.success)),
          const SizedBox(width: 8),
          Expanded(
            child: Text(title,
                style: const TextStyle(
                    fontSize: 12, color: AppColors.textPrimary),
                maxLines: 1,
                overflow: TextOverflow.ellipsis),
          ),
          const SizedBox(width: 8),
          Text('${scorePercent.toStringAsFixed(1)}%',
              style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: AppColors.success)),
        ],
      ),
    );
  }
}
