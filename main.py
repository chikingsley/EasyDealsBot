import os
import logging
from dotenv import load_dotenv
from bot.search_bot import DealSearchBot

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    try:
        # Get required environment variables
        database_id = os.getenv("NOTION_DATABASE_ID")
        if not database_id:
            raise ValueError("NOTION_DATABASE_ID environment variable is not set")

        # Initialize and run the bot
        bot = DealSearchBot(debug=True, database_id=database_id)
        print("🤖 Deal Search Bot is starting...")
        bot.run()
    except Exception as e:
        logging.error(f"Error starting bot: {str(e)}")
        raise

if __name__ == '__main__':
    main()
