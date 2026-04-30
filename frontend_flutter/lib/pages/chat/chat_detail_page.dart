import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:screenshot/screenshot.dart';
import 'package:share_plus/share_plus.dart';
import 'package:path_provider/path_provider.dart';
import '../../models/message.dart';
import '../../providers/chat_provider.dart';
import '../../providers/favorite_provider.dart';
import '../../services/chat_service.dart';
import '../../services/favorite_service.dart';
import '../../widgets/common/app_loading.dart';
import '../../widgets/common/app_error.dart';
import '../../widgets/chat/message_bubble.dart';
import '../../widgets/chat/voice_input_btn.dart';
import '../../core/theme/app_theme.dart';

// ── 流式阶段枚举 ────────────────────────────────────────────────
enum _Stage { idle, retrieving, evaluating, generating, done }

class ChatDetailPage extends ConsumerStatefulWidget {
  final String conversationId;
  const ChatDetailPage({super.key, required this.conversationId});

  @override
  ConsumerState<ChatDetailPage> createState() => _ChatDetailPageState();
}

class _ChatDetailPageState extends ConsumerState<ChatDetailPage> {
  final _inputCtrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  final _screenshotCtrl = ScreenshotController();

  bool _loading = false;
  String? _loadError;

  List<Message> _messages = [];
  String? _currentConvId;
  String _title = '新对话';

  // ── 流式状态 ────────────────────────────────────────────────
  _Stage _stage = _Stage.idle;
  String _streamingAnswer = '';
  List<Map<String, dynamic>> _sources = [];
  List<Map<String, dynamic>> _searchResults = [];
  String _retrievalDecision = '';
  int? _pendingConvId;
  List<String> _relatedQuestions = [];
  bool _sourcesExpanded = false;
  final _streamStart = ValueNotifier<int>(0); // 毫秒，用于计时
  int _responseMs = 0;

  bool get _isNew => widget.conversationId == 'new';
  bool get _sending => _stage != _Stage.idle && _stage != _Stage.done;

  @override
  void initState() {
    super.initState();
    if (!_isNew) {
      _currentConvId = widget.conversationId;
      _loadConversation();
    }
  }

  @override
  void dispose() {
    _inputCtrl.dispose();
    _scrollCtrl.dispose();
    _streamStart.dispose();
    super.dispose();
  }

  Future<void> _loadConversation() async {
    setState(() {
      _loading = true;
      _loadError = null;
    });
    try {
      final conv = await ref
          .read(chatServiceProvider)
          .getConversation(_currentConvId!);
      setState(() {
        _title = conv.title;
        _messages = conv.messages;
      });
      _scrollToBottom();
    } catch (e) {
      setState(() => _loadError = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _scrollToBottom({bool animate = true}) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        if (animate) {
          _scrollCtrl.animateTo(
            _scrollCtrl.position.maxScrollExtent,
            duration: const Duration(milliseconds: 250),
            curve: Curves.easeOut,
          );
        } else {
          _scrollCtrl.jumpTo(_scrollCtrl.position.maxScrollExtent);
        }
      }
    });
  }

  Future<void> _send() async {
    final text = _inputCtrl.text.trim();
    if (text.isEmpty || _sending) return;
    _inputCtrl.clear();

    final tempUserMsg = Message(
      id: 'tmp_${DateTime.now().millisecondsSinceEpoch}',
      role: 'user',
      content: text,
      createdAt: DateTime.now(),
    );

    setState(() {
      _messages = [..._messages, tempUserMsg];
      _stage = _Stage.retrieving;
      _streamingAnswer = '';
      _sources = [];
      _searchResults = [];
      _retrievalDecision = '';
      _relatedQuestions = [];
      _sourcesExpanded = false;
      _responseMs = 0;
    });
    _streamStart.value = DateTime.now().millisecondsSinceEpoch;
    _scrollToBottom();

    try {
      final svc = ChatService();
      await for (final event in svc.sendMessageStream(
        question: text,
        conversationId: _currentConvId,
      )) {
        if (!mounted) break;
        final type = event['type'] as String? ?? '';

        switch (type) {
          case 'sources':
            setState(() {
              _sources = List<Map<String, dynamic>>.from(
                  (event['sources'] as List? ?? [])
                      .map((e) => Map<String, dynamic>.from(e as Map)));
              _searchResults = List<Map<String, dynamic>>.from(
                  (event['search_results'] as List? ?? [])
                      .map((e) => Map<String, dynamic>.from(e as Map)));
              _retrievalDecision =
                  event['retrieval_decision']?.toString() ?? '';
              _pendingConvId = event['conversation_id'] as int?;
              _stage = _Stage.evaluating;
            });
            _scrollToBottom();

          case 'content':
            setState(() {
              _streamingAnswer += (event['content'] as String? ?? '');
              _stage = _Stage.generating;
            });
            _scrollToBottom(animate: false);

          case 'done':
            final ms = DateTime.now().millisecondsSinceEpoch -
                _streamStart.value;
            setState(() => _responseMs = ms);

            // 持久化消息
            final convId = _pendingConvId ??
                ((_currentConvId != null)
                    ? int.tryParse(_currentConvId!)
                    : null);
            if (convId != null) {
              try {
                await svc.saveMessages(
                  conversationId: convId,
                  question: text,
                  answer: _streamingAnswer,
                  sources: _sources,
                  retrievalDecision: _retrievalDecision,
                  searchResults: _searchResults,
                  contextCount: _sources.length,
                  responseTimeMs: _responseMs,
                );
              } catch (_) {}
              _currentConvId = convId.toString();
            }

            // 拉取完整对话（获取正式消息 ID）
            if (_currentConvId != null) {
              try {
                final conv = await svc.getConversation(_currentConvId!);
                setState(() {
                  _title = conv.title;
                  _messages = conv.messages;
                  _streamingAnswer = '';
                  _stage = _Stage.done;
                });
              } catch (_) {
                setState(() => _stage = _Stage.done);
              }
            } else {
              setState(() => _stage = _Stage.done);
            }
            ref.invalidate(conversationsProvider);
            _scrollToBottom();

          case 'related':
            setState(() {
              _relatedQuestions = List<String>.from(
                  (event['questions'] as List? ?? []).map((e) => e.toString()));
            });
        }
      }
    } catch (e) {
      // 回滚乐观消息
      setState(() {
        _messages =
            _messages.where((m) => m.id != tempUserMsg.id).toList();
        _stage = _Stage.idle;
        _streamingAnswer = '';
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('发送失败: $e'),
            backgroundColor: AppColors.error,
            behavior: SnackBarBehavior.floating,
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            margin: const EdgeInsets.all(16),
          ),
        );
      }
    }
  }

  Future<void> _favoriteMessage(Message msg) async {
    try {
      await FavoriteService().addFavorite(msg.id);
      ref.invalidate(favoritesProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Row(children: [
              Icon(Icons.bookmark_added_rounded, color: Colors.white, size: 18),
              SizedBox(width: 8),
              Text('已加入收藏'),
            ]),
            behavior: SnackBarBehavior.floating,
            backgroundColor: AppColors.success,
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12)),
            margin: const EdgeInsets.all(16),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('收藏失败: $e')));
      }
    }
  }

  Future<void> _shareMessage(Message msg) async {
    if (kIsWeb) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Web 端暂不支持分享图片')),
      );
      return;
    }
    final image = await _screenshotCtrl.captureFromWidget(
      Material(
        child: Container(
          padding: const EdgeInsets.all(20),
          color: Colors.white,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [AppColors.primary, AppColors.secondary],
                    ),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(Icons.visibility_rounded,
                      color: Colors.white, size: 16),
                ),
                const SizedBox(width: 8),
                const Text('眼科智能问答',
                    style: TextStyle(
                        fontWeight: FontWeight.w700,
                        color: AppColors.primary)),
              ]),
              const SizedBox(height: 12),
              Text(msg.content),
            ],
          ),
        ),
      ),
    );
    final dir = await getTemporaryDirectory();
    final file = File('${dir.path}/share_${msg.id}.png');
    await file.writeAsBytes(image);
    await Share.shareXFiles([XFile(file.path)], text: '来自眼科智能问答的回答');
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    Widget body;
    if (_loading) {
      body = const AppLoading(message: '加载中…');
    } else if (_loadError != null) {
      body = AppError(message: _loadError!, onRetry: _loadConversation);
    } else {
      body = Column(
        children: [
          Expanded(
            child: Screenshot(
              controller: _screenshotCtrl,
              child: _messages.isEmpty &&
                      _stage == _Stage.idle &&
                      _streamingAnswer.isEmpty
                  ? _EmptyChat(
                      onSuggest: (q) {
                        _inputCtrl.text = q;
                        _send();
                      },
                    )
                  : _buildMessageList(isDark),
            ),
          ),
          // 相关问题推荐
          if (_relatedQuestions.isNotEmpty && _stage == _Stage.done)
            _RelatedQuestions(
              questions: _relatedQuestions,
              onTap: (q) {
                setState(() {
                  _relatedQuestions = [];
                  _stage = _Stage.idle;
                });
                _inputCtrl.text = q;
                _send();
              },
            ),
          _InputBar(
            controller: _inputCtrl,
            sending: _sending,
            isDark: isDark,
            onSend: _send,
            onVoiceResult: (text) {
              _inputCtrl.text = text;
              _inputCtrl.selection = TextSelection.fromPosition(
                TextPosition(offset: text.length),
              );
            },
          ),
        ],
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(_title),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          if (_responseMs > 0)
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: Center(
                child: Text(
                  '${(_responseMs / 1000).toStringAsFixed(1)}s',
                  style: const TextStyle(
                      fontSize: 11,
                      color: AppColors.textMuted,
                      fontWeight: FontWeight.w500),
                ),
              ),
            ),
        ],
      ),
      body: body,
    );
  }

  Widget _buildMessageList(bool isDark) {
    // 计算 item 数量
    // 历史消息 + (状态条?) + (检索卡?) + (流式气泡?) 
    final showStatusBar = _stage == _Stage.retrieving ||
        _stage == _Stage.evaluating ||
        _stage == _Stage.generating;
    final showSources = _sources.isNotEmpty;
    final showStreaming = _streamingAnswer.isNotEmpty;

    return ListView.builder(
      controller: _scrollCtrl,
      padding: const EdgeInsets.only(top: 12, bottom: 12),
      itemCount: _messages.length +
          (showStatusBar ? 1 : 0) +
          (showSources ? 1 : 0) +
          (showStreaming ? 1 : 0),
      itemBuilder: (_, i) {
        int idx = i;

        // 历史消息
        if (idx < _messages.length) {
          final msg = _messages[idx];
          final isTemp = msg.id.startsWith('tmp_');
          return MessageBubble(
            message: msg,
            isTyping: false,
            onFavorite: msg.isAssistant && !isTemp
                ? () => _favoriteMessage(msg)
                : null,
            onShare: msg.isAssistant && !isTemp
                ? () => _shareMessage(msg)
                : null,
          );
        }
        idx -= _messages.length;

        // 检索结果卡（在状态条之前出现）
        if (showSources && idx == 0) {
          return _SourcesPanel(
            sources: _sources,
            searchResults: _searchResults,
            decision: _retrievalDecision,
            expanded: _sourcesExpanded,
            onToggle: () =>
                setState(() => _sourcesExpanded = !_sourcesExpanded),
            isDark: isDark,
          );
        }
        if (showSources) idx--;

        // 状态条（retrieving / evaluating / generating）
        if (showStatusBar && idx == 0) {
          return _StatusBar(stage: _stage, isDark: isDark);
        }
        if (showStatusBar) idx--;

        // 流式回答气泡
        if (showStreaming && idx == 0) {
          return _StreamingBubble(text: _streamingAnswer, isDark: isDark);
        }

        return const SizedBox.shrink();
      },
    );
  }
}

// ── 状态横幅 ────────────────────────────────────────────────────────────────

class _StatusBar extends StatefulWidget {
  final _Stage stage;
  final bool isDark;
  const _StatusBar({required this.stage, required this.isDark});

  @override
  State<_StatusBar> createState() => _StatusBarState();
}

class _StatusBarState extends State<_StatusBar>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _pulse;
  Timer? _dotTimer;
  int _dots = 1;

  static const _stageInfo = {
    _Stage.retrieving: (
      icon: Icons.manage_search_rounded,
      label: '正在检索知识库',
      color: Color(0xFF0891B2),
    ),
    _Stage.evaluating: (
      icon: Icons.analytics_outlined,
      label: '正在评估文档相关性',
      color: Color(0xFF7C3AED),
    ),
    _Stage.generating: (
      icon: Icons.auto_awesome_rounded,
      label: '生成回答中',
      color: Color(0xFF059669),
    ),
  };

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
    _pulse = Tween(begin: 0.6, end: 1.0).animate(
        CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut));
    _dotTimer = Timer.periodic(const Duration(milliseconds: 500),
        (_) => mounted ? setState(() => _dots = (_dots % 3) + 1) : null);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    _dotTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final info = _stageInfo[widget.stage];
    if (info == null) return const SizedBox.shrink();

    final dots = '.' * _dots;
    return Padding(
      padding: const EdgeInsets.only(left: 16, right: 64, bottom: 8, top: 4),
      child: Row(
        children: [
          // AI 头像
          Container(
            width: 32,
            height: 32,
            margin: const EdgeInsets.only(right: 8),
            decoration: const BoxDecoration(
                gradient: AppGradients.hero, shape: BoxShape.circle),
            child: const Icon(Icons.visibility_rounded,
                color: Colors.white, size: 16),
          ),
          FadeTransition(
            opacity: _pulse,
            child: Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: info.color.withAlpha(15),
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(16),
                  topRight: Radius.circular(16),
                  bottomRight: Radius.circular(16),
                  bottomLeft: Radius.circular(4),
                ),
                border: Border.all(color: info.color.withAlpha(50)),
              ),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(info.icon, size: 14, color: info.color),
                const SizedBox(width: 6),
                Text(
                  '${info.label}$dots',
                  style: TextStyle(
                    fontSize: 13,
                    color: info.color,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}

// ── 检索结果面板 ─────────────────────────────────────────────────────────────

class _SourcesPanel extends StatelessWidget {
  final List<Map<String, dynamic>> sources;
  final List<Map<String, dynamic>> searchResults;
  final String decision;
  final bool expanded;
  final VoidCallback onToggle;
  final bool isDark;

  const _SourcesPanel({
    required this.sources,
    required this.searchResults,
    required this.decision,
    required this.expanded,
    required this.onToggle,
    required this.isDark,
  });

  Color get _decisionColor {
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

  String get _decisionLabel {
    switch (decision) {
      case 'proceed':
        return '✓ 直接生成';
      case 'retry':
        return '↻ 二次检索';
      case 'fallback':
        return '⚠ 降级回答';
      default:
        return decision;
    }
  }

  @override
  Widget build(BuildContext context) {
    final bgColor = isDark ? const Color(0xFF1E293B) : const Color(0xFFF0F9FF);
    final borderColor = isDark
        ? const Color(0xFF0891B2).withAlpha(60)
        : const Color(0xFF0891B2).withAlpha(40);

    return Padding(
      padding: const EdgeInsets.only(left: 16, right: 16, bottom: 8),
      child: Container(
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: borderColor),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 折叠头
            InkWell(
              onTap: onToggle,
              borderRadius: BorderRadius.circular(14),
              child: Padding(
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                child: Row(
                  children: [
                    const Icon(Icons.library_books_rounded,
                        size: 15, color: Color(0xFF0891B2)),
                    const SizedBox(width: 7),
                    Text(
                      '检索到 ${sources.length} 个相关文档块',
                      style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF0891B2)),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 7, vertical: 2),
                      decoration: BoxDecoration(
                        color: _decisionColor.withAlpha(25),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(
                            color: _decisionColor.withAlpha(70)),
                      ),
                      child: Text(
                        _decisionLabel,
                        style: TextStyle(
                            fontSize: 10,
                            color: _decisionColor,
                            fontWeight: FontWeight.w700),
                      ),
                    ),
                    const Spacer(),
                    Icon(
                      expanded
                          ? Icons.keyboard_arrow_up_rounded
                          : Icons.keyboard_arrow_down_rounded,
                      size: 18,
                      color: const Color(0xFF0891B2),
                    ),
                  ],
                ),
              ),
            ),
            // 展开内容
            if (expanded)
              Padding(
                padding: const EdgeInsets.fromLTRB(14, 0, 14, 12),
                child: Column(
                  children: searchResults.take(5).map((sr) {
                    final content = sr['content']?.toString() ?? '';
                    final meta =
                        sr['metadata'] as Map? ?? {};
                    final title =
                        meta['source']?.toString().split('/').last ??
                            meta['title']?.toString() ??
                            '未知来源';
                    final score = (sr['rrf_score'] as num?)?.toDouble() ?? 0.0;
                    final type = sr['retrieval_type']?.toString() ?? '';

                    return _DocChunk(
                      title: title,
                      content: content,
                      score: score,
                      retrievalType: type,
                      isDark: isDark,
                    );
                  }).toList(),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _DocChunk extends StatefulWidget {
  final String title;
  final String content;
  final double score;
  final String retrievalType;
  final bool isDark;

  const _DocChunk({
    required this.title,
    required this.content,
    required this.score,
    required this.retrievalType,
    required this.isDark,
  });

  @override
  State<_DocChunk> createState() => _DocChunkState();
}

class _DocChunkState extends State<_DocChunk> {
  bool _expanded = false;

  Color get _typeColor {
    switch (widget.retrievalType) {
      case 'vector':
        return AppColors.primary;
      case 'bm25':
        return const Color(0xFF059669);
      case 'hybrid':
        return const Color(0xFF7C3AED);
      default:
        return AppColors.textMuted;
    }
  }

  @override
  Widget build(BuildContext context) {
    final maxScore = 0.05; // RRF 分数通常较小
    final progress = (widget.score / maxScore).clamp(0.0, 1.0);

    return GestureDetector(
      onTap: () => setState(() => _expanded = !_expanded),
      child: Container(
        margin: const EdgeInsets.only(top: 8),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: widget.isDark
              ? Colors.white.withAlpha(8)
              : Colors.white.withAlpha(200),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
              color: widget.isDark
                  ? Colors.white12
                  : const Color(0xFFE2E8F0)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Expanded(
                child: Text(
                  widget.title,
                  style: const TextStyle(
                      fontSize: 12, fontWeight: FontWeight.w600),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 6),
              if (widget.retrievalType.isNotEmpty)
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 5, vertical: 1),
                  decoration: BoxDecoration(
                    color: _typeColor.withAlpha(20),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    widget.retrievalType,
                    style: TextStyle(
                        fontSize: 9,
                        color: _typeColor,
                        fontWeight: FontWeight.w600),
                  ),
                ),
              const SizedBox(width: 4),
              Text(
                widget.score.toStringAsFixed(4),
                style: const TextStyle(
                    fontSize: 10, color: AppColors.textMuted),
              ),
            ]),
            const SizedBox(height: 5),
            ClipRRect(
              borderRadius: BorderRadius.circular(2),
              child: LinearProgressIndicator(
                value: progress,
                minHeight: 3,
                backgroundColor: AppColors.primary.withAlpha(20),
                valueColor:
                    const AlwaysStoppedAnimation(AppColors.primary),
              ),
            ),
            if (_expanded) ...[
              const SizedBox(height: 6),
              Text(
                widget.content,
                style: const TextStyle(
                    fontSize: 11,
                    color: AppColors.textSecondary,
                    height: 1.5),
                maxLines: 6,
                overflow: TextOverflow.ellipsis,
              ),
            ] else ...[
              const SizedBox(height: 4),
              Text(
                widget.content,
                style: const TextStyle(
                    fontSize: 11,
                    color: AppColors.textMuted,
                    height: 1.4),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// ── 流式回答气泡 ─────────────────────────────────────────────────────────────

class _StreamingBubble extends StatelessWidget {
  final String text;
  final bool isDark;
  const _StreamingBubble({required this.text, required this.isDark});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 16, right: 64, bottom: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 32,
            height: 32,
            margin: const EdgeInsets.only(right: 8, top: 2),
            decoration: const BoxDecoration(
                gradient: AppGradients.hero, shape: BoxShape.circle),
            child: const Icon(Icons.visibility_rounded,
                color: Colors.white, size: 16),
          ),
          Expanded(
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF1E293B) : Colors.white,
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(18),
                  topRight: Radius.circular(18),
                  bottomRight: Radius.circular(18),
                  bottomLeft: Radius.circular(4),
                ),
                boxShadow: [
                  BoxShadow(
                    color: AppColors.primary.withAlpha(15),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  MarkdownBody(
                    data: text,
                    styleSheet: MarkdownStyleSheet(
                      p: TextStyle(
                        fontSize: 14,
                        height: 1.7,
                        color: isDark
                            ? const Color(0xFFE2E8F0)
                            : AppColors.textPrimary,
                      ),
                      code: TextStyle(
                        fontSize: 12,
                        backgroundColor: isDark
                            ? Colors.white12
                            : const Color(0xFFF1F5F9),
                      ),
                    ),
                  ),
                  const SizedBox(height: 6),
                  // 光标闪烁
                  _BlinkingCursor(),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _BlinkingCursor extends StatefulWidget {
  @override
  State<_BlinkingCursor> createState() => _BlinkingCursorState();
}

class _BlinkingCursorState extends State<_BlinkingCursor>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl =
        AnimationController(vsync: this, duration: const Duration(milliseconds: 600))
          ..repeat(reverse: true);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _ctrl,
      child: Container(
        width: 2,
        height: 14,
        decoration: BoxDecoration(
          color: AppColors.primary,
          borderRadius: BorderRadius.circular(1),
        ),
      ),
    );
  }
}

// ── 相关问题推荐 ─────────────────────────────────────────────────────────────

class _RelatedQuestions extends StatelessWidget {
  final List<String> questions;
  final ValueChanged<String> onTap;
  const _RelatedQuestions({required this.questions, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(left: 4, bottom: 6),
            child: Row(children: [
              Icon(Icons.lightbulb_outline_rounded,
                  size: 13, color: AppColors.textMuted),
              SizedBox(width: 5),
              Text('您可能还想问',
                  style: TextStyle(
                      fontSize: 11,
                      color: AppColors.textMuted,
                      fontWeight: FontWeight.w600)),
            ]),
          ),
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: questions
                .map((q) => GestureDetector(
                      onTap: () => onTap(q),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: const Color(0xFFEEF2FF),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                              color: const Color(0xFFDBEAFE)),
                        ),
                        child: Text(q,
                            style: const TextStyle(
                                fontSize: 12,
                                color: AppColors.primary,
                                fontWeight: FontWeight.w500)),
                      ),
                    ))
                .toList(),
          ),
          const SizedBox(height: 6),
        ],
      ),
    );
  }
}

// ── 空状态 ──────────────────────────────────────────────────────────────────

class _EmptyChat extends StatelessWidget {
  final ValueChanged<String> onSuggest;
  const _EmptyChat({required this.onSuggest});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                    colors: [Color(0xFFEEF2FF), Color(0xFFDBEAFE)]),
                borderRadius: BorderRadius.circular(24),
              ),
              child: const Icon(Icons.visibility_rounded,
                  size: 40, color: AppColors.primary),
            ),
            const SizedBox(height: 16),
            const Text('眼科智能助手',
                style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary)),
            const SizedBox(height: 8),
            const Text('请输入您的眼科相关问题\n我将为您提供专业解答',
                textAlign: TextAlign.center,
                style: TextStyle(
                    fontSize: 14,
                    color: AppColors.textMuted,
                    height: 1.6)),
            const SizedBox(height: 20),
            // Self-RAG 特性标签
            Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment: WrapAlignment.center,
              children: [
                _FeatureTag(
                    icon: Icons.psychology_alt_rounded,
                    label: 'Self-RAG 自适应检索',
                    color: AppColors.primary),
                _FeatureTag(
                    icon: Icons.stream_rounded,
                    label: '流式渐进回答',
                    color: const Color(0xFF059669)),
                _FeatureTag(
                    icon: Icons.library_books_rounded,
                    label: '眼科知识库',
                    color: const Color(0xFF0891B2)),
              ],
            ),
            const SizedBox(height: 20),
            ...[
              '散瞳检查有什么作用？',
              '近视手术后有哪些注意事项？',
              '眼压高有什么症状？',
            ].map(
              (q) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: _SuggestChip(text: q, onTap: () => onSuggest(q)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FeatureTag extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  const _FeatureTag(
      {required this.icon, required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withAlpha(18),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withAlpha(50)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 12, color: color),
        const SizedBox(width: 5),
        Text(label,
            style: TextStyle(
                fontSize: 11, color: color, fontWeight: FontWeight.w600)),
      ]),
    );
  }
}

class _SuggestChip extends StatelessWidget {
  final String text;
  final VoidCallback onTap;
  const _SuggestChip({required this.text, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
        decoration: BoxDecoration(
          color: const Color(0xFFEEF2FF),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: const Color(0xFFDBEAFE)),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.arrow_forward_ios_rounded,
              size: 11, color: AppColors.primary),
          const SizedBox(width: 6),
          Text(text,
              style: const TextStyle(
                  fontSize: 13,
                  color: AppColors.primary,
                  fontWeight: FontWeight.w500)),
        ]),
      ),
    );
  }
}

// ── 输入栏 ──────────────────────────────────────────────────────────────────

class _InputBar extends StatelessWidget {
  final TextEditingController controller;
  final bool sending;
  final bool isDark;
  final VoidCallback onSend;
  final ValueChanged<String> onVoiceResult;

  const _InputBar({
    required this.controller,
    required this.sending,
    required this.isDark,
    required this.onSend,
    required this.onVoiceResult,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
      decoration: BoxDecoration(
        color: isDark ? AppColors.surfaceDark : Colors.white,
        border: Border(
          top: BorderSide(
            color: isDark
                ? const Color(0xFF1E293B)
                : const Color(0xFFEEF2FF),
          ),
        ),
        boxShadow: isDark
            ? null
            : [
                BoxShadow(
                  color: const Color(0xFF1D4ED8).withAlpha(10),
                  blurRadius: 20,
                  offset: const Offset(0, -4),
                ),
              ],
      ),
      child: SafeArea(
        top: false,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            VoiceInputButton(onResult: onVoiceResult),
            const SizedBox(width: 8),
            Expanded(
              child: Container(
                decoration: BoxDecoration(
                  color: isDark
                      ? AppColors.surfaceVariantDark
                      : const Color(0xFFF5F8FF),
                  borderRadius: BorderRadius.circular(22),
                  border: Border.all(
                    color: isDark
                        ? const Color(0xFF334155)
                        : const Color(0xFFE0E7FF),
                  ),
                ),
                child: TextField(
                  controller: controller,
                  maxLines: 5,
                  minLines: 1,
                  textInputAction: TextInputAction.newline,
                  style: TextStyle(
                      fontSize: 15,
                      color: isDark
                          ? const Color(0xFFF1F5F9)
                          : AppColors.textPrimary),
                  decoration: const InputDecoration(
                    hintText: '请输入眼科相关问题…',
                    border: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    contentPadding:
                        EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    hintStyle:
                        TextStyle(color: AppColors.textMuted, fontSize: 15),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            GestureDetector(
              onTap: sending ? null : onSend,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  gradient: sending
                      ? const LinearGradient(
                          colors: [Color(0xFF93C5FD), Color(0xFF67E8F9)])
                      : const LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [AppColors.primary, AppColors.secondary]),
                  shape: BoxShape.circle,
                  boxShadow: sending
                      ? []
                      : [
                          BoxShadow(
                            color: AppColors.primary.withAlpha(77),
                            blurRadius: 10,
                            offset: const Offset(0, 4),
                          ),
                        ],
                ),
                child: Center(
                  child: sending
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.send_rounded,
                          color: Colors.white, size: 18),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
