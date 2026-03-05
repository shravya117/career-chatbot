##Career Guidance Chatbot – Project Documentation


1. System Overview
The Career Guidance Chatbot is an AI-powered conversational system that helps users transition into technology careers. 
It provides career guidance, learning support, and technical assistance through interactive conversations.

Core Features:
• AI-based career mentoring
• Context-aware conversations with session memory
• Document-based knowledge retrieval (RAG)
• PDF upload and validation for technical documents
• Persistent conversation history per user session


2. System Architecture
The system follows a layered architecture consisting of a frontend interface, backend API, knowledge retrieval system, 
and an LLM for response generation.

Main Components:
• Frontend – Chat interface and file upload
• Backend API – Handles chat requests and session management
• Memory Manager – Stores and retrieves conversation history
• Document Processor – Extracts and validates PDF content
• Knowledge Retrieval (RAG) – Finds relevant document information
• LLM Engine – Generates responses using prompts and context


3. User Interaction Flow
Starting a Conversation:
- User opens the chatbot interface.
- A new conversation session is created.
- The chatbot sends an initial greeting.

Continuing a Conversation:
- User sends a message.
- Conversation history is retrieved.
- Relevant documents are searched (RAG).
- A prompt is built with history and knowledge.
- The LLM generates a response.
- The response is saved and returned to the user.



4. Data Flow
User Opens Chatbot → User Sends Message →Frontend Interface → Flask Backend (app.py) → Conversation Memory Retrieval (memory.py) → Knowledge Retrieval (RAG - rag.py) →
Prompt Construction (prompts.py) → LLM Processing (Gemini / Ollama) → Response Generated → Conversation Saved → Response Sent to Frontend → Answer Displayed to User


5. Knowledge Retrieval (RAG)
The chatbot uses Retrieval-Augmented Generation (RAG) to improve responses.
Process:
- User query is analyzed.
- Relevant documents are searched.
- Top results are selected.
- Information is injected into the prompt.
- The LLM generates a response using the retrieved context.



6. Document Processing
When a PDF is uploaded:
- File type and size are validated.
- Text is extracted from the document.
- Content is scanned for technical keywords.
- A confidence score determines if the document is tech-related.
- Valid documents are added to the knowledge base.
Maximum file size: 16 MB.


7. Conversation Memory
Conversations are stored in JSON format with timestamps.
Features:
• Persistent chat history
• Role-based messages (user/assistant)
• Context window management
• Storage per conversation session
