import '../core/network/dio_client.dart';
import '../core/constants/api_constants.dart';
import '../models/search_history.dart';

class HistoryService {
  final _dio = DioClient.instance.dio;

  Future<List<SearchHistory>> getHistory({
    String keyword = '',
    String decision = '',
    int pageSize = 100,
  }) async {
    final resp = await _dio.get(
      ApiConstants.searchHistory,
      queryParameters: {
        if (keyword.isNotEmpty) 'keyword': keyword,
        if (decision.isNotEmpty) 'decision': decision,
        'page_size': pageSize,
      },
    );
    final data = resp.data as Map<String, dynamic>;
    final list = data['items'] as List<dynamic>? ?? [];
    return list
        .map((e) => SearchHistory.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<SearchHistory> getDetail(String id) async {
    final resp = await _dio.get(ApiConstants.searchHistoryById(id));
    return SearchHistory.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<void> deleteRecord(String id) async {
    await _dio.delete(ApiConstants.searchHistoryById(id));
  }

  Future<void> clearAll() async {
    await _dio.delete(ApiConstants.searchHistory);
  }
}
