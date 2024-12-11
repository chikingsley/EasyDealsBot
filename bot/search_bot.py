import os
import logging
import json
from typing import Dict, Any, List
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
        self.notion_service = NotionService(
            notion_token=os.getenv("NOTION_TOKEN"),
            database_id=database_id if database_id else os.getenv("NOTION_DATABASE_ID")
        )
        self.ai_service = AIService(reference_data=self.notion_service.reference_data)
        
        # Create application
        self.app = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
        
        # Add handlers
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(CallbackQueryHandler(self._handle_callback))
        
        # Set debug mode
        self.debug = debug
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        
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
        """Handle incoming messages."""
        query = update.message.text

        try:
            # Parse the query and get deals
            deals = await self._get_deals(query)
            if not deals:
                await update.message.reply_text("No deals found matching your criteria.")
                return

            # Create new session
            context.user_data['session'] = UserSession(deals)
            
            # Display the first page
            await self._display_deals_page(update.message, context.user_data['session'])
            
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            if self.debug:
                error_msg += f"\n{traceback.format_exc()}"
            await update.message.reply_text(error_msg)

    async def _get_deals(self, query: str) -> List[Dict[str, Any]]:
        """Parse query and get deals from Notion."""
        # Parse search query
        search_params = await self.ai_service.parse_search_query(query)
        
        # Search for deals
        deals = await self.notion_service.search_deals(search_params)
        
        return deals

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline keyboard."""
        query = update.callback_query
        await query.answer()
        
        if 'session' not in context.user_data:
            await query.edit_message_text("Session expired. Please start a new search.")
            return
            
        session = context.user_data['session']
        header_text = f"📄 Page {session.get_current_page()} | {session.pricing_mode.title()} Pricing"
        
        if query.data.startswith("select_"):
            idx = int(query.data.split("_")[1])
            if idx in session.selected_deals:
                session.selected_deals.remove(idx)
            else:
                session.selected_deals.add(idx)
                # Show full deal info in message text
                deal = session.deals[idx]
                header_text = f"Selected Deal:\n{session.format_deal_for_display(deal)}\n\n{header_text}"
        
        elif query.data == "prev":
            session.prev_page()
        
        elif query.data == "next":
            session.next_page()
        
        elif query.data.startswith("price_"):
            mode = query.data.split("_")[1]
            session.pricing_mode = mode
            # If a deal is selected, update its display with new pricing
            if session.selected_deals:
                selected_idx = max(session.selected_deals)  # Show the last selected deal
                deal = session.deals[selected_idx]
                header_text = f"Selected Deal:\n{session.format_deal_for_display(deal)}\n\n{header_text}"
            else:
                header_text = f"Switched to {mode.title()} pricing\n{header_text}"
        
        elif query.data == "view":
            # Format selected deals for copying
            if session.selected_deals:
                deals_text = "\n\n".join(
                    session.format_deal_for_display(session.deals[idx], include_partner=False)
                    for idx in sorted(session.selected_deals)
                )
                await query.message.reply_text(deals_text)
                header_text = f"Deals displayed above\n{header_text}"
            else:
                header_text = f"No deals selected\n{header_text}"
        
        elif query.data == "exit":
            await query.message.edit_text("Search completed. Start a new search with /search")
            del context.user_data['session']
            return
        
        # Update the message with new keyboard
        keyboard = self._create_keyboard(session)
        await query.message.edit_text(
            text=header_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    def _format_deal_button(self, deal: Dict[str, Any], absolute_idx: int, is_selected: bool) -> str:
        """Format a deal for display in a button."""
        emoji = "✅" if is_selected else "⭕️"
        
        # Basic info: GEO-Partner-Source
        partner = deal.get('partner', 'N/A')
        geo = deal.get('geo', 'N/A')
        traffic_sources = deal.get('traffic_sources', [])
        traffic_str = ' | '.join(traffic_sources) if isinstance(traffic_sources, list) else traffic_sources
        
        button_text = f"{emoji} {geo}-{partner}-{traffic_str}"
        
        # Truncate if too long
        if len(button_text) > 50:
            button_text = button_text[:47] + "..."
            
        return button_text

    def _create_keyboard(self, session: UserSession) -> List[List[InlineKeyboardButton]]:
        """Create an inline keyboard for deal selection."""
        keyboard = []
        
        # Add deals for current page
        start_idx = session.current_index
        end_idx = min(start_idx + session.deals_per_page, len(session.deals))
        
        for i in range(start_idx, end_idx):
            deal = session.deals[i]
            button_text = self._format_deal_button(deal, i, i in session.selected_deals)
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"select_{i}")])
        
        # Navigation row
        nav_row = []
        if session.has_prev():
            nav_row.append(InlineKeyboardButton("⬅️ Previous", callback_data="prev"))
        if session.has_next():
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data="next"))
        if nav_row:
            keyboard.append(nav_row)
        
        # Control buttons row
        control_row = [
            InlineKeyboardButton("💰 Network", callback_data="price_network"),
            InlineKeyboardButton("💎 Brand", callback_data="price_brand"),
        ]
        keyboard.append(control_row)
        
        # Action buttons row
        action_row = [
            InlineKeyboardButton("📋 View Deals", callback_data="view"),
            InlineKeyboardButton("❌ Exit", callback_data="exit")
        ]
        keyboard.append(action_row)
        
        return keyboard

    async def _display_deals_page(self, message, session: UserSession, edit: bool = False) -> None:
        """Display current page of deals with selection UI."""
        if not session.has_deals():
            await message.reply_text("No deals to display.")
            return

        # Create minimal header
        selected_count = len(session.selected_deals)
        header = f"📄 Page {session.get_current_page()}/{session.total_pages()}"
        if selected_count > 0:
            header += f" | ✅ {selected_count} deals selected"
        
        # Create and send/edit message with inline keyboard
        keyboard = self._create_keyboard(session)
        if edit:
            await message.edit_text(header, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await message.reply_text(header, reply_markup=InlineKeyboardMarkup(keyboard))

if __name__ == '__main__':
    try:
        bot = DealSearchBot()
        print("🤖 Deal Search Bot is running...")
        bot.run()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
