import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_SHEETS_CREDS_FILE = os.getenv("GOOGLE_SHEETS_CREDS_FILE", "creds.json")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Haydays Staff Checkin")
MANAGER_TELEGRAM_ID = os.getenv("MANAGER_TELEGRAM_ID")
ANALYST_TELEGRAM_ID = os.getenv("ANALYST_TELEGRAM_ID")
