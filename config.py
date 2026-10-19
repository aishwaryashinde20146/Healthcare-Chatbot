import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# Flask configuration
DEBUG = True
SECRET_KEY = os.urandom(24) 