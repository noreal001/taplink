import os
from dotenv import load_dotenv

load_dotenv()

PORT = os.getenv("PORT", 8000)