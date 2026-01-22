import os
import logging
import tempfile
import asyncio
import glob
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL

# Configuration
TOKEN = "8086508947:AAFPs8ToECrX9bkLZmwftb38cIiPpgHt_l4"

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the command /start is issued."""
    await update.message.reply_text(
        "مرحباً بك! أنا بوت تنزيل الفيديوهات. \n"
        "أرسل لي رابط فيديو من تيك توك أو إنستغرام وسأقوم بتنزيله لك بدون علامة مائية."
    )

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Downloads video from a URL and sends it back to the user."""
    url = update.message.text
    chat_id = update.message.chat_id
    
    # Send initial message
    status_message = await context.bot.send_message(chat_id, "جارٍ معالجة الرابط وبدء التنزيل... ⏳")

    # Create a temporary file path
    temp_dir = tempfile.gettempdir()
    output_path_base = os.path.join(temp_dir, f"{chat_id}_video")
    
    # yt-dlp options
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': f"{output_path_base}.%(ext)s",
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        # Fixed postprocessor options
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }

    downloaded_file_path = None
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            
            # Get the actual file path from info_dict
            # yt-dlp stores the final file path in 'requested_downloads'
            if 'requested_downloads' in info_dict and len(info_dict['requested_downloads']) > 0:
                downloaded_file_path = info_dict['requested_downloads'][0].get('filepath')
            
            # Fallback: check for the file manually
            if not downloaded_file_path or not os.path.exists(downloaded_file_path):
                files = glob.glob(f"{output_path_base}.*")
                if files:
                    # Filter out .part or other temp files
                    valid_files = [f for f in files if not f.endswith(('.part', '.ytdl', '.temp'))]
                    if valid_files:
                        downloaded_file_path = valid_files[0]

            if downloaded_file_path and os.path.exists(downloaded_file_path):
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_message.message_id,
                    text="تم التنزيل بنجاح. جارٍ الإرسال إلى تيليجرام... 📤"
                )
                
                # Send the video file
                with open(downloaded_file_path, 'rb') as video_file:
                    await context.bot.send_video(
                        chat_id=chat_id,
                        video=video_file,
                        caption=f"✅ تم تنزيل الفيديو بدون علامة مائية من: {url}",
                        supports_streaming=True,
                        read_timeout=600, 
                        write_timeout=600
                    )
                
                await context.bot.delete_message(chat_id, status_message.message_id)
            else:
                raise FileNotFoundError("لم يتم العثور على ملف الفيديو بعد التنزيل.")

    except Exception as e:
        logger.error(f"Error downloading or sending video: {e}")
        error_msg = str(e)
        if "Unsupported URL" in error_msg:
            friendly_error = "عذراً، هذا الرابط غير مدعوم أو غير صحيح."
        else:
            friendly_error = f"❌ حدث خطأ أثناء معالجة الفيديو. يرجى المحاولة مرة أخرى لاحقاً."
            
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_message.message_id,
            text=friendly_error
        )
    finally:
        # Cleanup
        try:
            for f in glob.glob(f"{output_path_base}*"):
                os.remove(f)
            logger.info(f"Cleaned up temporary files for chat_id {chat_id}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
