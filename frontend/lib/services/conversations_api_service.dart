import 'package:dio/dio.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import '../models/conversation.dart';

class ConversationsApiService {
  final Dio _dio = Dio();

  String get baseUrl {
    final envUrl = dotenv.env['API_URL'] ?? dotenv.env['API_BASE_URL'];
    if (envUrl != null && envUrl.isNotEmpty) return envUrl;
    return 'http://192.168.1.11:8080';
  }

  Future<List<ConversationMeta>> listConversations(String userId) async {
    final resp = await _dio.get(
      '$baseUrl/conversations',
      queryParameters: {'user_id': userId},
    );
    final List data = resp.data as List;
    return data.map((e) {
      return ConversationMeta(
        id: e['id'] as String,
        title: (e['title'] ?? '') as String,
        createdAt: DateTime.parse(e['created_at'] as String),
        updatedAt: DateTime.parse(e['updated_at'] as String),
        lastMessagePreview: (e['last_message_preview'] ?? '') as String,
      );
    }).toList();
  }

  Future<ConversationMeta> upsert(String userId, ConversationMeta meta) async {
    final resp = await _dio.post(
      '$baseUrl/conversations',
      queryParameters: {'user_id': userId},
      data: {
        'id': meta.id,
        'title': meta.title,
        'created_at': meta.createdAt.toIso8601String(),
        'updated_at': meta.updatedAt.toIso8601String(),
        'last_message_preview': meta.lastMessagePreview,
      },
    );
    final e = resp.data;
    return ConversationMeta(
      id: e['id'] as String,
      title: (e['title'] ?? '') as String,
      createdAt: DateTime.parse(e['created_at'] as String),
      updatedAt: DateTime.parse(e['updated_at'] as String),
      lastMessagePreview: (e['last_message_preview'] ?? '') as String,
    );
  }

  Future<void> delete(String userId, String conversationId) async {
    await _dio.delete(
      '$baseUrl/conversations/$conversationId',
      queryParameters: {'user_id': userId},
    );
  }
}

