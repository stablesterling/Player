import logging
import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
)
from yt_dlp import YoutubeDL
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()

# ✅ Correct usage: read BOT_TOKEN from environment OR use fallback
BOT_TOKEN = os.getenv("BOT_TOKEN", "8438947587:AAF798xzM76oR8_TY8UyP7u_FpjeFLF7Kss")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
PORT = int(os.getenv("PORT", 8080))
DOWNLOAD_PATH = './downloads'
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

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
    'default_search': 'ytsearch5',  # Top 5 results
}

# --- /start Command ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎶 *Welcome to VoFo Music Bot!*\n\n"
        "Send me any *song name or artist* and I’ll fetch YouTube results.\n"
        "Then tap a button to play or download the song. 🎧",
        parse_mode='Markdown'
    )

# --- /help Command ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 *How to use:*\n"
        "1️⃣ Send any song or artist name\n"
        "2️⃣ Choose from the search results\n"
        "3️⃣ I’ll send the MP3 audio file 🎵",
        parse_mode='Markdown'
    )

# --- Handle Song Search ---
async def handle_music_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if not query:
        await update.message.reply_text("❌ Please send a valid song name.")
        return

    status_message = await update.message.reply_text(f"🔍 Searching YouTube for: *{query}* ...", parse_mode='Markdown')

    try:
        with YoutubeDL(YDL_OPTS) as ydl:
            results = ydl.extract_info(query, download=False)["entries"]

        if not results:
            await status_message.edit_text("⚠️ No results found. Try another name.")
            return

        # Create inline buttons for top results
        buttons = []
        for vid in results:
            title = re.sub(r'[^\w\s]', '', vid["title"])[:50]
            video_id = vid.get("id")
            if video_id:
                buttons.append([InlineKeyboardButton(title, callback_data=video_id)])

        reply_markup = InlineKeyboardMarkup(buttons)
        await status_message.edit_text(
            f"🎧 *Top results for:* `{query}`\nTap a song to play ↓",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Search error: {e}")
        await status_message.edit_text("❌ Error while searching. Try again later.")

# --- Handle Song Selection (Download/Play) ---
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    video_id = query.data

    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        await query.edit_message_text("🎵 Fetching audio... Please wait ⏳")

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
            filename = ydl.prepare_filename(info)
            filename = filename.replace(".webm", ".mp3").replace(".m4a", ".mp3")

        title = info.get("title", "Unknown Song")
        await query.message.reply_audio(
            audio=open(filename, 'rb'),
            caption=f"🎶 *{title}*\n\nPowered by VoFo Music Bot 🎧",
            parse_mode='Markdown'
        )

        os.remove(filename)

    except Exception as e:
        logger.error(f"Download error: {e}")
        await query.edit_message_text("❌ Failed to download or send the audio.")

# --- Main Entry Point ---
def main():
    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN is missing in environment variables!")

    # --- Local Polling (for testing) ---
    if not WEBHOOK_URL or WEBHOOK_URL == "YOUR_RENDER_OR_RAILWAY_URL":
        logger.info("🚀 Starting bot in LOCAL POLLING mode.")
        application = Application.builder().token(BOT_TOKEN).build()

        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_music_search))
        application.add_handler(CallbackQueryHandler(button_callback_handler))

        application.run_polling(allowed_updates=Update.ALL_TYPES)
        return

    # --- Webhook Mode (for Render/Railway) ---
    logger.info(f"🚀 Starting bot in WEBHOOK mode on port {PORT}.")
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_music_search))
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="",
        webhook_url=WEBHOOK_URL
    )

if __name__ == '__main__':
    main()
