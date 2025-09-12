// filepath: /Users/hossamzaki/StudioProjects/dineout/frontend/lib/models/conversation.dart
import 'dart:convert';

class ConversationMeta {
  final String id; // sessionId
  final String title;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String lastMessagePreview;
  final List<String> restaurantSuggestionNames; // Names of restaurants suggested in this conversation
  final int totalRestaurantSuggestions; // Total count of restaurant suggestions
  final List<String> restaurantPhotoUrls; // Photo URLs of restaurants suggested in this conversation

  ConversationMeta({
    required this.id,
    required this.title,
    required this.createdAt,
    required this.updatedAt,
    required this.lastMessagePreview,
    this.restaurantSuggestionNames = const [],
    this.totalRestaurantSuggestions = 0,
    this.restaurantPhotoUrls = const [],
  });

  ConversationMeta copyWith({
    String? id,
    String? title,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? lastMessagePreview,
    List<String>? restaurantSuggestionNames,
    int? totalRestaurantSuggestions,
    List<String>? restaurantPhotoUrls,
  }) {
    return ConversationMeta(
      id: id ?? this.id,
      title: title ?? this.title,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      lastMessagePreview: lastMessagePreview ?? this.lastMessagePreview,
      restaurantSuggestionNames: restaurantSuggestionNames ?? this.restaurantSuggestionNames,
      totalRestaurantSuggestions: totalRestaurantSuggestions ?? this.totalRestaurantSuggestions,
      restaurantPhotoUrls: restaurantPhotoUrls ?? this.restaurantPhotoUrls,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'title': title,
      'createdAt': createdAt.toIso8601String(),
      'updatedAt': updatedAt.toIso8601String(),
      'lastMessagePreview': lastMessagePreview,
      'restaurantSuggestionNames': restaurantSuggestionNames,
      'totalRestaurantSuggestions': totalRestaurantSuggestions,
      'restaurantPhotoUrls': restaurantPhotoUrls,
    };
  }

  factory ConversationMeta.fromMap(Map<String, dynamic> map) {
    return ConversationMeta(
      id: map['id'] as String,
      title: map['title'] as String,
      createdAt: DateTime.parse(map['createdAt'] as String),
      updatedAt: DateTime.parse(map['updatedAt'] as String),
      lastMessagePreview: (map['lastMessagePreview'] ?? '') as String,
      restaurantSuggestionNames: map['restaurantSuggestionNames'] != null 
          ? List<String>.from(map['restaurantSuggestionNames'])
          : [],
      totalRestaurantSuggestions: (map['totalRestaurantSuggestions'] ?? 0) as int,
      restaurantPhotoUrls: map['restaurantPhotoUrls'] != null 
          ? List<String>.from(map['restaurantPhotoUrls'])
          : [],
    );
  }

  String toJson() => json.encode(toMap());

  factory ConversationMeta.fromJson(String source) => ConversationMeta.fromMap(json.decode(source) as Map<String, dynamic>);
}

class ConversationMessage {
  final String role; // 'user' or 'assistant'
  final String content;
  final DateTime timestamp;
  final List<Map<String, dynamic>>? restaurantSuggestions; // Add restaurant suggestions

  ConversationMessage({
    required this.role,
    required this.content,
    required this.timestamp,
    this.restaurantSuggestions,
  });

  Map<String, dynamic> toMap() {
    return {
      'role': role,
      'content': content,
      'timestamp': timestamp.toIso8601String(),
      'restaurant_suggestions': restaurantSuggestions,
    };
  }

  factory ConversationMessage.fromMap(Map<String, dynamic> map) {
    return ConversationMessage(
      role: map['role'] as String,
      content: map['content'] as String,
      timestamp: DateTime.parse(map['timestamp'] as String),
      restaurantSuggestions: map['restaurant_suggestions'] != null 
          ? List<Map<String, dynamic>>.from(map['restaurant_suggestions'])
          : null,
    );
  }
}
