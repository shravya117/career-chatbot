import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Flask Configuration
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
DEBUG = FLASK_ENV == 'development'

# Gemini API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')

# Conversation Memory Configuration
STORAGE_DIR = os.getenv('STORAGE_DIR', 'conversation_data')
MAX_CONVERSATION_MESSAGES = int(os.getenv('MAX_CONVERSATION_MESSAGES', '10'))

# Flask App Configuration
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', '5005'))

# Validation
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set. Please create a .env file with your API key.")
