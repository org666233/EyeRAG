import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../providers/chat_provider.dart';
import '../../widgets/common/app_loading.dart';
import '../../widgets/common/app_empty.dart';
import '../../widgets/common/app_error.dart';
import '../../core/theme/app_theme.dart';

class ChatListPage extends ConsumerWidget {
  const ChatListPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(conversationsProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      body: CustomScrollView(
        slivers: [
          // 渐变 AppBar
          SliverAppBar(
            expandedHeight: 140,
            floating: false,
            pinned: true,
            backgroundColor:
                isDark ? AppColors.backgroundDark : AppColors.primary,
            flexibleSpace: FlexibleSpaceBar(
              centerTitle: true,
              titlePadding:
                  const EdgeInsets.only(left: 20, bottom: 16, right: 20),
              title: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  const Text(
                    '智能问答',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.3,
                    ),
                  ),
                  _NewChatButton(
                      onTap: () => _createConversation(context, ref)),
                ],
              ),
              background: Container(
                decoration: isDark
                    ? BoxDecoration(
                        gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [
                          AppColors.primaryDark,
                          AppColors.surfaceVariantDark,
                        ],
                      ))
                    : const BoxDecoration(gradient: AppGradients.hero),
                child: Stack(
                  children: [
                    Positioned(
                      top: -30,
                      right: -30,
                      child: Container(
                        width: 150,
                        height: 150,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: Colors.white.withAlpha(15),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          // 内容区
          state.when(
            loading: () => const SliverFillRemaining(
              child: AppLoading(message: '加载对话列表…'),
            ),
            error: (e, _) => SliverFillRemaining(
              child: AppError(
                message: e.toString(),
                onRetry: () => ref.refresh(conversationsProvider),
              ),
            ),
            data: (conversations) {
              if (conversations.isEmpty) {
                return SliverFillRemaining(
                  child: AppEmpty(
                    title: '开始你的第一次问答',
                    subtitle: '点击右上角 + 提问眼科相关问题',
                    icon: Icons.chat_bubble_outline_rounded,
                    actionLabel: '新建对话',
                    onAction: () => _createConversation(context, ref),
                  ),
                );
              }
              return SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
                sliver: SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (ctx, i) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _ConversationCard(
                        conversation: conversations[i],
                        index: i,
                        onTap: () =>
                            context.push('/chat/${conversations[i].id}'),
                        onDelete: () => _confirmDelete(context, ref,
                            conversations[i].id),
                      ),
                    ),
                    childCount: conversations.length,
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  void _createConversation(BuildContext context, WidgetRef ref) {
    context.push('/chat/new');
  }

  Future<void> _confirmDelete(
      BuildContext context, WidgetRef ref, String id) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('删除对话'),
        content: const Text('确定要删除这条对话吗？'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('取消')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: AppColors.error),
            child: const Text('删除'),
          ),
        ],
      ),
    );
    if (ok == true) {
      ref.read(conversationsProvider.notifier).deleteConversation(id);
    }
  }
}

class _NewChatButton extends StatelessWidget {
  final VoidCallback onTap;
  const _NewChatButton({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
        decoration: BoxDecoration(
          color: Colors.white.withAlpha(38),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.white.withAlpha(77)),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.add_rounded, color: Colors.white, size: 16),
            SizedBox(width: 4),
            Text('新对话',
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }
}

class _ConversationCard extends StatelessWidget {
  final dynamic conversation;
  final int index;
  final VoidCallback onTap;
  final VoidCallback onDelete;

  const _ConversationCard({
    required this.conversation,
    required this.index,
    required this.onTap,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final gradient =
        AppGradients.avatarPalette[index % AppGradients.avatarPalette.length];

    return Dismissible(
      key: Key(conversation.id),
      direction: DismissDirection.endToStart,
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 24),
        decoration: BoxDecoration(
          color: AppColors.error.withAlpha(26),
          borderRadius: BorderRadius.circular(20),
        ),
        child: const Icon(Icons.delete_rounded, color: AppColors.error),
      ),
      confirmDismiss: (_) async {
        onDelete();
        return false;
      },
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(20),
          child: Container(
            padding: const EdgeInsets.all(16),
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
                        blurRadius: 20,
                        offset: const Offset(0, 4),
                      ),
                    ],
            ),
            child: Row(
              children: [
                // 渐变头像
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    gradient: gradient,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: const Icon(Icons.chat_rounded,
                      color: Colors.white, size: 22),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        conversation.title,
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                          color: isDark
                              ? const Color(0xFFF1F5F9)
                              : AppColors.textPrimary,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        DateFormat('MM月dd日  HH:mm')
                            .format(conversation.updatedAt),
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),
                Icon(
                  Icons.chevron_right_rounded,
                  color: AppColors.textMuted.withAlpha(128),
                  size: 20,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
