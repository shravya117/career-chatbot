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
from prompts import PROMPTS


# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

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
                         user_message: str) -> str:
        """
        Generate a response using Gemini API
        
        Args:
            system_prompt: The system prompt/instructions
            conversation_history: Previous conversation context
            user_message: Current user message
            
        Returns:
            Generated response from the model
        """
        full_prompt = f"""{system_prompt}

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
            user_message=user_message
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
