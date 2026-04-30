import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/favorite.dart';
import '../../providers/favorite_provider.dart';
import '../../widgets/common/app_loading.dart';
import '../../widgets/common/app_empty.dart';
import '../../widgets/common/app_error.dart';
import '../../widgets/chat/markdown_view.dart';
import '../../core/theme/app_theme.dart';

class FavoritesPage extends ConsumerStatefulWidget {
  const FavoritesPage({super.key});
  @override
  ConsumerState<FavoritesPage> createState() => _FavoritesPageState();
}

class _FavoritesPageState extends ConsumerState<FavoritesPage> {
  String _keyword = '';

  List<Favorite> _filtered(List<Favorite> all) {
    if (_keyword.isEmpty) return all;
    return all
        .where((f) =>
            f.question.contains(_keyword) || f.answer.contains(_keyword))
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(favoritesProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(title: const Text('我的收藏')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
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
                          color: const Color(0xFF1D4ED8).withAlpha(10),
                          blurRadius: 12,
                          offset: const Offset(0, 2),
                        )
                      ],
              ),
              child: TextField(
                onChanged: (v) => setState(() => _keyword = v),
                decoration: const InputDecoration(
                  hintText: '搜索收藏内容…',
                  prefixIcon: Icon(Icons.search_rounded, color: AppColors.textMuted),
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  contentPadding:
                      EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                ),
              ),
            ),
          ),
          Expanded(
            child: state.when(
              loading: () => const AppLoading(),
              error: (e, _) => AppError(
                message: e.toString(),
                onRetry: () => ref.refresh(favoritesProvider),
              ),
              data: (favorites) {
                final filtered = _filtered(favorites);
                if (filtered.isEmpty) {
                  return AppEmpty(
                    title: _keyword.isEmpty ? '暂无收藏' : '未找到相关收藏',
                    icon: Icons.bookmark_outline_rounded,
                    subtitle:
                        _keyword.isEmpty ? '在对话中长按消息可以收藏' : null,
                  );
                }
                return RefreshIndicator(
                  onRefresh: () =>
                      ref.read(favoritesProvider.notifier).refresh(),
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 100),
                    itemCount: filtered.length,
                    separatorBuilder: (_, __) =>
                        const SizedBox(height: 12),
                    itemBuilder: (_, i) => _FavoriteCard(
                      favorite: filtered[i],
                      index: i,
                      isDark: isDark,
                      onDelete: () => ref
                          .read(favoritesProvider.notifier)
                          .removeFavorite(filtered[i].id),
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _FavoriteCard extends StatelessWidget {
  final Favorite favorite;
  final int index;
  final bool isDark;
  final VoidCallback onDelete;

  const _FavoriteCard(
      {required this.favorite,
      required this.index,
      required this.isDark,
      required this.onDelete});

  @override
  Widget build(BuildContext context) {
    final gradient =
        AppGradients.avatarPalette[index % AppGradients.avatarPalette.length];

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
                  color: const Color(0xFF1D4ED8).withAlpha(13),
                  blurRadius: 16,
                  offset: const Offset(0, 4),
                )
              ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 渐变顶部条
          Container(
            height: 4,
            decoration: BoxDecoration(
              gradient: gradient,
              borderRadius:
                  const BorderRadius.vertical(top: Radius.circular(20)),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 问题行
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 32,
                      height: 32,
                      decoration: BoxDecoration(
                        gradient: gradient,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(Icons.help_rounded,
                          size: 16, color: Colors.white),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        favorite.question,
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: isDark
                              ? const Color(0xFFF1F5F9)
                              : AppColors.textPrimary,
                          height: 1.4,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.delete_outline_rounded,
                          size: 18, color: AppColors.error),
                      onPressed: onDelete,
                      visualDensity: VisualDensity.compact,
                      padding: EdgeInsets.zero,
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Container(
                  height: 1,
                  color: isDark
                      ? const Color(0xFF1E293B)
                      : const Color(0xFFEEF2FF),
                ),
                const SizedBox(height: 12),
                // 回答预览
                MarkdownView(data: favorite.answer),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
