import os
import re
import logging
from flask import Flask, request, jsonify, send_from_directory
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from yt_dlp import YoutubeDL
from dotenv import load_dotenv
import asyncio

# --- Load Environment Variables ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
PORT = int(os.getenv("PORT", 8080))
DOWNLOAD_PATH = './downloads'
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Flask App ---
app = Flask(__name__, static_folder='static')

# --- YT-DLP Config ---
YDL_OPTS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'extract_flat': 'in_playlist',
    'default_search': 'ytsearch20',  # Top 20 results
}

# --- Telegram Bot Application ---
application = Application.builder().token(BOT_TOKEN).build()

# --- /start Command ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎶 Welcome to VoFo Music Bot!\nSend a song name to play."
    )

# --- /help Command ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send a song name and I will show the top 20 results. Click to play!"
    )

# --- Handle Song Search ---
async def handle_music_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if not query:
        await update.message.reply_text("❌ Please send a valid song name.")
        return

    status_msg = await update.message.reply_text(f"🔍 Searching: {query} ...")
    try:
        with YoutubeDL(YDL_OPTS) as ydl:
            results = ydl.extract_info(query, download=False)["entries"]

        if not results:
            await status_msg.edit_text("⚠️ No results found.")
            return

        buttons = []
        for vid in results:
            title = re.sub(r'[^\w\s]', '', vid["title"])[:50]
            vid_id = vid.get("id")
            if vid_id:
                buttons.append([InlineKeyboardButton(title, callback_data=vid_id)])

        reply_markup = InlineKeyboardMarkup(buttons)
        await status_msg.edit_text(
            f"🎧 Top results for: {query}",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        await status_msg.edit_text("❌ Search error.")

# --- Handle Button Callback (Play) ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    video_id = query.data

    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        await query.edit_message_text("🎵 Fetching audio...")

        opts = {
            'format': 'bestaudio/best',
            'outtmpl': f"{DOWNLOAD_PATH}/%(title)s.%(ext)s",
            'quiet': True,
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3")

        title = info.get("title", "Unknown")
        await query.message.reply_audio(audio=open(filename, 'rb'), caption=f"🎶 {title}")

        os.remove(filename)
    except Exception as e:
        logger.error(f"Playback error: {e}")
        await query.edit_message_text("❌ Failed to play audio.")

# --- Add Telegram Handlers ---
application.add_handler(CommandHandler("start", start_command))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_music_search))
application.add_handler(CallbackQueryHandler(button_callback))

# --- Flask Routes ---
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/search', methods=['POST'])
def search():
    data = request.json
    query = data.get("query", "")
    if not query:
        return jsonify({"error": "No query provided"}), 400

    async def send_query():
        # Send to Telegram bot to search
        fake_update = Update(update_id=0, message=None)
        # Not fully functional in Flask for async bot; use frontend → Telegram directly in production
        return

    asyncio.run(send_query())
    return jsonify({"message": f"Search request sent: {query}"})

# --- Run Flask App ---
if __name__ == '__main__':
    # Start Telegram bot in background
    application.run_polling()
    # Flask app will be served by Railway automatically
