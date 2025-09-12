// filepath: /Users/hossamzaki/StudioProjects/dineout/frontend/lib/services/conversation_service.dart
import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';
import '../models/conversation.dart';

class ConversationService {
  static const _storageKeyPrefix = 'conversations:'; // key per user
  static const _historyKeyPrefix = 'conversation_history:'; // key per conversation

  String _keyForUser(String? userId) => '$_storageKeyPrefix${userId ?? 'guest'}';
  String _historyKeyForConversation(String conversationId, String? userId) =>
      '$_historyKeyPrefix${userId ?? 'guest'}:$conversationId';

  Future<List<ConversationMeta>> getConversations({String? userId}) async {
    final prefs = await SharedPreferences.getInstance();
    final key = _keyForUser(userId);
    final raw = prefs.getString(key);
    if (raw == null || raw.isEmpty) return [];
    try {
      final List list = json.decode(raw) as List;
      return list
          .map((e) => ConversationMeta.fromMap(e as Map<String, dynamic>))
          .toList()
        ..sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
    } catch (_) {
      return [];
    }
  }

  Future<void> upsertConversation(ConversationMeta meta, {String? userId}) async {
    final prefs = await SharedPreferences.getInstance();
    final key = _keyForUser(userId);
    final existing = await getConversations(userId: userId);
    final idx = existing.indexWhere((c) => c.id == meta.id);
    if (idx >= 0) {
      // Preserve createdAt
      final current = existing[idx];
      existing[idx] = meta.copyWith(createdAt: current.createdAt);
    } else {
      existing.add(meta);
    }
    final encoded = json.encode(existing.map((e) => e.toMap()).toList());
    await prefs.setString(key, encoded);
  }

  Future<void> deleteConversation(String id, {String? userId}) async {
    final prefs = await SharedPreferences.getInstance();
    final key = _keyForUser(userId);
    final existing = await getConversations(userId: userId);
    existing.removeWhere((c) => c.id == id);
    final encoded = json.encode(existing.map((e) => e.toMap()).toList());
    await prefs.setString(key, encoded);
  }

  Future<void> clearAll({String? userId}) async {
    final prefs = await SharedPreferences.getInstance();
    final key = _keyForUser(userId);
    await prefs.remove(key);
  }

  Future<ConversationMeta?> getConversationMeta(String? conversationId, {String? userId}) async {
    if (conversationId == null) return null;
    final conversations = await getConversations(userId: userId);
    try {
      return conversations.firstWhere((c) => c.id == conversationId);
    } catch (_) {
      return null;
    }
  }

  Future<List<ConversationMessage>?> getConversationHistory(String? conversationId, {String? userId}) async {
    if (conversationId == null) return null;
    final prefs = await SharedPreferences.getInstance();
    final key = _historyKeyForConversation(conversationId, userId);
    final raw = prefs.getString(key);
    if (raw == null || raw.isEmpty) return null;
    try {
      final List list = json.decode(raw) as List;
      return list
          .map((e) => ConversationMessage.fromMap(e as Map<String, dynamic>))
          .toList();
    } catch (_) {
      return null;
    }
  }

  Future<void> saveConversationHistory(String conversationId, List<ConversationMessage> messages, {String? userId}) async {
    final prefs = await SharedPreferences.getInstance();
    final key = _historyKeyForConversation(conversationId, userId);
    final encoded = json.encode(messages.map((e) => e.toMap()).toList());
    await prefs.setString(key, encoded);
  }

  Future<void> addMessageToConversation(String conversationId, ConversationMessage message, {String? userId}) async {
    final existing = await getConversationHistory(conversationId, userId: userId) ?? [];
    existing.add(message);
    await saveConversationHistory(conversationId, existing, userId: userId);
  }

  /// Extract restaurant suggestion names from conversation history
  List<String> _extractRestaurantNames(List<ConversationMessage> messages) {
    final Set<String> restaurantNames = {};
    
    for (final message in messages) {
      if (message.restaurantSuggestions != null && message.restaurantSuggestions!.isNotEmpty) {
        for (final suggestion in message.restaurantSuggestions!) {
          final name = suggestion['name'] as String?;
          if (name != null && name.isNotEmpty) {
            restaurantNames.add(name);
          }
        }
      }
    }
    
    return restaurantNames.toList();
  }

  /// Extract restaurant photo URLs from conversation history
  List<String> _extractRestaurantPhotoUrls(List<ConversationMessage> messages) {
    final Set<String> photoUrls = {};
    
    for (final message in messages) {
      if (message.restaurantSuggestions != null && message.restaurantSuggestions!.isNotEmpty) {
        for (final suggestion in message.restaurantSuggestions!) {
          final photoUrl = suggestion['photo_url'] as String?;
          if (photoUrl != null && photoUrl.isNotEmpty) {
            photoUrls.add(photoUrl);
          }
        }
      }
    }
    
    return photoUrls.toList();
  }

  /// Count total restaurant suggestions in conversation history
  int _countRestaurantSuggestions(List<ConversationMessage> messages) {
    int count = 0;
    
    for (final message in messages) {
      if (message.restaurantSuggestions != null) {
        count += message.restaurantSuggestions!.length;
      }
    }
    
    return count;
  }

  /// Update conversation metadata with restaurant suggestions summary
  Future<void> updateConversationWithSuggestions(String conversationId, {String? userId}) async {
    final history = await getConversationHistory(conversationId, userId: userId);
    if (history == null || history.isEmpty) return;
    
    final meta = await getConversationMeta(conversationId, userId: userId);
    if (meta == null) return;
    
    final restaurantNames = _extractRestaurantNames(history);
    final restaurantPhotoUrls = _extractRestaurantPhotoUrls(history);
    final totalSuggestions = _countRestaurantSuggestions(history);
    
    final updatedMeta = meta.copyWith(
      restaurantSuggestionNames: restaurantNames,
      restaurantPhotoUrls: restaurantPhotoUrls,
      totalRestaurantSuggestions: totalSuggestions,
      updatedAt: DateTime.now(),
    );
    
    await upsertConversation(updatedMeta, userId: userId);
  }
}
