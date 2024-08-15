from flask import Flask
import threading
import bot  # Import the bot logic

flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return "Telegram bot is running!"

def run_bot_thread():
    bot.run_bot()

if __name__ == "__main__":
    # Start the Telegram bot in a separate thread
    bot_thread = threading.Thread(target=run_bot_thread)
    bot_thread.start()

    # Run the Flask app
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
