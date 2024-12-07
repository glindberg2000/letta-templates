"""
Configuration management for Letta quickstart
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Server configuration
LETTA_SERVER_PORT = os.getenv('LETTA_SERVER_PORT', '8283')
LETTA_SERVER_HOST = os.getenv('LETTA_SERVER_HOST', 'localhost')
LETTA_BASE_URL = f"http://{LETTA_SERVER_HOST}:{LETTA_SERVER_PORT}"

# OpenAI configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def validate_config():
    """Validate required configuration variables"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY must be set in environment") 