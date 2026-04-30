import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

class MarkdownView extends StatelessWidget {
  final String data;
  final bool shrinkWrap;

  const MarkdownView({super.key, required this.data, this.shrinkWrap = true});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return MarkdownBody(
      data: data,
      shrinkWrap: shrinkWrap,
      styleSheet: MarkdownStyleSheet(
        p: theme.textTheme.bodyMedium,
        h1: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
        h2: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
        h3: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
        code: theme.textTheme.bodySmall?.copyWith(
          fontFamily: 'monospace',
          backgroundColor: theme.colorScheme.surfaceContainerHighest,
        ),
        codeblockDecoration: BoxDecoration(
          color: theme.colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(8),
        ),
        blockquoteDecoration: BoxDecoration(
          border: Border(
            left: BorderSide(color: theme.colorScheme.primary, width: 3),
          ),
        ),
        listBullet: theme.textTheme.bodyMedium,
        strong: theme.textTheme.bodyMedium?.copyWith(
          fontWeight: FontWeight.bold,
        ),
        em: theme.textTheme.bodyMedium?.copyWith(
          fontStyle: FontStyle.italic,
        ),
      ),
    );
  }
}
