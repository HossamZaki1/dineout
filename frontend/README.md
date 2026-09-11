# DineQuest Flutter app

See the [root README](../README.md) for backend setup, Firebase configuration and
API contracts. Set `API_URL` in `.env`; this file is bundled in the app, so it
must contain only public client settings, never backend API keys.

```bash
flutter pub get
flutter analyze
flutter test
flutter run
```

`ChatScreen` handles rendering and speech. `ChatController` owns messages,
busy/error state and cancellation. `ConversationRepository` treats the backend
as authoritative and maintains a per-user cache of successful operations.
`PhotoService` resolves photos through the authenticated API before loading
their key-free image URLs.

Tests use fake repositories, HTTP adapters, local preferences and the Google
sign-in platform interface; no live Firebase, Maps or Gemini calls are required.
