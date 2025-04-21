import os
import logging
import threading
from bot import setup_bot
from app import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Import Flask app for gunicorn
from app import app

def run_discord_bot():
    """Run the Discord bot in a separate thread"""
    # Get the bot token from environment variables
    token = os.getenv("DISCORD_TOKEN", "MTI3NDQyMTIzMTM4MjI5ODY0NQ.GJf0Sb.CPC49kEH3Uni5FQrLWcTBZTjL4rTRhEhGrVAiM")
    
    try:
        # Setup and run the bot
        bot = setup_bot()
        bot.run(token)
    except Exception as e:
        logger.error(f"Error starting the bot: {e}")

# This is for running the bot directly with `python main.py`
if __name__ == "__main__":
    try:
        # Just run the Discord bot - web app is handled by gunicorn
        run_discord_bot()
    except Exception as e:
        logger.error(f"Error starting Discord bot: {e}")
