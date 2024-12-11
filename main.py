import os
import logging
from dotenv import load_dotenv
from bot.search_bot import DealSearchBot

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',  # Simplified format
    handlers=[
        logging.StreamHandler(),  # Console handler
    ]
)

# Load environment variables
load_dotenv()

def main():
    """Main function to run the bot."""
    try:
        # Get required environment variables
        database_id = os.getenv("NOTION_DATABASE_ID")
        if not database_id:
            raise ValueError("NOTION_DATABASE_ID environment variable is not set")

        # Initialize and run bot
        bot = DealSearchBot(debug=True, database_id=database_id)
        print("🤖 Deal Search Bot is starting...")
        bot.run()
    except Exception as e:
        logging.error(f"Error starting bot: {e}")

if __name__ == '__main__':
    main()
