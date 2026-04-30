class User {
  final String id;
  final String username;
  final String email;
  final String role;
  final bool isActive;

  const User({
    required this.id,
    required this.username,
    required this.email,
    required this.role,
    required this.isActive,
  });

  factory User.fromJson(Map<String, dynamic> json) => User(
        id: json['id']?.toString() ?? '',
        username: json['username'] ?? '',
        email: json['email'] ?? '',
        role: json['role'] ?? 'user',
        isActive: json['is_active'] ?? true,
      );

  bool get isAdmin => role == 'admin';
}
