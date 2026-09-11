import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import '../models/chat.dart';
import '../models/conversation.dart';
import 'conversation_service.dart';
import 'conversations_api_service.dart';

abstract interface class ChatRepository {
  Future<LoadedConversation> load(String sessionId, {CancelToken? cancelToken});
  Future<ChatReply> send(
    String sessionId,
    String text,
    List<Map<String, String>> history, {
    CancelToken? cancelToken,
  });
}

/// The API is authoritative. Local data is a cache of successful operations.
class ConversationRepository implements ChatRepository {
  final String userId;
  final String? Function() currentUserId;
  final ConversationsApiService api;
  final ConversationService local;

  ConversationRepository({
    required this.userId,
    required this.currentUserId,
    ConversationsApiService? api,
    ConversationService? local,
  }) : api = api ?? ConversationsApiService(),
       local = local ?? ConversationService();

  void _checkIdentity() {
    if (userId.isEmpty || currentUserId() != userId) {
      throw StateError('Please sign in again to continue.');
    }
  }

  Future<void> _cache(Future<void> Function() action) async {
    try {
      await action();
    } catch (error) {
      if (kDebugMode) {
        debugPrint('Conversation cache could not be updated: $error');
      }
    }
  }

  @override
  Future<LoadedConversation> load(
    String sessionId, {
    CancelToken? cancelToken,
  }) async {
    _checkIdentity();
    try {
      final data = await api.getConversationFull(
        sessionId,
        cancelToken: cancelToken,
      );
      _checkIdentity();
      final messages = (data['messages'] as List)
          .map((m) => ConversationMessage.fromMap(m as Map<String, dynamic>))
          .toList();
      await _cache(() async {
        await local.saveConversationHistory(
          sessionId,
          messages,
          userId: userId,
        );
        await local.upsertConversation(
          ConversationMeta.fromApi(data),
          userId: userId,
        );
      });
      _checkIdentity();
      return LoadedConversation(messages);
    } on DioException catch (error) {
      _checkIdentity();
      final status = error.response?.statusCode;
      if (status == 404) {
        await local.deleteConversation(sessionId, userId: userId);
        rethrow;
      }
      // Authentication failures and cancellations must not reveal cached data.
      if (!canUseConversationCache(error)) rethrow;
      final history = await local.getConversationHistory(
        sessionId,
        userId: userId,
      );
      _checkIdentity();
      if (history == null) rethrow;
      return LoadedConversation(history, fromCache: true);
    }
  }

  @override
  Future<ChatReply> send(
    String sessionId,
    String text,
    List<Map<String, String>> history, {
    CancelToken? cancelToken,
  }) async {
    _checkIdentity();
    final reply = await api.chat(
      sessionId,
      text,
      history,
      cancelToken: cancelToken,
    );
    _checkIdentity();
    await _cache(() async {
      final now = DateTime.now().toUtc();
      final messages =
          await local.getConversationHistory(sessionId, userId: userId) ?? [];
      messages.addAll([
        ConversationMessage(role: 'user', content: text, timestamp: now),
        ConversationMessage(
          role: 'assistant',
          content: reply.text,
          timestamp: now.add(const Duration(microseconds: 1)),
          restaurantSuggestions: reply.suggestions,
        ),
      ]);
      await local.saveConversationHistory(sessionId, messages, userId: userId);
      final existing = await local.getConversationMeta(
        sessionId,
        userId: userId,
      );
      final suggestions = messages.expand(
        (m) => m.restaurantSuggestions ?? <Map<String, dynamic>>[],
      );
      final names = suggestions
          .map((s) => s['name'])
          .whereType<String>()
          .toSet()
          .take(20)
          .toList();
      final photos = suggestions
          .map((s) => s['photo_url'])
          .whereType<String>()
          .toSet()
          .take(12)
          .toList();
      await local.upsertConversation(
        ConversationMeta(
          id: sessionId,
          title:
              existing?.title ??
              (text.length <= 50 ? text : text.substring(0, 50)),
          createdAt: existing?.createdAt ?? now,
          updatedAt: now,
          lastMessagePreview: reply.text.length <= 100
              ? reply.text
              : reply.text.substring(0, 100),
          restaurantSuggestionNames: names,
          restaurantPhotoUrls: photos,
          totalRestaurantSuggestions: suggestions.length,
        ),
        userId: userId,
      );
    });
    _checkIdentity();
    return reply;
  }
}

bool canUseConversationCache(Object error) =>
    error is DioException &&
    !CancelToken.isCancel(error) &&
    (error.response?.statusCode == null || error.response!.statusCode! >= 500);

String conversationError(Object error) {
  if (error is DioException) {
    if (error.response?.statusCode == 404) {
      return 'This conversation is no longer available.';
    }
    if (error.response?.statusCode == 401) {
      return 'Please sign in again to continue.';
    }
    final data = error.response?.data;
    if (data is Map && data['detail'] is String) {
      return data['detail'] as String;
    }
    return 'Could not connect. Please try again.';
  }
  if (error is StateError) return error.message;
  return 'Could not complete the request. Please try again.';
}
