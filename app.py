import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from datetime import datetime
from typing import Dict, Any

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    STORAGE_DIR,
    MAX_CONVERSATION_MESSAGES,
    HOST,
    PORT
)
from memory import memory
from rag import rag
from pdf_handler import pdf_handler
from prompts import PROMPTS


# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)


class ChatbotManager:
    """Manages chatbot interactions with Gemini API"""
    
    def __init__(self):
        """Initialize the chatbot manager"""
        self.model = genai.GenerativeModel(GEMINI_MODEL)
    
    def format_prompt(self, prompt_template: str, context: Dict[str, Any]) -> str:
        """
        Format the prompt template with user context
        
        Args:
            prompt_template: Template string with placeholders
            context: Dictionary with values to fill in
            
        Returns:
            Formatted prompt string
        """
        # Ensure missing keys don't leave raw placeholders in the prompt.
        # Provide sensible defaults for common keys used in prompts.
        defaults = {
            "user_name": "there",
            "user_background": "your background",
            "day_number": "0",
            "task_assigned": "no",
            "quiz_assigned": "no",
            "quiz_topic": "the quiz",
            "total_questions": "0",
            "score": "0",
            "wrong_question_numbers": "none",
            "task_description": "",
            "submission_type": "",
            "deadline": ""
        }

        safe_context = {**defaults, **(context or {})}

        try:
            return prompt_template.format(**safe_context)
        except Exception:
            # If formatting still fails for any reason, return a cleaned-up
            # version where braces are removed to avoid showing raw placeholders.
            return prompt_template.replace("{", "").replace("}", "")
    
    def get_system_prompt(self, session_type: str, user_context: Dict[str, Any]) -> str:
        """
        Get the appropriate system prompt based on session type
        
        Args:
            session_type: Type of session (career_counselor, quiz_feedback, technical_review)
            user_context: User context data
            
        Returns:
            Formatted system prompt
        """
        prompt_template = PROMPTS.get(session_type)
        
        if not prompt_template:
            raise ValueError(f"Unknown session type: {session_type}")
        
        return self.format_prompt(prompt_template, user_context)
    
    def generate_response(self, 
                         system_prompt: str,
                         conversation_history: str,
                         user_message: str,
                         use_rag: bool = True) -> str:
        """
        Generate a response using Gemini API with RAG
        
        Args:
            system_prompt: The system prompt/instructions
            conversation_history: Previous conversation context
            user_message: Current user message
            use_rag: Whether to use RAG for retrieval
            
        Returns:
            Generated response from the model
        """
        rag_context = ""
        if use_rag:
            # Retrieve relevant documents from RAG
            retrieved_docs = rag.retrieve_documents(user_message, limit=5)
            rag_context = rag.format_context(retrieved_docs)
        
        full_prompt = f"""{system_prompt}

{rag_context}

--- CONVERSATION HISTORY ---
{conversation_history if conversation_history else "(No previous conversation)"}

--- CURRENT USER MESSAGE ---
User: {user_message}

Assistant Response:"""
        
        try:
            response = self.model.generate_content(full_prompt)
            return response.text.strip()
        except Exception as e:
            return f"Error generating response: {str(e)}"


# Initialize chatbot manager
chatbot = ChatbotManager()



# ROUTES FOR WEB INTERFACE

@app.route('/')
def index():
    """Serve the chat interface"""
    return render_template('index.html')


@app.route('/api/newchats', methods=['POST'])
def api_new_chat():
    """API route for new chat (same as /newchats)"""
    return new_chat()


@app.route('/api/chats', methods=['POST'])
def api_chat():
    """API route for continuing chat (same as /chats)"""
    return chat()


@app.route('/api/upload-pdf', methods=['POST'])
def upload_pdf():
    """Upload and process a PDF file with tech validation"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        user_id = request.form.get('user_id')
        
        if not file or file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"error": "Only PDF files are allowed"}), 400
        
        # Step 1: Save and extract PDF
        pdf_data = pdf_handler.save_pdf(file, user_id)
        
        # Step 2: Check if tech-related
        tech_check = pdf_handler.is_tech_related(
            pdf_data['full_text'],
            pdf_data['filename']
        )
        
        # If not tech-related, reject it
        if not tech_check['is_tech']:
            return jsonify({
                "pdf_id": pdf_data['pdf_id'],
                "filename": pdf_data['filename'],
                "is_tech_related": False,
                "confidence": tech_check['confidence'],
                "reason": tech_check['reason'],
                "message": "I only review tech-related PDFs. This document doesn't appear to contain tech content like programming, AI, data science, cybersecurity, or other tech domains."
            }), 400
        
        # Step 3: Process to RAG (only if tech-related)
        status_msg = pdf_handler.process_pdf_to_rag(
            pdf_data['pdf_id'],
            pdf_data['full_text'],
            pdf_data['filename']
        )
        
        return jsonify({
            "pdf_id": pdf_data['pdf_id'],
            "filename": pdf_data['filename'],
            "text_preview": pdf_data['text_preview'],
            "pages": pdf_data['metadata']['pages'],
            "is_tech_related": True,
            "confidence": tech_check['confidence'],
            "tech_keywords_found": tech_check['tech_keywords_found'],
            "status": status_msg,
            "message": f"✓ PDF '{pdf_data['filename']}' has been uploaded successfully! It's recognized as a tech document. Now ask questions about it!"
        }), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ENDPOINTS

@app.route('/newchats', methods=['POST'])
def new_chat():
    """
    Start a new chat session
    
    Request body:
    {
        "user_id": "user123",
        "session_type": "career_counselor|quiz_feedback|technical_review",
        "user_context": {
            "user_name": "John",
            "user_background": "Marketing",
            "day_number": 5,
            "task_assigned": "yes",
            "quiz_assigned": "no"
        }
    }
    
    Response:
    {
        "conversation_id": "user123_career_counselor",
        "session_type": "career_counselor",
        "message": "Welcome message from bot"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({"error": "Request body is empty"}), 400
        
        user_id = data.get('user_id')
        session_type = data.get('session_type')
        user_context = data.get('user_context', {})
        
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
        if not session_type:
            return jsonify({"error": "session_type is required"}), 400
        
        # Validate session type
        if session_type not in PROMPTS:
            return jsonify({
                "error": f"Invalid session_type. Must be one of: {list(PROMPTS.keys())}"
            }), 400
        
        # Generate conversation ID
        conversation_id = memory.get_conversation_id(user_id, session_type)
        
        # Clear previous conversation for fresh start
        memory.clear_conversation(conversation_id)
        
        # Get system prompt
        system_prompt = chatbot.get_system_prompt(session_type, user_context)
        
        # Generate initial message
        initial_message = """Start the conversation appropriately based on your role. 
        Be warm, welcoming, and establish context. Keep it brief."""
        
        response = chatbot.generate_response(
            system_prompt=system_prompt,
            conversation_history="",
            user_message=initial_message
        )
        
        # Save the initial bot message to memory
        memory.add_message(conversation_id, "assistant", response)
        
        return jsonify({
            "conversation_id": conversation_id,
            "session_type": session_type,
            "user_id": user_id,
            "message": response,
            "timestamp": datetime.now().isoformat()
        }), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/chats', methods=['POST'])
def chat():
    """
    Continue an existing chat session
    
    Request body:
    {
        "conversation_id": "user123_career_counselor",
        "user_id": "user123",
        "session_type": "career_counselor",
        "message": "User's message",
        "user_context": {
            "user_name": "John",
            "user_background": "Marketing"
        }
    }
    
    Response:
    {
        "conversation_id": "user123_career_counselor",
        "message": "Assistant response",
        "conversation_history": [...]
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({"error": "Request body is empty"}), 400
        
        conversation_id = data.get('conversation_id')
        user_id = data.get('user_id')
        session_type = data.get('session_type')
        user_message = data.get('message')
        user_context = data.get('user_context', {})
        
        if not conversation_id:
            return jsonify({"error": "conversation_id is required"}), 400
        if not user_message:
            return jsonify({"error": "message is required"}), 400
        if not session_type:
            return jsonify({"error": "session_type is required"}), 400
        
        # Validate session type
        if session_type not in PROMPTS:
            return jsonify({
                "error": f"Invalid session_type. Must be one of: {list(PROMPTS.keys())}"
            }), 400
        
        # Save user message to memory
        memory.add_message(conversation_id, "user", user_message)
        
        # Get system prompt
        system_prompt = chatbot.get_system_prompt(session_type, user_context)
        
        # Get conversation context
        conversation_history = memory.get_context(
            conversation_id,
            max_messages=MAX_CONVERSATION_MESSAGES
        )
        
        # Generate response
        response = chatbot.generate_response(
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            user_message=user_message,
            use_rag=True
        )
        
        # Save assistant response to memory
        memory.add_message(conversation_id, "assistant", response)
        
        # Get updated conversation history
        full_history = memory.get_messages(conversation_id)
        
        return jsonify({
            "conversation_id": conversation_id,
            "message": response,
            "user_id": user_id,
            "session_type": session_type,
            "conversation_history": full_history,
            "timestamp": datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# PDF UPLOAD ENDPOINTS

@app.route('/api/user-pdfs/<user_id>', methods=['GET'])
def get_user_pdfs(user_id):
    """Get all PDFs uploaded by a user"""
    try:
        pdfs = pdf_handler.get_user_pdfs(user_id)
        
        return jsonify({
            "user_id": user_id,
            "pdfs": pdfs,
            "count": len(pdfs)
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/search-pdf-content', methods=['POST'])
def search_pdf_content():
    """Search within uploaded PDF content"""
    try:
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({"error": "query is required"}), 400
        
        results = rag.retrieve_documents(query, category="user_pdf", limit=5)
        
        return jsonify({
            "query": query,
            "results": results,
            "count": len(results)
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ERROR HANDLERS

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({"error": "Internal server error"}), 500



# MAIN

if __name__ == '__main__':
    print(f"Starting Career Guidance Chatbot on {HOST}:{PORT}")
    print(f"Using Gemini Model: {GEMINI_MODEL}")
    print(f"Storage Directory: {STORAGE_DIR}")
    print("\nAvailable endpoints:")
    print("  POST /newchats - Start a new conversation")
    print("  POST /chats - Continue a conversation")
    
    app.run(host=HOST, port=PORT, debug=app.config['DEBUG'])
