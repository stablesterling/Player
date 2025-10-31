import logging
import os
import re
from flask import Flask, request, jsonify, send_file
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from yt_dlp import YoutubeDL
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))

# --- Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- YT-DLP Config ---
YDL_OPTS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'extract_flat': 'in_playlist',
    'default_search': 'ytsearch10',
}

# --- Flask App ---
app = Flask(__name__, static_folder=".", static_url_path="")

@app.route('/')
def home():
    return send_file("index.html")

@app.route('/search', methods=['POST'])
def search_song():
    data = request.json
    song_name = data.get('query')
    if not song_name:
        return {"error": "No song name provided"}, 400
    try:
        with YoutubeDL(YDL_OPTS) as ydl:
            results = ydl.extract_info(song_name, download=False)["entries"]
        songs = [{"title": re.sub(r'[^\w\s]', '', vid["title"]),
                  "id": vid["id"]} for vid in results if vid.get("id")]
        return {"results": songs}
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {"error": "Failed to search"}, 500

# --- Telegram Bot Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎶 Welcome! Send a song name to search and play.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send a song name to search and play.")

async def handle_music_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if not query:
        await update.message.reply_text("❌ Please send a valid song name.")
        return

    status_message = await update.message.reply_text(
        f"🔍 Searching YouTube for: *{query}* ...", parse_mode='Markdown'
    )
    try:
        with YoutubeDL(YDL_OPTS) as ydl:
            results = ydl.extract_info(query, download=False)["entries"]

        if not results:
            await status_message.edit_text("⚠️ No results found.")
            return

        msg = "🎵 Top results (click to play on web app):\n\n"
        for vid in results:
            if vid.get("id") and vid.get("title"):
                # Link points to your web app which streams the song
                msg += f"{re.sub(r'[^\w\s]', '', vid['title'])}: http://localhost:{PORT}/play/{vid['id']}\n"

        await status_message.edit_text(msg)
    except Exception as e:
        logger.error(f"Bot search error: {e}")
        await status_message.edit_text("❌ Error while searching.")

# --- Main Function ---
def main():
    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN missing!")

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_music_search))
    application.run_polling()

if __name__ == '__main__':
    main()
