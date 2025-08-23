import 'dart:async';
import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:uuid/uuid.dart';

// Data Models
class Message {
  final String text;
  final bool isUser;
  final List<RestaurantInfo> restaurants;

  Message({required this.text, this.isUser = true, this.restaurants = const []});
}

class RestaurantInfo {
  final String name;
  final String address;
  final double rating;
  final bool isOpenNow;
  final List<String> photoUrls;
  final String summary;

  RestaurantInfo.fromJson(Map<String, dynamic> json)
      : name = json['name'],
        address = json['address'],
        rating = (json['rating'] as num).toDouble(),
        isOpenNow = json['is_open_now'],
        photoUrls = List<String>.from(json['photo_urls']),
        summary = json['summary'];
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _textController = TextEditingController();
  final List<Message> _messages = [];
  bool _isLoading = false;
  String? _sessionId;
  final Dio _dio = Dio();

  // Speech and TTS
  final SpeechToText _speechToText = SpeechToText();
  final FlutterTts _flutterTts = FlutterTts();
  bool _speechEnabled = false;
  bool _isListening = false;

  @override
  void initState() {
    super.initState();
    _initSpeech();
    _sessionId = const Uuid().v4();
    _addInitialMessage();
  }

  void _initSpeech() async {
    _speechEnabled = await _speechToText.initialize();
    setState(() {});
  }

  void _addInitialMessage() {
    const initialMessage = "Hi! I can help you find a great place to eat. Where are you looking for restaurants?";
    setState(() {
      _messages.insert(0, Message(text: initialMessage, isUser: false));
    });
    _speak(initialMessage);
  }

  Future<void> _speak(String text) async {
    await _flutterTts.speak(text);
  }

  Future<void> _startListening() async {
    if (!_speechEnabled) return;
    await _stopListening(); // Ensure it's stopped before starting
    await _flutterTts.stop();
    setState(() => _isListening = true);
    await _speechToText.listen(
      onResult: _onSpeechResult,
      listenFor: const Duration(seconds: 30),
      pauseFor: const Duration(seconds: 5),
    );
  }

  Future<void> _stopListening() async {
    if (!_isListening) return;
    await _speechToText.stop();
    setState(() => _isListening = false);
  }

  void _onSpeechResult(SpeechRecognitionResult result) {
    setState(() {
      _textController.text = result.recognizedWords;
    });
    if (result.finalResult) {
      _handleSubmitted(result.recognizedWords);
    }
  }

  Future<void> _handleSubmitted(String text) async {
    if (text.trim().isEmpty) return;

    _textController.clear();
    _stopListening();

    setState(() {
      _messages.insert(0, Message(text: text));
      _isLoading = true;
    });

    try {
      final history = _messages
          .where((m) => m.text.isNotEmpty)
          .take(10) // Limit history size
          .map((m) => {"role": m.isUser ? "user" : "assistant", "content": m.text})
          .toList()
          .reversed
          .toList();

      final response = await _dio.post(
        '${dotenv.env['API_URL']}/chat',
        data: {
          'user_input': text,
          'session_id': _sessionId,
          'history': history,
        },
      );

      final data = response.data;
      final botResponse = data['response'];
      final List<RestaurantInfo> restaurants = (data['suggestions'] as List)
          .map((r) => RestaurantInfo.fromJson(r))
          .toList();

      setState(() {
        _messages.insert(0, Message(text: botResponse, isUser: false, restaurants: restaurants));
      });
      _speak(botResponse);

    } catch (e) {
      final errorMessage = "Sorry, I'm having trouble connecting. Please try again later.";
      setState(() {
        _messages.insert(0, Message(text: errorMessage, isUser: false));
      });
      _speak(errorMessage);
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Restaurant Finder AI'),
        elevation: 2,
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              reverse: true,
              padding: const EdgeInsets.all(8.0),
              itemCount: _messages.length,
              itemBuilder: (_, int index) => _buildMessageItem(_messages[index]),
            ),
          ),
          if (_isLoading) const LinearProgressIndicator(),
          const Divider(height: 1.0),
          // Use SafeArea to ensure content is not hidden by system UI
          SafeArea(
            minimum: const EdgeInsets.only(bottom: 8.0),
            child: _buildTextComposer(),
          ),
        ],
      ),
    );
  }

  Widget _buildMessageItem(Message message) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 10.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: message.isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        children: [
          if (!message.isUser)
            const CircleAvatar(child: Icon(Icons.restaurant_menu)),
          Flexible(
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: 8.0),
              padding: const EdgeInsets.all(12.0),
              decoration: BoxDecoration(
                color: message.isUser ? Colors.deepOrange[100] : Colors.grey[200],
                borderRadius: BorderRadius.circular(12.0),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(message.text),
                  if (message.restaurants.isNotEmpty)
                    _buildRestaurantList(message.restaurants),
                ],
              ),
            ),
          ),
          if (message.isUser)
            const CircleAvatar(child: Icon(Icons.person)),
        ],
      ),
    );
  }

  Widget _buildRestaurantList(List<RestaurantInfo> restaurants) {
    return Container(
      margin: const EdgeInsets.only(top: 10),
      height: 320,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        itemCount: restaurants.length,
        itemBuilder: (context, index) {
          final restaurant = restaurants[index];
          return SizedBox(
            width: 250,
            child: Card(
              clipBehavior: Clip.antiAlias,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    height: 120,
                    width: double.infinity,
                    child: restaurant.photoUrls.isNotEmpty
                        ? Image.network(
                            restaurant.photoUrls.first,
                            fit: BoxFit.cover,
                            errorBuilder: (context, error, stackTrace) => const Icon(Icons.broken_image),
                          )
                        : Container(color: Colors.grey[300], child: const Icon(Icons.camera_alt)),
                  ),
                  Padding(
                    padding: const EdgeInsets.all(8.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(restaurant.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                        const SizedBox(height: 4),
                        Text(restaurant.address, style: Theme.of(context).textTheme.bodySmall),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Icon(Icons.star, color: Colors.amber, size: 16),
                            Text(' ${restaurant.rating}'),
                            const SizedBox(width: 8),
                            Text(
                              restaurant.isOpenNow ? 'OPEN' : 'CLOSED',
                              style: TextStyle(
                                color: restaurant.isOpenNow ? Colors.green : Colors.red,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(restaurant.summary, maxLines: 3, overflow: TextOverflow.ellipsis),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildTextComposer() {
    return IconTheme(
      data: IconThemeData(color: Theme.of(context).colorScheme.primary),
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 8.0),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey.shade300),
          borderRadius: BorderRadius.circular(25.0),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: Container(
                constraints: const BoxConstraints(
                  minHeight: 40.0,
                  maxHeight: 120.0,
                ),
                child: TextField(
                  controller: _textController,
                  onSubmitted: _handleSubmitted,
                  maxLines: null,
                  minLines: 1,
                  textInputAction: TextInputAction.newline,
                  decoration: const InputDecoration(
                    hintText: "Message",
                    border: InputBorder.none,
                    contentPadding: EdgeInsets.symmetric(horizontal: 16.0, vertical: 10.0),
                  ),
                ),
              ),
            ),
            IconButton(
              icon: Icon(_isListening ? Icons.mic_off : Icons.mic),
              onPressed: _isListening ? _stopListening : _startListening,
            ),
            IconButton(
              icon: const Icon(Icons.send),
              onPressed: () => _handleSubmitted(_textController.text),
            ),
          ],
        ),
      ),
    );
  }
}
