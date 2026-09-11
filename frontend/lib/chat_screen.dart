import 'dart:async';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:uuid/uuid.dart';

import 'controllers/chat_controller.dart';
import 'models/chat.dart';
import 'services/conversation_repository.dart';
import 'widgets/restaurant_card.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({
    super.key,
    this.sessionId,
    this.initialTitle,
    this.controller,
  });
  final String? sessionId;
  final String? initialTitle;

  /// Allows widget tests to supply a controller without live Firebase or HTTP.
  final ChatController? controller;

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _textController = TextEditingController();
  final _speech = SpeechToText();
  final _tts = FlutterTts();
  late final ChatController _chat;
  bool _speechEnabled = false;
  bool _isListening = false;
  bool _submitting = false;
  bool get _busy => _chat.isBusy || _submitting;

  @override
  void initState() {
    super.initState();
    _chat =
        widget.controller ??
        ChatController(
          sessionId: widget.sessionId ?? const Uuid().v4(),
          existing: widget.sessionId != null,
          repository: ConversationRepository(
            userId: FirebaseAuth.instance.currentUser?.uid ?? '',
            currentUserId: () => FirebaseAuth.instance.currentUser?.uid,
          ),
        );
    _chat.addListener(_refresh);
    unawaited(_initializeSpeech());
    if (widget.sessionId != null) {
      unawaited(_chat.load());
    } else if (_chat.messages.isNotEmpty) {
      unawaited(_speak(_chat.messages.first.text));
    }
  }

  void _refresh() {
    if (mounted) setState(() {});
  }

  Future<void> _initializeSpeech() async {
    try {
      final enabled = await _speech.initialize(
        onStatus: (status) {
          if (mounted && (status == 'done' || status == 'notListening')) {
            setState(() => _isListening = false);
          }
        },
      );
      if (mounted) setState(() => _speechEnabled = enabled);
    } catch (_) {
      // Text input remains available if the device has no speech service.
    }
  }

  Future<void> _speak(String text) async {
    if (!mounted) return;
    try {
      await _tts.speak(text);
    } catch (_) {
      // A missing TTS engine should not fail a successful chat.
    }
  }

  Future<void> _stopListening() async {
    if (!_isListening) return;
    if (mounted) setState(() => _isListening = false);
    try {
      await _speech.stop();
    } catch (_) {}
  }

  Future<void> _stopVoice() async {
    await _stopListening();
    try {
      await _tts.stop();
    } catch (_) {}
  }

  Future<void> _startListening() async {
    if (!_speechEnabled || _busy) return;
    try {
      await _tts.stop();
      if (!mounted || _busy) return;
      setState(() => _isListening = true);
      await _speech.listen(
        onResult: _onSpeechResult,
        listenFor: const Duration(seconds: 30),
        pauseFor: const Duration(seconds: 5),
      );
    } catch (_) {
      if (mounted) setState(() => _isListening = false);
    }
  }

  void _onSpeechResult(SpeechRecognitionResult result) {
    if (!mounted || _busy) return;
    _textController.text = result.recognizedWords;
    if (result.finalResult) unawaited(_handleSubmitted(result.recognizedWords));
  }

  Future<void> _handleSubmitted(String input) async {
    if (_busy || input.trim().isEmpty) return;
    setState(() => _submitting = true);
    _textController.clear();
    try {
      // Sending text must not depend on a device's speech engine responding.
      unawaited(_stopVoice());
      final reply = await _chat.send(input);
      if (!mounted) return;
      if (reply != null) {
        unawaited(_speak(reply.text));
      } else {
        _textController.text = input;
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _openMaps(RestaurantInfo restaurant) async {
    final uri = Uri.https('www.google.com', '/maps/search/', {
      'api': '1',
      'query': '${restaurant.name}, ${restaurant.address}',
      if (restaurant.placeId != null) 'query_place_id': restaurant.placeId!,
    });
    try {
      final launched = await launchUrl(
        uri,
        mode: LaunchMode.externalApplication,
      );
      if (!launched && mounted) _showMapsError();
    } catch (_) {
      if (mounted) _showMapsError();
    }
  }

  void _showMapsError() => ScaffoldMessenger.of(
    context,
  ).showSnackBar(const SnackBar(content: Text('Could not open Google Maps')));

  @override
  void dispose() {
    _chat.removeListener(_refresh);
    _chat.dispose();
    unawaited(_speech.cancel().catchError((Object _) {}));
    unawaited(_tts.stop().catchError((Object _) => 0));
    _textController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(widget.initialTitle ?? 'Restaurant Finder AI')),
    body: Column(
      children: [
        Expanded(
          child: ListView.builder(
            reverse: true,
            padding: const EdgeInsets.all(8),
            itemCount: _chat.messages.length,
            itemBuilder: (context, index) => _message(_chat.messages[index]),
          ),
        ),
        if (_chat.notice != null)
          Padding(padding: const EdgeInsets.all(8), child: Text(_chat.notice!)),
        if (_chat.error != null)
          Padding(
            padding: const EdgeInsets.all(8),
            child: Text(
              _chat.error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ),
        if (_busy) const LinearProgressIndicator(),
        const Divider(height: 1),
        SafeArea(
          minimum: const EdgeInsets.only(bottom: 8),
          child: Padding(
            padding: const EdgeInsets.all(8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _textController,
                    enabled: !_busy,
                    minLines: 1,
                    maxLines: 4,
                    onSubmitted: _handleSubmitted,
                    decoration: const InputDecoration(
                      hintText: 'Message',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                IconButton(
                  tooltip: 'Voice input',
                  icon: Icon(_isListening ? Icons.mic_off : Icons.mic),
                  onPressed: _busy || !_speechEnabled
                      ? null
                      : _isListening
                      ? _stopListening
                      : _startListening,
                ),
                IconButton(
                  tooltip: 'Send',
                  icon: const Icon(Icons.send),
                  onPressed: _busy
                      ? null
                      : () => _handleSubmitted(_textController.text),
                ),
              ],
            ),
          ),
        ),
      ],
    ),
  );

  Widget _message(Message message) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 10),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisAlignment: message.isUser
          ? MainAxisAlignment.end
          : MainAxisAlignment.start,
      children: [
        if (!message.isUser)
          const CircleAvatar(child: Icon(Icons.restaurant_menu)),
        Flexible(
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 8),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: message.isUser ? Colors.deepOrange[100] : Colors.grey[200],
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(message.text),
                if (message.restaurants.isNotEmpty) ...[
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Text(
                      '${message.restaurants.length} restaurants found',
                    ),
                  ),
                  SizedBox(
                    height: 340,
                    child: ListView.builder(
                      scrollDirection: Axis.horizontal,
                      itemCount: message.restaurants.length,
                      itemBuilder: (context, index) => RestaurantCard(
                        restaurant: message.restaurants[index],
                        onTap: () => _openMaps(message.restaurants[index]),
                      ),
                    ),
                  ),
                ] else if (message.wasSearchRequest)
                  const Padding(
                    padding: EdgeInsets.only(top: 8),
                    child: Text(
                      'No restaurants found. Try another location or cuisine.',
                    ),
                  ),
              ],
            ),
          ),
        ),
        if (message.isUser) const CircleAvatar(child: Icon(Icons.person)),
      ],
    ),
  );
}
