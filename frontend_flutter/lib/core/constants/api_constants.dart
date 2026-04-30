class ApiConstants {
  ApiConstants._();

  static const String baseUrl = 'http://localhost:8000/api';

  // Auth
  static const String login = '/auth/login';
  static const String register = '/auth/register';
  static const String me = '/auth/me';

  // Chat
  static const String conversations = '/chat/conversations';
  static String conversationById(String id) => '/chat/conversations/$id';
  static String conversationTitle(String id) => '/chat/conversations/$id/title';
  static const String chatCompletions = '/chat/completions';
  static const String saveMessages = '/chat/messages';

  // Search History
  static const String searchHistory = '/search-history';
  static String searchHistoryById(String id) => '/search-history/$id';

  // Favorites
  static const String favorites = '/favorites';
  static String favoriteById(String id) => '/favorites/$id';
  static String favoriteCheck(String messageId) => '/favorites/check/$messageId';

  // Stats (用户维度)
  static const String statsOverview = '/stats/overview';

  // Admin (管理员专用)
  static const String adminStatsOverview = '/admin/stats/overview';
  static const String adminModelConfig = '/admin/model-config';
  static const String adminUsers = '/admin/users';
  static String adminToggleUser(String id) =>
      '/admin/users/$id/toggle-active';
  static String adminDeleteUser(String id) => '/admin/users/$id';

  // Health
  static const String health = '/health';
}
