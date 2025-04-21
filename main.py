import os
import logging
from bot import setup_bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def run_discord_bot():
    """Run the Discord bot"""
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
        logger.info("Starting Discord Premium Key Bot...")
        # Run the Discord bot
        run_discord_bot()
    except Exception as e:
        logger.error(f"Error starting Discord bot: {e}")
