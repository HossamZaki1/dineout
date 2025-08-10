# Remedy Bot - Multi-Agent Action Analysis System

A sophisticated multi-agent system that analyzes actions, provides criticism, researches alternatives, and offers guidance for better decision-making.

## Architecture

The system consists of multiple specialized AI agents:

### Backend Agents
1. **Critic Agent** - Analyzes actions and identifies potential issues and risks
2. **Researcher Agent** - Researches better alternatives and best practices
3. **Guidance Agent** - Provides practical guidance for implementing better actions and dealing with consequences
4. **Coordinator Agent** - Synthesizes all agent outputs into coherent recommendations

### Storage System
- **ChromaDB Cloud** - Stores anonymized action analyses for learning and similarity matching
- Cloud-hosted for scalability and reliability
- Anonymization ensures privacy while enabling system learning

### Frontend
- **Flutter Mobile App** - Clean, intuitive interface for action analysis
- Real-time analysis with detailed breakdowns
- Expandable cards showing criticism, alternatives, research insights, and guidance

## Features

### Action Analysis
- Submit action descriptions and situational context
- Get comprehensive multi-agent analysis
- View confidence scores and processing time

### Detailed Insights
- **Criticism**: Areas of concern with severity levels
- **Alternatives**: Research-backed alternative actions
- **Research Findings**: Relevant insights from various sources
- **Consequence Guidance**: Strategies for dealing with potential outcomes

### Privacy & Learning
- All stored data is anonymized
- System learns from past analyses
- Similar situations inform future recommendations

## Setup Instructions

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Install dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   - Update `.env` file with your OpenAI API key and ChromaDB Cloud credentials
   - Your ChromaDB Cloud configuration is already set up:
     - Tenant: `2f695255-a693-428d-b6e4-bcffbbd35e56`
     - Database: `SelfHelpReceipes`
     - API Key: Already configured

4. **Validate configuration:**
   ```bash
   python validate_config.py
   ```

5. **Test ChromaDB connection:**
   ```bash
   python test_chroma.py
   ```

6. **Start the server:**
   ```bash
   ./start.sh
   ```

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install Flutter dependencies:**
   ```bash
   flutter pub get
   ```

3. **Run the app:**
   ```bash
   flutter run
   ```

## API Endpoints

### Main Analysis Endpoint
```
POST /analyze-action
```

**Request Body:**
```json
{
  "action_description": "Description of the action taken or planned",
  "situation_description": "Context and situation details"
}
```

**Response:**
```json
{
  "session_id": "unique-session-id",
  "criticism": [...],
  "alternatives": [...],
  "research_findings": [...],
  "consequence_guidance": [...],
  "summary": "Overall recommendation",
  "confidence_score": 0.85,
  "processing_time_seconds": 2.5
}
```

### Other Endpoints
- `GET /health` - System health check
- `GET /analytics/actions` - Anonymized analytics
- `POST /chat` - Legacy chat endpoint for backwards compatibility

## Technology Stack

### Backend
- **FastAPI** - High-performance API framework
- **LangChain** - LLM orchestration and chaining
- **OpenAI GPT-4** - Primary language model
- **ChromaDB** - Vector database for storing embeddings
- **Pydantic** - Data validation and serialization

### Frontend
- **Flutter** - Cross-platform mobile framework
- **Dio** - HTTP client for API communication
- **Material Design** - UI components and theming

## Configuration

### Environment Variables

**Backend (.env):**
```
OPENAI_API_KEY=your_openai_api_key
CHROMA_PERSIST_DIRECTORY=./chroma_db
HOST=0.0.0.0
PORT=8000
```

**Frontend (.env):**
```
API_BASE_URL=http://localhost:8000
```

## Usage Examples

### Example 1: Career Decision
**Action:** "I decided to quit my job without having another one lined up"
**Situation:** "I was feeling overwhelmed and stressed at work, my manager was being unreasonable"

**Analysis Includes:**
- Criticism about financial planning and timing
- Alternative approaches like job searching while employed
- Research on career transition best practices
- Guidance for managing financial stress during unemployment

### Example 2: Relationship Decision
**Action:** "I broke up with my partner via text message"
**Situation:** "We've been having issues and I wanted to avoid a confrontation"

**Analysis Includes:**
- Criticism about communication method and emotional impact
- Alternatives like in-person conversation or counseling
- Research on healthy relationship communication
- Guidance for healing and moving forward constructively

## Multi-Agent Workflow

1. **Input Processing** - User provides action and situation descriptions
2. **Parallel Analysis** - Critic and Researcher agents work simultaneously
3. **Guidance Generation** - Guidance agent uses criticism and research results
4. **Coordination** - Coordinator synthesizes all outputs into coherent response
5. **Storage** - Anonymized analysis stored for future learning
6. **Response** - Comprehensive analysis returned to user

## Privacy & Ethics

- All personal information is anonymized before storage
- No personally identifiable information is retained
- System focuses on constructive criticism and helpful guidance
- Designed to support better decision-making, not replace professional advice

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues, feature requests, or questions:
- Create an issue in the GitHub repository
- Check the documentation
- Review existing issues for solutions

---

**Note:** This system is designed to provide guidance and insights for decision-making. It should not replace professional advice for serious matters involving health, legal issues, or major life decisions.
