import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../models/message.dart';
import '../../core/theme/app_theme.dart';
import 'markdown_view.dart';
import 'typing_animation.dart';

class MessageBubble extends StatelessWidget {
  final Message message;
  final bool isTyping;
  final VoidCallback? onFavorite;
  final VoidCallback? onShare;

  const MessageBubble({
    super.key,
    required this.message,
    this.isTyping = false,
    this.onFavorite,
    this.onShare,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final isUser = message.isUser;

    return Padding(
      padding: EdgeInsets.only(
        top: 6,
        bottom: 6,
        left: isUser ? 56 : 12,
        right: isUser ? 12 : 56,
      ),
      child: Column(
        crossAxisAlignment:
            isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          // 角色标签
          if (!isUser)
            Padding(
              padding: const EdgeInsets.only(left: 4, bottom: 6),
              child: Row(
                children: [
                  Container(
                    width: 24,
                    height: 24,
                    decoration: const BoxDecoration(
                      gradient: AppGradients.hero,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.visibility_rounded,
                        size: 13, color: Colors.white),
                  ),
                  const SizedBox(width: 6),
                  const Text('眼科助手',
                      style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textSecondary)),
                ],
              ),
            ),
          GestureDetector(
            onLongPress: () => _showActionMenu(context),
            child: isUser
                ? _UserBubble(text: message.content)
                : _AiBubble(
                    content: message.content,
                    isTyping: isTyping,
                    isDark: isDark,
                  ),
          ),
        ],
      ),
    );
  }

  void _showActionMenu(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (ctx) => _ActionSheet(
        isAssistant: message.isAssistant,
        content: message.content,
        onFavorite: onFavorite,
        onShare: onShare,
      ),
    );
  }
}

class _UserBubble extends StatelessWidget {
  final String text;
  const _UserBubble({required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.primary, AppColors.secondary],
        ),
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(20),
          topRight: Radius.circular(20),
          bottomLeft: Radius.circular(20),
          bottomRight: Radius.circular(4),
        ),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withAlpha(51),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Text(
        text,
        style: const TextStyle(
            color: Colors.white, fontSize: 15, height: 1.5),
      ),
    );
  }
}

class _AiBubble extends StatelessWidget {
  final String content;
  final bool isTyping;
  final bool isDark;

  const _AiBubble(
      {required this.content,
      required this.isTyping,
      required this.isDark});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: isDark ? AppColors.surfaceVariantDark : Colors.white,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(4),
          topRight: Radius.circular(20),
          bottomLeft: Radius.circular(20),
          bottomRight: Radius.circular(20),
        ),
        border: Border.all(
          color: isDark
              ? const Color(0xFF1E293B)
              : const Color(0xFFEEF2FF),
        ),
        boxShadow: isDark
            ? null
            : [
                BoxShadow(
                  color: const Color(0xFF1D4ED8).withAlpha(10),
                  blurRadius: 12,
                  offset: const Offset(0, 3),
                ),
              ],
      ),
      child: isTyping
          ? TypingAnimation(text: content)
          : MarkdownView(data: content),
    );
  }
}

class _ActionSheet extends StatelessWidget {
  final bool isAssistant;
  final String content;
  final VoidCallback? onFavorite;
  final VoidCallback? onShare;

  const _ActionSheet({
    required this.isAssistant,
    required this.content,
    this.onFavorite,
    this.onShare,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      margin: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isDark ? AppColors.surfaceDark : Colors.white,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(height: 8),
          Container(
            width: 36,
            height: 4,
            decoration: BoxDecoration(
              color: AppColors.textMuted.withAlpha(77),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(height: 8),
          _SheetTile(
            icon: Icons.copy_rounded,
            color: AppColors.accent,
            title: '复制文本',
            onTap: () {
              Clipboard.setData(ClipboardData(text: content));
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                _buildSnackbar('已复制到剪贴板'),
              );
            },
          ),
          if (isAssistant && onFavorite != null)
            _SheetTile(
              icon: Icons.bookmark_add_rounded,
              color: AppColors.warning,
              title: '收藏此回答',
              onTap: () {
                Navigator.pop(context);
                onFavorite?.call();
              },
            ),
          if (isAssistant && onShare != null)
            _SheetTile(
              icon: Icons.share_rounded,
              color: AppColors.success,
              title: '分享为图片',
              onTap: () {
                Navigator.pop(context);
                onShare?.call();
              },
            ),
          const SizedBox(height: 12),
        ],
      ),
    );
  }

  SnackBar _buildSnackbar(String msg) {
    return SnackBar(
      content: Text(msg),
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      margin: const EdgeInsets.all(16),
    );
  }
}

class _SheetTile extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String title;
  final VoidCallback onTap;

  const _SheetTile(
      {required this.icon,
      required this.color,
      required this.title,
      required this.onTap});

  @override
  Widget build(BuildContext context) {
    return ListTile(
      onTap: onTap,
      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 2),
      leading: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: color.withAlpha(26),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(icon, color: color, size: 20),
      ),
      title: Text(title,
          style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 15)),
    );
  }
}
