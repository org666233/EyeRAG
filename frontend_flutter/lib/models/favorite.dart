class Favorite {
  final String id;
  final String messageId;
  final String question;
  final String answer;
  final DateTime createdAt;

  const Favorite({
    required this.id,
    required this.messageId,
    required this.question,
    required this.answer,
    required this.createdAt,
  });

  factory Favorite.fromJson(Map<String, dynamic> json) => Favorite(
        id: json['id']?.toString() ?? '',
        messageId: json['message_id']?.toString() ?? '',
        question: json['question'] ?? '',
        answer: json['answer'] ?? '',
        createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
      );

  Map<String, dynamic> toLocalDb() => {
        'id': id,
        'message_id': messageId,
        'question': question,
        'answer': answer,
        'created_at': createdAt.toIso8601String(),
      };

  factory Favorite.fromLocalDb(Map<String, dynamic> row) => Favorite(
        id: row['id'] as String,
        messageId: row['message_id'] as String,
        question: row['question'] as String,
        answer: row['answer'] as String,
        createdAt: DateTime.parse(row['created_at'] as String),
      );
}
