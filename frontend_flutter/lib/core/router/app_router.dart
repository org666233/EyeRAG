import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../pages/splash/splash_page.dart';
import '../../pages/auth/login_page.dart';
import '../../pages/auth/register_page.dart';
import '../../pages/shell/main_shell.dart';
import '../../pages/chat/chat_list_page.dart';
import '../../pages/chat/chat_detail_page.dart';
import '../../pages/history/history_page.dart';
import '../../pages/favorites/favorites_page.dart';
import '../../pages/profile/profile_page.dart';
import '../../pages/profile/about_page.dart';
import '../../pages/showcase/rag_showcase_page.dart';

final _rootNavigatorKey = GlobalKey<NavigatorState>();
final _shellNavigatorKey = GlobalKey<NavigatorState>();

final appRouterProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authStateProvider);

  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/splash',
    redirect: (context, state) {
      final isLoggedIn = authState.valueOrNull != null;
      final isSplash = state.matchedLocation == '/splash';
      final isAuth = state.matchedLocation.startsWith('/login') ||
          state.matchedLocation.startsWith('/register');

      if (isSplash) return null;
      if (!isLoggedIn && !isAuth) return '/login';
      if (isLoggedIn && isAuth) return '/chat';
      return null;
    },
    routes: [
      GoRoute(
        path: '/splash',
        builder: (_, __) => const SplashPage(),
      ),
      GoRoute(
        path: '/login',
        builder: (_, __) => const LoginPage(),
        routes: [
          GoRoute(
            path: 'register',
            builder: (_, __) => const RegisterPage(),
          ),
        ],
      ),
      ShellRoute(
        navigatorKey: _shellNavigatorKey,
        builder: (_, __, child) => MainShell(child: child),
        routes: [
          GoRoute(
            path: '/chat',
            builder: (_, __) => const ChatListPage(),
            routes: [
              GoRoute(
                path: ':id',
                builder: (_, state) =>
                    ChatDetailPage(conversationId: state.pathParameters['id']!),
              ),
            ],
          ),
          GoRoute(
            path: '/history',
            builder: (_, __) => const HistoryPage(),
          ),
          GoRoute(
            path: '/favorites',
            builder: (_, __) => const FavoritesPage(),
          ),
          GoRoute(
            path: '/profile',
            builder: (_, __) => const ProfilePage(),
            routes: [
              GoRoute(
                path: 'about',
                builder: (_, __) => const AboutPage(),
              ),
              GoRoute(
                path: 'showcase',
                builder: (_, __) => const RagShowcasePage(),
              ),
            ],
          ),
        ],
      ),
    ],
  );
});
