import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder
from bot.handlers import setup_handlers
from utils.logger import init_logger

# Load environment variables
load_dotenv()

# Load token from .env
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing from .env")

# Init logger to file + console
init_logger("logs/gayness_bot_stats.log")

# Build the Telegram bot application
app = ApplicationBuilder().token(TOKEN).build()
setup_handlers(app)

if __name__ == "__main__":
    app.run_polling()
