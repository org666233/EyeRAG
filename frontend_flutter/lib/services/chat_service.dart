import 'dart:convert';
import 'package:dio/dio.dart';
import '../core/network/dio_client.dart';
import '../core/constants/api_constants.dart';
import '../models/conversation.dart';

class ChatService {
  final _dio = DioClient.instance.dio;

  Future<List<Conversation>> getConversations() async {
    final resp = await _dio.get(ApiConstants.conversations);
    final list = resp.data as List<dynamic>;
    return list
        .map((e) => Conversation.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Conversation> getConversation(String id) async {
    final resp = await _dio.get(ApiConstants.conversationById(id));
    return Conversation.fromJson(resp.data as Map<String, dynamic>);
  }

  /// SSE 流式发送消息，逐个 yield 后端推送的事件对象。
  /// 事件类型：sources / content / done / related
  Stream<Map<String, dynamic>> sendMessageStream({
    required String question,
    String? conversationId,
    int topK = 10,
  }) async* {
    final body = <String, dynamic>{
      'question': question,
      'top_k': topK,
      'stream': true,
    };
    if (conversationId != null) {
      body['conversation_id'] = int.tryParse(conversationId);
    }

    final resp = await _dio.post<ResponseBody>(
      ApiConstants.chatCompletions,
      data: body,
      options: Options(
        responseType: ResponseType.stream,
        receiveTimeout: const Duration(minutes: 5),
      ),
    );

    String buffer = '';
    await for (final bytes in resp.data!.stream) {
      buffer += utf8.decode(bytes, allowMalformed: true);
      // SSE 每条消息以 \n\n 结束
      while (buffer.contains('\n\n')) {
        final idx = buffer.indexOf('\n\n');
        final message = buffer.substring(0, idx);
        buffer = buffer.substring(idx + 2);
        for (final line in message.split('\n')) {
          if (line.startsWith('data: ')) {
            final jsonStr = line.substring(6).trim();
            if (jsonStr.isNotEmpty) {
              try {
                final event = jsonDecode(jsonStr) as Map<String, dynamic>;
                yield event;
              } catch (_) {}
            }
          }
        }
      }
    }
  }

  /// 非流式（兼容旧逻辑，新页面已改用 sendMessageStream）
  Future<Map<String, dynamic>> sendMessage({
    required String question,
    String? conversationId,
    int topK = 10,
  }) async {
    final body = <String, dynamic>{
      'question': question,
      'top_k': topK,
      'stream': false,
    };
    if (conversationId != null) {
      body['conversation_id'] = int.tryParse(conversationId);
    }
    final resp = await _dio.post(ApiConstants.chatCompletions, data: body);
    return resp.data as Map<String, dynamic>;
  }

  /// 流式完成后，显式持久化消息到后端（避免流式接口内部双写）
  Future<Map<String, dynamic>> saveMessages({
    required int conversationId,
    required String question,
    required String answer,
    List<dynamic> sources = const [],
    String retrievalDecision = 'proceed',
    List<dynamic> searchResults = const [],
    int contextCount = 0,
    int responseTimeMs = 0,
  }) async {
    final resp = await _dio.post(ApiConstants.saveMessages, data: {
      'conversation_id': conversationId,
      'question': question,
      'answer': answer,
      'sources': sources,
      'retrieval_decision': retrievalDecision,
      'search_results': searchResults,
      'context_count': contextCount,
      'response_time_ms': responseTimeMs,
    });
    return resp.data as Map<String, dynamic>;
  }

  Future<void> updateTitle(String id, String title) async {
    await _dio.patch(ApiConstants.conversationTitle(id), data: {'title': title});
  }

  Future<void> deleteConversation(String id) async {
    await _dio.delete(ApiConstants.conversationById(id));
  }
}
