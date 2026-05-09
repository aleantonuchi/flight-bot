import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN         = os.getenv("TELEGRAM_BOT_TOKEN")
AI_PROVIDER            = os.getenv("AI_PROVIDER", "groq")
GEMINI_API_KEY         = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY           = os.getenv("GROQ_API_KEY", "")
ANTHROPIC_API_KEY      = os.getenv("ANTHROPIC_API_KEY", "")
TRAVELPAYOUTS_TOKEN    = os.getenv("TRAVELPAYOUTS_TOKEN", "")
DATABASE_URL           = os.getenv("DATABASE_URL", "")
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "21600"))  # 6 horas
MAX_MONITOR_DAYS       = 3
PORT                   = int(os.getenv("PORT", "8080"))
