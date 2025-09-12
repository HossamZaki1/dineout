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
        restaurantSuggestionNames: e['restaurant_suggestion_names'] != null 
            ? List<String>.from(e['restaurant_suggestion_names'])
            : [],
        totalRestaurantSuggestions: (e['total_restaurant_suggestions'] ?? 0) as int,
        restaurantPhotoUrls: e['restaurant_photo_urls'] != null 
            ? List<String>.from(e['restaurant_photo_urls'])
            : [],
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
        'restaurant_suggestion_names': meta.restaurantSuggestionNames,
        'total_restaurant_suggestions': meta.totalRestaurantSuggestions,
        'restaurant_photo_urls': meta.restaurantPhotoUrls,
      },
    );
    final e = resp.data;
    return ConversationMeta(
      id: e['id'] as String,
      title: (e['title'] ?? '') as String,
      createdAt: DateTime.parse(e['created_at'] as String),
      updatedAt: DateTime.parse(e['updated_at'] as String),
      lastMessagePreview: (e['last_message_preview'] ?? '') as String,
      restaurantSuggestionNames: e['restaurant_suggestion_names'] != null 
          ? List<String>.from(e['restaurant_suggestion_names'])
          : [],
      totalRestaurantSuggestions: (e['total_restaurant_suggestions'] ?? 0) as int,
      restaurantPhotoUrls: e['restaurant_photo_urls'] != null 
          ? List<String>.from(e['restaurant_photo_urls'])
          : [],
    );
  }

  Future<void> delete(String userId, String conversationId) async {
    await _dio.delete(
      '$baseUrl/conversations/$conversationId',
      queryParameters: {'user_id': userId},
    );
  }

  // --- Full Conversation Methods ---

  Future<List<ConversationMessage>> getConversationMessages(String userId, String conversationId) async {
    final resp = await _dio.get(
      '$baseUrl/conversations/$conversationId/messages',
      queryParameters: {'user_id': userId},
    );
    final List data = resp.data as List;
    return data.map((e) {
      return ConversationMessage(
        role: e['role'] as String,
        content: e['content'] as String,
        timestamp: DateTime.parse(e['timestamp'] as String),
        restaurantSuggestions: e['restaurant_suggestions'] != null 
            ? List<Map<String, dynamic>>.from(e['restaurant_suggestions'])
            : null,
      );
    }).toList();
  }

  Future<ConversationMessage> addMessage(String userId, String conversationId, String role, String content, {List<Map<String, dynamic>>? restaurantSuggestions}) async {
    final resp = await _dio.post(
      '$baseUrl/conversations/$conversationId/messages',
      queryParameters: {'user_id': userId},
      data: {
        'role': role,
        'content': content,
        'timestamp': DateTime.now().toIso8601String(),
        'restaurant_suggestions': restaurantSuggestions ?? [],
      },
    );
    final e = resp.data;
    return ConversationMessage(
      role: e['role'] as String,
      content: e['content'] as String,
      timestamp: DateTime.parse(e['timestamp'] as String),
    );
  }

  Future<Map<String, dynamic>> getConversationFull(String userId, String conversationId) async {
    final resp = await _dio.get(
      '$baseUrl/conversations/$conversationId/full',
      queryParameters: {'user_id': userId},
    );
    return resp.data as Map<String, dynamic>;
  }
}

