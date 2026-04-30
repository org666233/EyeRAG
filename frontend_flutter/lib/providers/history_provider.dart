import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/search_history.dart';
import '../services/history_service.dart';

final historyServiceProvider = Provider((_) => HistoryService());

// 当前过滤条件
final historyFilterProvider =
    StateProvider<({String keyword, String decision})>(
  (_) => (keyword: '', decision: ''),
);

final historyProvider =
    AsyncNotifierProvider<HistoryNotifier, List<SearchHistory>>(() {
  return HistoryNotifier();
});

class HistoryNotifier extends AsyncNotifier<List<SearchHistory>> {
  @override
  Future<List<SearchHistory>> build() {
    final filter = ref.watch(historyFilterProvider);
    return ref.read(historyServiceProvider).getHistory(
          keyword: filter.keyword,
          decision: filter.decision,
        );
  }

  Future<void> deleteRecord(String id) async {
    await ref.read(historyServiceProvider).deleteRecord(id);
    state = AsyncData(
      (state.valueOrNull ?? []).where((h) => h.id != id).toList(),
    );
  }

  Future<void> clearAll() async {
    await ref.read(historyServiceProvider).clearAll();
    state = const AsyncData([]);
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() {
      final filter = ref.read(historyFilterProvider);
      return ref.read(historyServiceProvider).getHistory(
            keyword: filter.keyword,
            decision: filter.decision,
          );
    });
  }

  /// 乐观更新评分（仅本地，后端可扩展）
  void rateRecord(String id, int rating) {
    final list = state.valueOrNull ?? [];
    state = AsyncData(
      list.map((h) {
        if (h.id == id) h.rating = (h.rating == rating) ? null : rating;
        return h;
      }).toList(),
    );
  }
}
