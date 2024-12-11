import os
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    CallbackContext,
    Application
)
from services.ai_service import AIService
from services.notion_service import NotionService
from models.user_session import UserSession

logger = logging.getLogger(__name__)

class DealSearchBot:
    def __init__(self, debug: bool = False, database_id: str = None):
        # Initialize services
        self.ai_service = AIService()
        self.notion_service = NotionService(
            notion_token=os.getenv("NOTION_TOKEN"),
            database_id=database_id if database_id else os.getenv("NOTION_DATABASE_ID")
        )
        
        # Create application
        self.app = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
        
        # Add handlers
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(CallbackQueryHandler(self.button_click))
        
        # Set debug mode
        self.debug = debug
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        
        # Store user sessions
        self.user_sessions = {}

    def run(self):
        """Start the bot."""
        self.app.run_polling()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /start is issued."""
        welcome_message = (
            "👋 Welcome to the Deal Search Bot!\n\n"
            "I can help you search for deals using natural language. "
            "Just describe what you're looking for, and I'll find the most relevant deals.\n\n"
            "For example, try:\n"
            "- 'Show me deals from India'\n"
            "- 'Find offers with CPA pricing model'\n"
            "- 'Search for deals from partner XYZ'\n\n"
            "Use /help to see more options."
        )
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /help is issued."""
        help_message = (
            "🔍 Here's how to use the Deal Search Bot:\n\n"
            "1. Search by country/region:\n"
            "   - 'Show deals from UK'\n"
            "   - 'Find offers in TIER1 countries'\n\n"
            "2. Search by traffic source:\n"
            "   - 'Facebook deals'\n"
            "   - 'Google traffic offers'\n\n"
            "3. Search by partner:\n"
            "   - 'Deals from partner XYZ'\n\n"
            "4. Search by pricing model:\n"
            "   - 'CPA offers'\n"
            "   - 'CPL deals'\n\n"
            "5. Combine criteria:\n"
            "   - 'Facebook deals from UK with CPA model'\n\n"
            "Use natural language - I'll understand what you're looking for! 😊"
        )
        await update.message.reply_text(help_message)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle user messages and search for deals."""
        try:
            # Get user message
            message_text = update.message.text
            chat_id = update.effective_chat.id
            
            # Parse search query
            search_params = await self.ai_service.parse_search_query(message_text)
            
            # Search for deals
            deals = await self.notion_service.search_deals(search_params)
            
            if not deals:
                await update.message.reply_text(
                    "No deals found matching your criteria. Try a different search query."
                )
                return
            
            # Store deals in user session
            self.user_sessions[chat_id] = UserSession(deals=deals, current_index=0)
            
            # Send first deal
            await self._send_deal(update, context)
            
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            await update.message.reply_text(
                "Sorry, I encountered an error while processing your request. Please try again."
            )

    async def button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle button clicks."""
        query = update.callback_query
        chat_id = update.effective_chat.id
        session = self.user_sessions.get(chat_id)
        
        if not session:
            await query.answer("Session expired. Please start a new search.")
            return
            
        if query.data == "prev":
            session.prev_deal()
        elif query.data == "next":
            session.next_deal()
            
        await query.answer()
        await self._send_deal(update, context, edit=True)

    async def _send_deal(self, update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False) -> None:
        """Send deal information to user."""
        chat_id = update.effective_chat.id
        session = self.user_sessions.get(chat_id)
        
        if not session or not session.has_deals():
            await update.message.reply_text(
                "No deals found. Try a new search query."
            )
            return
            
        deal = session.current_deal()
        logger.info("\n🔄 Formatting deal for Telegram:")
        logger.info(json.dumps(deal, indent=2))
        
        # Format traffic sources
        traffic_sources = deal.get('traffic_source', [])
        traffic_str = '|'.join(traffic_sources) if traffic_sources else 'N/A'
        
        # Format partner and GEO
        partner = deal.get('partner', 'Unknown')
        geo = deal.get('geo', 'N/A')
        
        # Format pricing
        pricing = deal.get('pricing_model', 'N/A')
        
        # Format funnels
        funnels = deal.get('funnels', [])
        funnel_str = f"\nFunnels: {', '.join(funnels)}" if funnels else ""
        
        message = (
            f"📋 Deal {session.current_index + 1} of {session.total_deals()}\n\n"
            f"{partner} -> {geo} [{traffic_str}] {pricing}"
            f"{funnel_str}"
        )
        
        logger.info("\n📤 Sending to Telegram:")
        logger.info(message)
        
        # Create navigation buttons
        keyboard = []
        if session.has_prev():
            keyboard.append(InlineKeyboardButton("⬅️ Previous", callback_data="prev"))
        if session.has_next():
            keyboard.append(InlineKeyboardButton("Next ➡️", callback_data="next"))
            
        reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None
        
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(
                text=message,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text=message,
                reply_markup=reply_markup
            )

if __name__ == '__main__':
    try:
        bot = DealSearchBot()
        print("🤖 Deal Search Bot is running...")
        bot.run()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
