import logging
import os
import re
from flask import Flask, request, jsonify, send_file
from yt_dlp import YoutubeDL
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# --- Load environment variables ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- yt-dlp options ---
YDL_OPTS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'extract_flat': 'in_playlist',
    'default_search': 'ytsearch10',
}

# --- Flask app ---
app = Flask(__name__, static_folder=".", static_url_path="")

# --- Helper function using Telegram bot logic ---
def search_youtube(query):
    """Return top 10 results with title and video ID."""
    with YoutubeDL(YDL_OPTS) as ydl:
        results = ydl.extract_info(query, download=False)["entries"]
    songs = [
        {"title": re.sub(r'[^\w\s]', '', vid["title"]), "id": vid["id"]}
        for vid in results if vid.get("id")
    ]
    return songs

# --- Flask routes ---
@app.route('/')
def home():
    return send_file("index.html")

@app.route("/search", methods=["POST"])
def search_song():
    data = request.json
    query = data.get("query")
    if not query:
        return jsonify({"error": "No song name provided"}), 400
    try:
        songs = search_youtube(query)
        return jsonify({"results": songs})
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({"error": "Failed to search"}), 500

@app.route("/play/<video_id>")
def play_song(video_id):
    """Return direct audio URL for <audio> tag."""
    try:
        with YoutubeDL({'format': 'bestaudio/best', 'quiet': True}) as ydl:
            info = ydl.extract_info(video_id, download=False)
            return jsonify({"url": info['url']})
    except Exception as e:
        logger.error(f"Play error: {e}")
        return jsonify({"error": "Failed to get audio"}), 500

# --- Telegram bot commands ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎶 Welcome! Send a song name to search and play.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send a song name to search and play.")

async def handle_music_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if not query:
        await update.message.reply_text("❌ Please send a valid song name.")
        return
    try:
        songs = search_youtube(query)
        if not songs:
            await update.message.reply_text("⚠️ No results found.")
            return
        msg = "🎵 Top results:\n\n"
        for song in songs:
            msg += f"{song['title']}: /play/{song['id']}\n"
        await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"Bot search error: {e}")
        await update.message.reply_text("❌ Error while searching.")

def run_telegram_bot():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN missing!")
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_music_search))
    application.run_polling()

if __name__ == "__main__":
    import threading
    # Run Telegram bot in separate thread
    threading.Thread(target=run_telegram_bot, daemon=True).start()
    # Run Flask app
    app.run(host="0.0.0.0", port=PORT)
