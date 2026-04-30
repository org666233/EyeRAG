class Message {
  final String id;
  final String role; // 'user' | 'assistant'
  final String content;
  final DateTime createdAt;
  final List<dynamic> sources;

  const Message({
    required this.id,
    required this.role,
    required this.content,
    required this.createdAt,
    this.sources = const [],
  });

  factory Message.fromJson(Map<String, dynamic> json) => Message(
        id: json['id']?.toString() ?? '',
        role: json['role'] ?? 'user',
        content: json['content'] ?? '',
        createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
        sources: json['sources'] as List<dynamic>? ?? [],
      );

  bool get isUser => role == 'user';
  bool get isAssistant => role == 'assistant';
}
