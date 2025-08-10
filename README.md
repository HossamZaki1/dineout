# Remedy Bot - Multi-Agent Action Analysis System

# DineOut AI 🍽️🤖

**Your personal AI-powered assistant for discovering the perfect restaurant.**

DineOut AI is a full-stack application that leverages a sophisticated multi-agent AI system to provide real-time restaurant recommendations. It features a voice-driven conversational interface built with Flutter and a powerful backend powered by Python, FastAPI, and Google's Gemini & Maps APIs.

---

## ✨ Features

- **🗣️ Conversational Interface**: Interact with the app using natural voice commands. Just ask for what you're looking for!
- **📍 Real-Time Search**: Get up-to-the-minute information on restaurants that are currently open in your desired location.
- **🧠 AI-Powered Summaries**: The AI agent reads through restaurant details to provide you with a quick, insightful summary of its vibe and specialties.
- **📸 Photo Previews**: See photos of the restaurants directly from Google Maps to get a feel for the atmosphere.
- **🚀 Cross-Platform**: Built with Flutter for a seamless experience on both Android and iOS devices.

---

## 🛠️ Architecture & Tech Stack

The application is built with a modern, decoupled architecture.

### **Frontend**
- **Framework**: [Flutter](https://flutter.dev/)
- **State Management**: `setState` (for simplicity in this version)
- **HTTP Client**: [Dio](https://pub.dev/packages/dio)
- **Voice Interaction**: [speech_to_text](https://pub.dev/packages/speech_to_text) & [flutter_tts](https://pub.dev/packages/flutter_tts)

### **Backend**
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **LLM Orchestration**: [LangChain](https://www.langchain.com/)
- **Language Model (LLM)**: [Google Gemini Pro](https://deepmind.google/technologies/gemini/)
- **External APIs**: [Google Maps Platform (Places API)](https://developers.google.com/maps/documentation/places/web-service)
- **Server**: [Uvicorn](https://www.uvicorn.org/)

---

## 🚀 Getting Started

Follow these instructions to get the project up and running on your local machine.

### **Prerequisites**

- [Flutter SDK](https://docs.flutter.dev/get-started/install) (version 3.x)
- [Python](https://www.python.org/downloads/) (version 3.10+) & `pip`
- [Git](https://git-scm.com/)
- A **Google API Key** with the "Generative Language API" and "Places API" enabled. You can get this from the [Google Cloud Console](https://console.cloud.google.com/).

### **1. Backend Setup**

First, set up and run the Python backend server.

```bash
# 1. Navigate to the backend directory
cd backend

# 2. Create and activate a Python virtual environment
python3 -m venv venv
source venv/bin/activate
# On Windows, use: venv\Scripts\activate

# 3. Install the required dependencies
pip install -r requirements.txt

# 4. Create a .env file in the `backend` directory
#    and add your Google API key
echo "GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY_HERE"" > .env

# 5. Run the FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The backend server should now be running on `http://0.0.0.0:8000`.

### **2. Frontend Setup**

In a **new terminal**, set up and run the Flutter application.

```bash
# 1. Find your computer's local IP address.
#    On macOS/Linux:
hostname -I | awk '{print $1}'
#    On Windows:
ipconfig | findstr "IPv4 Address"

# 2. Navigate to the frontend directory
cd frontend

# 3. Create a .env file in the `frontend` directory.
#    Replace <YOUR_COMPUTER_IP> with the IP from the previous step.
echo "API_URL="http://<YOUR_COMPUTER_IP>:8000"" > .env
#    Example: echo "API_URL="http://192.168.1.10:8000"" > .env

# 4. Get the Flutter dependencies
flutter pub get

# 5. Run the app (ensure an emulator is running or a device is connected)
flutter run
```

---

## 🕹️ Usage

1.  Launch the app and you'll see the landing screen.
2.  Tap **"Start Searching"**.
3.  The chat screen will appear, and the AI assistant will greet you.
4.  Tap the **microphone icon** to start speaking. Ask for restaurants (e.g., "Find me a good sushi place in San Francisco").
5.  The app will process your request, show you the results, and speak the summary back to you.

---

## 📂 Project Structure

```
.
├── ai/                  # (Future use for AI model assets)
├── backend/             # FastAPI Backend
│   ├── app/             # Main application package
│   │   ├── agents/      # Multi-agent AI system
│   │   ├── models/      # Pydantic data models
│   │   └── main.py      # FastAPI app entrypoint
│   ├── requirements.txt # Python dependencies
│   └── .env.example     # Environment variable template
│
├── frontend/            # Flutter Frontend
│   ├── lib/             # Main Dart source code
│   │   ├── main.dart    # App entrypoint
│   │   ├── landing_screen.dart
│   │   └── chat_screen.dart
│   ├── pubspec.yaml     # Flutter dependencies
│   └── .env.example     # Environment variable template
│
└── README.md            # You are here!
```

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.