import os
import logging
import asyncio
import cloudinary
import cloudinary.uploader
from docx import Document
import edge_tts
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from flask import Flask

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("dyzeagpkw"),
    api_key=os.getenv("737729173351875"),
    api_secret=os.getenv("CgHVO1-0SP8Hl3aYwKj3dA6HWwU")
)

VOICES = {
    "male": ["ar-DZ-IsmaelNeural", "ar-AE-HamdanNeural"],
    "female": ["ar-DZ-AminaNeural", "ar-AE-FatimaNeural"]
}

# Flask app
flask_app = Flask(__name__)


# Define telegram_app globally
telegram_app = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome! Please upload a Word document to begin.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    file = await document.get_file()  # Await the coroutine to get the File object
    file_path = await file.download()

    context.user_data['document'] = file_path
    keyboard = [
        [InlineKeyboardButton("Male", callback_data='male')],
        [InlineKeyboardButton("Female", callback_data='female')],
    ]
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Please choose a voice type:", reply_markup=InlineKeyboardMarkup(keyboard))

async def voice_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    voice_type = query.data
    context.user_data['voice_type'] = voice_type

    keyboard = [
        [InlineKeyboardButton(voice, callback_data=voice) for voice in VOICES[voice_type]]
    ]
    await query.edit_message_text("Please choose a specific voice:", reply_markup=InlineKeyboardMarkup(keyboard))

async def confirm_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    selected_voice = query.data
    context.user_data['selected_voice'] = selected_voice

    keyboard = [
        [InlineKeyboardButton("Yes", callback_data='yes')],
        [InlineKeyboardButton("No", callback_data='no')]
    ]
    await query.edit_message_text(f"Do you want to proceed with the {selected_voice} voice?", reply_markup=InlineKeyboardMarkup(keyboard))

async def process_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'yes':
        await query.edit_message_text("Your project is in process...")
        
        # Process the document with the selected voice
        voice = context.user_data['selected_voice']
        document_path = context.user_data['document']
        output_file = f"output_{voice}.mp3"
        
        text = extract_text(document_path)
        await save_text_to_audio(text, voice, output_file)
        
        try:
            # Upload to Cloudinary
            response = cloudinary.uploader.upload_large(output_file, resource_type="raw")
            url = response.get('secure_url', '')

            if url:
                await query.message.reply_text(f"Congratulations! Here is your audio file: {url}")
            else:
                await query.message.reply_text("Sorry, there was an error uploading your file.")
        except Exception as e:
            logging.error(f"Error uploading file: {e}")
            await query.message.reply_text(f"An error occurred: {e}")
    else:
        await query.edit_message_text("Operation canceled.")

# Additional functions to extract text and save as audio
def extract_text(doc_path):
    try:
        doc = Document(doc_path)
        full_text = [paragraph.text for paragraph in doc.paragraphs]
        return '\n'.join(full_text)
    except Exception as e:
        logging.error(f"Error extracting text: {e}")
        return ""

async def save_text_to_audio(text, voice, output_file):
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
    except Exception as e:
        logging.error(f"Error saving text to audio: {e}")

def create_app():
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(CallbackQueryHandler(voice_selection, pattern="^(male|female)$"))
    application.add_handler(CallbackQueryHandler(confirm_voice, pattern="^(ar-.+Neural)$"))
    application.add_handler(CallbackQueryHandler(process_audio, pattern="^(yes|no)$"))

    return application

@flask_app.route('/')
def index():
    global telegram_app
    if telegram_app is None:
        telegram_app = create_app()
        telegram_app.run_polling()
    return "Telegram bot is running!"

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
