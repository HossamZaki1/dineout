import 'conversation.dart';

class Message {
  final String text;
  final bool isUser;
  final List<RestaurantInfo> restaurants;
  final bool wasSearchRequest;

  const Message({
    required this.text,
    this.isUser = true,
    this.restaurants = const [],
    this.wasSearchRequest = false,
  });

  factory Message.fromStored(ConversationMessage message) => Message(
    text: message.content,
    isUser: message.role == 'user',
    restaurants: (message.restaurantSuggestions ?? [])
        .map(RestaurantInfo.fromJson)
        .toList(),
    wasSearchRequest: (message.restaurantSuggestions ?? []).isNotEmpty,
  );
}

class RestaurantInfo {
  final String name;
  final String address;
  final double rating;
  final bool? isOpenNow;
  final List<String> photoUrls;
  final String summary;
  final String? placeId;
  final String? googleMapsUri;
  final String? nextOpeningDisplay;

  RestaurantInfo.fromJson(Map<String, dynamic> json)
    : name = json['name'] ?? '',
      address = json['address'] ?? '',
      rating = (json['rating'] as num?)?.toDouble() ?? 0,
      isOpenNow = json['is_open_now'],
      photoUrls = json['photo_url'] != null ? [json['photo_url']] : [],
      summary = json['summary'] ?? '',
      placeId = json['place_id'],
      googleMapsUri = json['google_maps_uri'],
      nextOpeningDisplay = json['next_opening_display'];
}

class ChatReply {
  final String text;
  final List<Map<String, dynamic>> suggestions;
  final bool searchPerformed;

  const ChatReply({
    required this.text,
    this.suggestions = const [],
    this.searchPerformed = false,
  });

  factory ChatReply.fromJson(Map<String, dynamic> json) => ChatReply(
    text: json['response'] as String,
    suggestions: List<Map<String, dynamic>>.from(json['suggestions'] ?? []),
    searchPerformed: json['search_performed'] == true,
  );
}

class ConversationPage {
  final List<ConversationMeta> items;
  final String? nextCursor;
  const ConversationPage(this.items, this.nextCursor);
}

class LoadedConversation {
  final List<ConversationMessage> messages;
  final bool fromCache;
  const LoadedConversation(this.messages, {this.fromCache = false});
}
