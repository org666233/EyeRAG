import '../core/network/dio_client.dart';
import '../core/constants/api_constants.dart';
import '../core/storage/local_db.dart';
import '../models/favorite.dart';

class FavoriteService {
  final _dio = DioClient.instance.dio;

  Future<List<Favorite>> getFavorites() async {
    try {
      final resp = await _dio.get(ApiConstants.favorites);
      final list = resp.data as List<dynamic>;
      final favorites = list
          .map((e) => Favorite.fromJson(e as Map<String, dynamic>))
          .toList();
      // 同步到本地缓存
      await LocalDb.instance.clearFavorites();
      for (final f in favorites) {
        await LocalDb.instance.upsertFavorite(f.toLocalDb());
      }
      return favorites;
    } catch (_) {
      // 无网络时读本地缓存
      final rows = await LocalDb.instance.getFavorites();
      return rows.map(Favorite.fromLocalDb).toList();
    }
  }

  Future<void> addFavorite(String messageId) async {
    await _dio.post(ApiConstants.favorites, data: {'message_id': messageId});
  }

  Future<void> removeFavorite(String favoriteId) async {
    await _dio.delete(ApiConstants.favoriteById(favoriteId));
    await LocalDb.instance.deleteFavorite(favoriteId);
  }

  Future<bool> checkFavorite(String messageId) async {
    final resp = await _dio.get(ApiConstants.favoriteCheck(messageId));
    return (resp.data as Map<String, dynamic>)['is_favorite'] as bool? ?? false;
  }
}
