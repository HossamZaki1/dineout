import 'package:dio/dio.dart';
import '../models/conversation.dart';
import '../models/chat.dart';
import 'api_client.dart';

class ConversationsApiService {
  final Dio? client;
  ConversationsApiService({this.client});
  Dio get _dio => client ?? ApiClient.instance;

  Future<ConversationPage> listPage({String? cursor, int limit = 50}) async {
    final response = await _dio.get(
      '/conversations',
      queryParameters: {'limit': limit, if (cursor != null) 'cursor': cursor},
    );
    final data = response.data as Map<String, dynamic>;
    return ConversationPage(
      (data['items'] as List)
          .map((item) => ConversationMeta.fromApi(item as Map<String, dynamic>))
          .toList(),
      data['next_cursor'] as String?,
    );
  }

  Future<ChatReply> chat(
    String sessionId,
    String text,
    List<Map<String, String>> history, {
    CancelToken? cancelToken,
  }) async {
    final response = await _dio.post(
      '/chat',
      cancelToken: cancelToken,
      data: {'session_id': sessionId, 'user_input': text, 'history': history},
    );
    return ChatReply.fromJson(response.data as Map<String, dynamic>);
  }

  Future<ConversationMeta> updateTitle(
    String conversationId,
    String title,
  ) async {
    final response = await _dio.patch(
      '/conversations/$conversationId/title',
      data: {'title': title},
    );
    return ConversationMeta.fromApi(response.data as Map<String, dynamic>);
  }

  Future<void> delete(String conversationId) async {
    await _dio.delete('/conversations/$conversationId');
  }

  Future<Map<String, dynamic>> getConversationFull(
    String conversationId, {
    CancelToken? cancelToken,
  }) async {
    final response = await _dio.get(
      '/conversations/$conversationId/full',
      cancelToken: cancelToken,
    );
    return response.data as Map<String, dynamic>;
  }
}
