import 'message.dart';

class Conversation {
  final String id;
  final String title;
  final DateTime updatedAt;
  final List<Message> messages;

  const Conversation({
    required this.id,
    required this.title,
    required this.updatedAt,
    this.messages = const [],
  });

  factory Conversation.fromJson(Map<String, dynamic> json) => Conversation(
        id: json['id']?.toString() ?? '',
        title: json['title'] ?? '新对话',
        updatedAt: DateTime.tryParse(json['updated_at'] ?? '') ?? DateTime.now(),
        messages: (json['messages'] as List<dynamic>?)
                ?.map((m) => Message.fromJson(m as Map<String, dynamic>))
                .toList() ??
            [],
      );
}
