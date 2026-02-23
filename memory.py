import json
import os
from datetime import datetime
from typing import List, Dict, Any


class ConversationMemory:
    """Manages conversation history storage and retrieval"""
    
    def __init__(self, storage_dir: str = 'conversation_data'):
        """
        Initialize conversation memory
        
        Args:
            storage_dir: Directory to store conversation files
        """
        self.storage_dir = storage_dir
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self):
        """Create storage directory if it doesn't exist"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
    
    def get_conversation_id(self, user_id: str, session_type: str) -> str:
        """Generate conversation ID"""
        return f"{user_id}_{session_type}"
    
    def _get_file_path(self, conversation_id: str) -> str:
        """Get file path for a conversation"""
        return os.path.join(self.storage_dir, f"{conversation_id}.json")
    
    def add_message(self, conversation_id: str, role: str, content: str):
        """
        Add a message to conversation history
        
        Args:
            conversation_id: ID of the conversation
            role: "user" or "assistant"
            content: Message content
        """
        file_path = self._get_file_path(conversation_id)
        
        # Load existing messages
        messages = self._load_messages(file_path)
        
        # Add new message
        messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Save messages
        self._save_messages(file_path, messages)
    
    def get_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Get all messages in a conversation
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            List of messages
        """
        file_path = self._get_file_path(conversation_id)
        return self._load_messages(file_path)
    
    def get_context(self, conversation_id: str, max_messages: int = 10) -> str:
        """
        Get formatted conversation context for AI
        
        Args:
            conversation_id: ID of the conversation
            max_messages: Maximum number of previous messages to include
            
        Returns:
            Formatted conversation context as string
        """
        messages = self.get_messages(conversation_id)
        
        # Get last max_messages
        recent_messages = messages[-max_messages:]
        
        # Format as conversation string
        context = ""
        for msg in recent_messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            context += f"{role}: {msg['content']}\n"
        
        return context.strip()
    
    def clear_conversation(self, conversation_id: str):
        """
        Clear all messages in a conversation
        
        Args:
            conversation_id: ID of the conversation
        """
        file_path = self._get_file_path(conversation_id)
        if os.path.exists(file_path):
            os.remove(file_path)
    
    def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """
        Get conversation metadata
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Summary with message count and timestamps
        """
        messages = self.get_messages(conversation_id)
        
        if not messages:
            return {
                "conversation_id": conversation_id,
                "message_count": 0,
                "created_at": None,
                "last_message_at": None
            }
        
        return {
            "conversation_id": conversation_id,
            "message_count": len(messages),
            "created_at": messages[0]["timestamp"],
            "last_message_at": messages[-1]["timestamp"]
        }
    
    def _load_messages(self, file_path: str) -> List[Dict[str, Any]]:
        """Load messages from file"""
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading messages: {e}")
            return []
    
    def _save_messages(self, file_path: str, messages: List[Dict[str, Any]]):
        """Save messages to file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(messages, f, indent=2)
        except Exception as e:
            print(f"Error saving messages: {e}")


# Global memory instance
memory = ConversationMemory()
