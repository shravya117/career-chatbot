# Career Guidance Chatbot (Simple)

Lightweight Flask chatbot using Google's Gemini API with conversation memory.

Quick summary:
- Start a new conversation: `POST /newchats`
- Continue a conversation: `POST /chats`

Requirements
- Python 3.8+
- A Gemini API key (set in `.env`)

Quick start
1. Install dependencies:
```bash
pip install -r requirements.txt
```
2. Copy and update env:
```bash
cp .env.example .env
# Edit .env and add GEMINI_API_KEY
```
3. Run the server:
```bash
python app.py
```

Testing (Postman / curl)
- New conversation (`/newchats`):
```json
POST http://localhost:5001/newchats
Content-Type: application/json

{
  "user_id": "user_001",
  "session_type": "career_counselor",
  "user_context": { "user_name": "Sarah" }
}
```
- Continue conversation (`/chats`):
```json
POST http://localhost:5001/chats
Content-Type: application/json

{
  "conversation_id": "user_001_career_counselor",
  "user_id": "user_001",
  "session_type": "career_counselor",
  "message": "Can I switch to tech?",
  "user_context": { "user_name": "Sarah" }
}
```

Conversation storage
- Conversations are saved to `conversation_data/` as `{user_id}_{session_type}.json`.

Files
- `app.py` - Flask app and endpoints
- `config.py` - Loads `.env`
- `memory.py` - Conversation storage
- `prompts.py` - Prompt templates


## How It Works

1. **Start Conversation** (`/newchats`):
   - Creates unique `conversation_id`
   - Clears any previous conversation
   - Generates initial greeting from bot
   - Saves response to memory

2. **Continue Conversation** (`/chats`):
   - Saves user message to memory
   - Loads full conversation history
   - Sends conversation + new message to Gemini
   - Receives context-aware response
   - Saves response to memory
   - Returns new message + full history

3. **Memory Management**:
   - Conversations stored in JSON files
   - Each conversation identified by `{user_id}_{session_type}`
   - Up to `MAX_CONVERSATION_MESSAGES` included in API context







