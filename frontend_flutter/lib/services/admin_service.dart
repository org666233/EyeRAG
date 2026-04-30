import '../core/network/dio_client.dart';
import '../core/constants/api_constants.dart';

class AdminService {
  final _dio = DioClient.instance.dio;

  /// 全站系统总览统计
  Future<Map<String, dynamic>> getStatsOverview() async {
    final resp = await _dio.get(ApiConstants.adminStatsOverview);
    return resp.data as Map<String, dynamic>;
  }

  /// 当前模型配置（LLM + Embedding）
  Future<Map<String, dynamic>> getModelConfig() async {
    final resp = await _dio.get(ApiConstants.adminModelConfig);
    return resp.data as Map<String, dynamic>;
  }

  /// 用户列表（分页 + 关键词搜索）
  Future<Map<String, dynamic>> getUsers({
    String keyword = '',
    int page = 1,
    int pageSize = 20,
  }) async {
    final resp = await _dio.get(ApiConstants.adminUsers, queryParameters: {
      if (keyword.isNotEmpty) 'keyword': keyword,
      'page': page,
      'page_size': pageSize,
    });
    return resp.data as Map<String, dynamic>;
  }

  /// 启用 / 禁用用户
  Future<void> toggleUserActive(String userId) async {
    await _dio.patch(ApiConstants.adminToggleUser(userId));
  }

  /// 删除用户
  Future<void> deleteUser(String userId) async {
    await _dio.delete(ApiConstants.adminDeleteUser(userId));
  }
}
