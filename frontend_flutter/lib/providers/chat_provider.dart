import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/conversation.dart';
import '../services/chat_service.dart';

final chatServiceProvider = Provider((_) => ChatService());

final conversationsProvider =
    AsyncNotifierProvider<ConversationsNotifier, List<Conversation>>(() {
  return ConversationsNotifier();
});

class ConversationsNotifier extends AsyncNotifier<List<Conversation>> {
  @override
  Future<List<Conversation>> build() =>
      ref.read(chatServiceProvider).getConversations();

  Future<void> deleteConversation(String id) async {
    await ref.read(chatServiceProvider).deleteConversation(id);
    state = AsyncData(
      (state.valueOrNull ?? []).where((c) => c.id != id).toList(),
    );
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(chatServiceProvider).getConversations(),
    );
  }
}
