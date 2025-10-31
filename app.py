import logging
import os
import re
import requests
from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv
from telegram import Bot

# --- Load environment variables ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))
CHAT_ID = os.getenv("CHAT_ID")  # Telegram chat ID for sending messages

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Flask app ---
app = Flask(__name__, static_folder=".", static_url_path="")

# --- Telegram Bot ---
bot = Bot(token=BOT_TOKEN)

# This function searches music using Telegram (e.g., via inline search or bot command)
def search_music_via_telegram(query):
    """
    Dummy function — simulate getting Telegram file URLs.
    You can later modify this to use your own bot’s logic or database.
    """
    # Here, you could query Telegram (e.g., your saved music channel)
    # For demo, we simulate some fake data
    results = [
        {"title": f"{query} - Track 1", "file_id": "AUDIO_FILE_ID_1"},
        {"title": f"{query} - Track 2", "file_id": "AUDIO_FILE_ID_2"},
    ]
    return results


def get_telegram_file_url(file_id):
    """Get Telegram file download URL for playback."""
    try:
        file = bot.get_file(file_id)
        return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    except Exception as e:
        logger.error(f"Error fetching Telegram file URL: {e}")
        return None


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
        songs = search_music_via_telegram(query)
        return jsonify({"results": songs})
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({"error": "Failed to search"}), 500


@app.route("/play/<file_id>")
def play_song(file_id):
    try:
        url = get_telegram_file_url(file_id)
        if url:
            return jsonify({"url": url})
        else:
            return jsonify({"error": "Failed to get audio"}), 500
    except Exception as e:
        logger.error(f"Play error: {e}")
        return jsonify({"error": "Failed to play audio"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
