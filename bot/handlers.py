## Module that handles user commands and messages for the HowGayBot
from telegram import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    Update, 
    Document,
    ChatMember, 
    ChatMemberUpdated,
)
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ChatMemberHandler,
    ContextTypes,
    filters,
)
from utils.storage import (
    log_stat,
    get_user_stats_all,
    get_user_stats_nice,
    get_leaderboard,
    get_last_update,
    update_last_timestamp,
    delete_chat_data,
    get_chat_stats_all,
    get_users_all,
)
import re, json
from datetime import datetime, date
from collections import defaultdict
import logging
logger = logging.getLogger(__name__)

GAYNESS_RE = re.compile(r'I am (\d+)% gay')
SELECT_STATS_MODE = 1

def setup_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("mystats", mystats)],
        states={
            SELECT_STATS_MODE: [CallbackQueryHandler(handle_stats_mode)],
        },
        fallbacks=[],
    ))
    app.add_handler(CommandHandler("backfill", backfill))
    app.add_handler(MessageHandler(filters.Document.FileExtension("json"), handle_json_upload))
    app.add_handler(MessageHandler(filters.TEXT, process_message))
    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    
# === COMMAND HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    # Initialize config if needed
    existing = get_last_update(chat_id)
    if existing == datetime.min:
        update_last_timestamp(chat_id, datetime.min)

    msg = (
        "👋 *Welcome to use @HowGayBotStats_bot!*\n"
        "I will track your gay status in this group, shared via @HowGayBot, from now.\n\n"
        "*Commands:*\n"
        "/mystats — View your own stats\n"
        "/leaderboard — See the group's leaderboard\n"
        "/backfill — (Optional) Upload chat history JSON to update the database\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

    
async def mystats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask user whether to see all stats or only nice ones."""
    keyboard = [
        [InlineKeyboardButton("All", callback_data="all")],
        [InlineKeyboardButton("Nice numbers only", callback_data="nice")],
    ]
    await update.message.reply_text(
        "Which stats do you want to see?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return SELECT_STATS_MODE

async def handle_stats_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    mode = query.data  # 'all' or 'nice'
    user_id = query.from_user.id
    chat_id = str(query.message.chat.id)
    nice_only = (mode == "nice")
    
    # logger.debug(f"Chosen mode: {mode}, nice_only: {nice_only} - for user {user_id} in chat {chat_id}")
    # logger.debug(f"All stats: {get_chat_stats_all()}")
    # logger.debug(f"All users: {get_users_all()}")

    stats = get_user_stats_nice(chat_id, user_id) if nice_only else get_user_stats_all(chat_id, user_id)
    
    await query.edit_message_text(stats or "No stats yet! Start using @HowGayBot to log your gayness.")
    return ConversationHandler.END

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    output = get_leaderboard(chat_id)

    await update.message.reply_text(output)
    
# Allow for backfill of data from exported Telegram chat JSON
async def backfill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please upload the exported Telegram chat JSON file.")

# Handle the uploaded JSON file
async def handle_json_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document:
        await update.message.reply_text("Please upload a valid JSON file.")
        return

    document: Document = update.message.document

    if not document.file_name.endswith(".json"):
        await update.message.reply_text("Only .json files are supported.")
        return

    file = await document.get_file()
    chat_id = str(update.effective_chat.id)
    content = await file.download_as_bytearray()
    data = json.loads(content)

    count = 0
    for message in data.get("messages", []):
        if message.get("via_bot") != "@HowGayBot":
            continue

        text = message.get("text", "")
        if isinstance(text, list):  # Mixed entity case
            text = "".join(t["text"] if isinstance(t, dict) else str(t) for t in text)

        m = GAYNESS_RE.search(text)
        if not m:
            continue

        percent = int(m.group(1))
        ts = datetime.fromisoformat(message["date"])
        
        from_id = message.get("from_id", "unknown")
        if isinstance(from_id, str) and from_id.startswith("user"):
            user_id = int(from_id.replace("user", ""))
        elif isinstance(from_id, int):
            user_id = from_id
        else:
            user_id = "unknown"
            
        name = message.get("from", "")
        username = ""  # Not included in Telegram export

        log_stat(chat_id, user_id, username, name, percent, ts)
        count += 1

    await update.message.reply_text(f"Backfill complete. {count} messages added.")
    
# === MAIN MESSAGE HANDLER ===
async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    chat_id = str(update.effective_chat.id)

    # logger.debug(f"Processing message in chat {chat_id}: {msg}")
    
    # Check if the message contains the gayness percentage
    m = GAYNESS_RE.search(msg)
    if not m:
        return
    
    if not update.message.via_bot or update.message.via_bot.username != "HowGayBot":
        return

    message_time = update.message.date.replace(tzinfo=None)
    user = update.effective_user
    percent = int(m.group(1))

    # Get last update timestamp
    last_ts = get_last_update(chat_id)

    # Only process newer messages
    if message_time < last_ts:
        return

    log_stat(
        chat_id=chat_id,
        user_id=user.id,
        username=user.username or "",
        name=user.full_name,
        percent=percent,
        ts=message_time
    )

    update_last_timestamp(chat_id, message_time)
    
# === CHAT MEMBER HANDLER ===
## if bot is removed from a chat, delete its data
async def handle_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = update.my_chat_member.new_chat_member.status
    if status in ['left', 'kicked']:
        chat_id = update.effective_chat.id
        delete_chat_data(chat_id)
        logger.info(f"Bot removed from chat {chat_id}, data deleted")
        await context.bot.send_message(chat_id=chat_id, text="Bot removed, data deleted.")