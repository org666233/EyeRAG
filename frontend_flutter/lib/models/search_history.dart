class SearchHistory {
  final String id;
  final String question;
  final String answer;
  final DateTime createdAt;
  final String retrievalDecision; // proceed | retry | fallback
  final String? decisionReason;
  final int contextCount;
  final double? responseTimeMs;
  final List<dynamic> sources;
  final List<dynamic>? searchResults; // only present in detail response
  int? rating;                        // mutable: optimistic local update
  final bool isFavorited;

  SearchHistory({
    required this.id,
    required this.question,
    required this.answer,
    required this.createdAt,
    this.retrievalDecision = 'proceed',
    this.decisionReason,
    this.contextCount = 0,
    this.responseTimeMs,
    this.sources = const [],
    this.searchResults,
    this.rating,
    this.isFavorited = false,
  });

  factory SearchHistory.fromJson(Map<String, dynamic> json) => SearchHistory(
        id: json['id']?.toString() ?? '',
        question: json['question'] ?? '',
        answer: json['answer'] ?? '',
        createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
        retrievalDecision: json['retrieval_decision'] ?? 'proceed',
        decisionReason: json['decision_reason'] as String?,
        contextCount: json['context_count'] as int? ?? 0,
        responseTimeMs: (json['response_time_ms'] as num?)?.toDouble(),
        sources: json['sources'] as List<dynamic>? ?? [],
        searchResults: json['search_results'] as List<dynamic>?,
        rating: json['rating'] as int?,
        isFavorited: (json['is_favorited'] as int? ?? 0) == 1,
      );

  // 检索决策的中文标签和颜色
  String get decisionLabel {
    switch (retrievalDecision) {
      case 'proceed':
        return '正常检索';
      case 'retry':
        return '二次检索';
      case 'fallback':
        return '降级回答';
      default:
        return '未知';
    }
  }
}
