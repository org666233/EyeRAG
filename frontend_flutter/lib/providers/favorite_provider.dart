import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/favorite.dart';
import '../services/favorite_service.dart';

final favoriteServiceProvider = Provider((_) => FavoriteService());

final favoritesProvider =
    AsyncNotifierProvider<FavoritesNotifier, List<Favorite>>(() {
  return FavoritesNotifier();
});

class FavoritesNotifier extends AsyncNotifier<List<Favorite>> {
  @override
  Future<List<Favorite>> build() =>
      ref.read(favoriteServiceProvider).getFavorites();

  Future<void> removeFavorite(String id) async {
    await ref.read(favoriteServiceProvider).removeFavorite(id);
    state = AsyncData(
      (state.valueOrNull ?? []).where((f) => f.id != id).toList(),
    );
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(favoriteServiceProvider).getFavorites(),
    );
  }
}
