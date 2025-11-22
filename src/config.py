import os
from dotenv import load_dotenv

# Load variables from the .env file in the project root
load_dotenv()

# Read the API key from environment
FMP_API_KEY = os.getenv("FMP_API_KEY")

if FMP_API_KEY is None:
    raise ValueError("FMP_API_KEY not found. Please set it in your .env file.")
