import '../core/network/dio_client.dart';
import '../core/constants/api_constants.dart';

class StatsService {
  final _dio = DioClient.instance.dio;

  Future<Map<String, dynamic>> getOverview() async {
    final resp = await _dio.get(ApiConstants.statsOverview);
    return resp.data as Map<String, dynamic>;
  }
}
