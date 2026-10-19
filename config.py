import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyA6OlvhK_yoncKNe5Su_EYy9Z3AAqV9rbg')

# Flask configuration
DEBUG = True
SECRET_KEY = os.urandom(24) 