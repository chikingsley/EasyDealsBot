# EasyDealsBot

A Telegram bot that helps search and manage deals using Notion as a backend database. The bot provides natural language search capabilities for deals and offers, with support for filtering by GEO, traffic sources, partners, and more.

## Features

- 🔍 Natural language search for deals
- 🌍 Filter by GEO locations and languages
- 🚦 Traffic source filtering
- 🤝 Partner/advertiser filtering
- 💰 Multiple pricing models (Network/Brand)
- 🔄 Interactive deal selection interface
- 🏷️ Support for multiple funnels/verticals

## Prerequisites

- Python 3.12+
- Docker and Docker Compose (for containerized deployment)
- Telegram Bot Token
- Notion API Token
- Mistral AI API Key
- Notion databases set up for offers and advertisers

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
NOTION_TOKEN=your_notion_api_token
OFFERS_DATABASE_ID=your_notion_offers_database_id
ADVERTISERS_DATABASE_ID=your_notion_advertisers_database_id
MISTRAL_API_KEY=your_mistral_api_key
```

## Installation

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/EasyDealsBot.git
   cd EasyDealsBot
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the bot:
   ```bash
   python main.py
   ```

### Docker Deployment

1. Build and run using Docker Compose:
   ```bash
   docker-compose up -d
   ```

2. Check logs:
   ```bash
   docker-compose logs -f
   ```

## Project Structure

```
EasyDealsBot/
├── bot/
│   └── search_bot.py      # Main bot implementation
├── models/
│   ├── reference_data.py  # Reference data models
│   └── user_session.py    # User session management
├── services/
│   ├── ai_service.py      # AI service integration
│   └── notion_service.py  # Notion API integration
├── .env                   # Environment variables
├── .gitignore            # Git ignore rules
├── docker-compose.yml    # Docker compose configuration
├── Dockerfile           # Docker build instructions
├── main.py             # Application entry point
└── requirements.txt    # Python dependencies
```

## Usage

1. Start a chat with the bot on Telegram
2. Use natural language to search for deals:
   - "Show me deals from India"
   - "Find offers with CPA pricing model"
   - "Search for deals from partner XYZ"
3. Use the interactive interface to:
   - Select/deselect deals
   - Switch between pricing models
   - View selected deals
   - Navigate through pages of results

## Development

- Follow PEP 8 style guide
- Use type hints for better code clarity
- Add docstrings to functions and classes
- Update requirements.txt when adding new dependencies

## Security Notes

- All sensitive information should be stored in environment variables
- The bot runs as a non-root user in Docker for security
- API tokens should never be committed to the repository

## Maintenance

- Monitor the bot's health using Docker's health check
- Check logs regularly for any issues
- Keep dependencies updated
- Backup your Notion databases regularly

## License

This project is proprietary and confidential. Unauthorized copying, modification, distribution, or use of this software is strictly prohibited.
