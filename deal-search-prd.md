# Deal Search Bot - Product Requirements Document

## Project Overview
A Telegram bot that allows users to search and retrieve deals from Notion based on GEO codes and partner names. The bot will use AI for natural language understanding and provide an interactive selection interface for choosing specific deals.

## Core Components

### 1. File Structure
```
deal_search_bot/
├── main.py                 # Bot initialization and entry point
├── handlers/
│   ├── __init__.py
│   ├── message_handler.py  # Main message handling logic
│   ├── callback_handler.py # Callback query handling
│   └── error_handler.py    # Error handling and logging
├── services/
│   ├── __init__.py
│   ├── notion_service.py   # Notion API integration
│   └── ai_service.py       # AI/LLM integration
├── models/
│   ├── __init__.py
│   ├── deal.py            # Deal data model
│   └── user_session.py    # User session management
├── utils/
│   ├── __init__.py
│   ├── formatters.py      # Deal formatting utilities
│   └── validators.py      # Input validation
└── config.py              # Configuration and environment variables
```

### 2. Core Classes

#### MessageHandler
- Primary handler for incoming messages
- Uses AI service to parse natural language inputs
- Manages the search flow and user interactions

#### NotionService
- Handles all Notion API interactions
- Methods for searching, filtering, and retrieving deals
- Caches results to minimize API calls

#### AIService
- Integrates with Mistral AI
- Handles natural language parsing
- Extracts GEO codes and partner names from unstructured text

#### UserSession
- Manages user state and selected deals
- Handles pagination state
- Caches search results

#### DealFormatter
- Formats deals for display
- Handles different output formats (preview, detailed, export)

## User Interface Design

### 1. Search Flow
1. User sends message with search criteria
   - Can be natural language: "Show me all deals for UK and France"
   - Can be direct: "UK FR"
   - Can include partner names: "UK Tokomedia"

2. Bot responds with processing message:
```
🔍 Analyzing your request...
```

3. Initial results message:
```
Found 15 deals matching your criteria:
Use the buttons below to select deals you're interested in.
Page 1 of 3
```

### 2. Deal Selection Interface

#### Inline Keyboard Layout
```
⚪️ Deum -> MX Spanish [Facebook] 15 CPL [Button]
✅ FTD -> UK Native [Facebook|Google] 1200+10% [Button]
⚪️ Rayzone -> FR French [Native Ads] 1000+9% [Button]
           ...
Network Pricing ⚡️    Brand Pricing 🏢
⬅️ Previous    ➡️ Next
✅ Get Selected    ❌ Cancel
```

Key Features:
- Each deal formatted as: [Partner] -> [GEO] [Language] [[Source]] [Price]
- Funnels shown below each deal button
- Pricing type selector (Network/Brand) affects final output
- Selection status indicator (⚪️/✅)
- Pagination controls
- Maximum 4 deals per page for readability due to funnel lists

### 3. Selected Deals View
After clicking "Get Selected":
```
📋 Selected Deals (3) - Network Pricing:

1. FTD -> UK Native [Facebook|Google] 1250+12%
   Funnels: Quantum AI, ByteToken360
   
2. Deum -> MX Spanish [Facebook] 17 CPL
   Funnels: Oil Profit, Riquezal
   
3. Rayzone -> FR French [Native Ads] 1050+9%
   Funnels: ByteToken360, CryptoAI

Options:
📋 Copy All
🔄 Change to Brand Pricing
⬅️ Back to Selection

## Technical Specifications

### 1. AI Integration

AIService Configuration:
- Model: Mistral
- Temperature: 0.2 (for highly consistent parsing)
- Two-stage approach:
  1. Initial data loading:
     - Load all unique partner names from Notion
     - Load all valid GEO codes from existing deals
     - Create efficient lookup structures
  2. Query parsing:
     - Match against known partner names first
     - Match against known GEO codes
     - Handle variations and misspellings

Example Processing:
```python
# Stage 1: Load reference data
reference_data = {
    "partners": {
        "primary": ["Deum", "FTD", "Rayzone"],
        "aliases": {"TokoMedia": "Toko Media Ltd"} # Handle variations
    },
    "geo_codes": {
        "primary": ["UK", "DE", "FR", "MX"],
        "groups": {"LATAM": ["MX", "BR", "CO"]}
    }
}

# Stage 2: Parse input
Input: "hey can you show me deals for UK and Germany from TokoMedia?"
Intermediate: {
    "potential_geos": ["UK", "Germany"],
    "potential_partners": ["TokoMedia"],
    "original_text": "hey can you show me deals for UK and Germany from TokoMedia?"
}
Output: {
    "geo_codes": ["UK", "DE"],  # Germany normalized to DE
    "partner": "Toko Media Ltd",  # Aliased to primary name
    "constraints": None
}
```

Key Features:
- Pre-loaded lookups for faster processing
- Fuzzy matching for partner names
- GEO code normalization
- Group expansion (e.g., "LATAM" -> specific countries)
- Confidence scoring for matches

### 2. Notion Integration

Query Structure:
```python
filter = {
    "and": [
        {
            "or": [
                {"property": "GEO-Funnel Code", "title": {"contains": "UK"}},
                {"property": "GEO-Funnel Code", "title": {"contains": "DE"}}
            ]
        },
        {
            "property": "⚡ ALL ADVERTISERS | Kitchen",
            "relation": {"contains": "TokoMedia"}
        }
    ]
}
```

### 3. Callback Handling

#### Callback Data Structure
```python
class CallbackActions:
    # Deal Selection
    SELECT_DEAL = "select_{deal_id}"
    
    # Navigation
    NEXT_PAGE = "next_{current_page}"
    PREV_PAGE = "prev_{current_page}"
    
    # Pricing Type
    SET_NETWORK_PRICING = "price_network"
    SET_BRAND_PRICING = "price_brand"
    TOGGLE_PRICING = "price_toggle"  # For selected deals view
    
    # Final Actions
    GET_SELECTED = "get_selected"
    COPY_ALL = "copy_all"
    BACK_TO_SELECT = "back_select"
    CANCEL = "cancel"

class CallbackStates:
    SELECTING = "selecting"  # Initial deal selection
    REVIEWING = "reviewing"  # Viewing selected deals
    PRICING = "pricing"      # Choosing pricing type
```

#### State Management
```python
user_session = {
    # Navigation State
    "current_page": int,
    "total_pages": int,
    "last_message_id": int,
    
    # Selection State
    "selected_deals": Set[str],
    "pricing_type": Literal["network", "brand"],
    "current_state": CallbackStates,
    
    # Cache References
    "search_results": List[Deal],
    "reference_data_version": str,  # For cache validation
    
    # Format Preferences
    "output_format": Literal["preview", "full", "copied"]
}
```

### 4. Caching Strategy

#### Global Cache
```python
global_cache = {
    # Reference Data Cache (1 hour TTL)
    "reference_data": {
        "version": str,  # Incremented on updates
        "partners": Dict[str, str],  # name -> canonical name
        "geo_codes": Dict[str, List[str]],  # code/group -> codes
        "last_updated": datetime,
    },
    
    # Deal Cache (15 minutes TTL)
    "deals": {
        "by_partner": Dict[str, List[Deal]],
        "by_geo": Dict[str, List[Deal]],
        "last_updated": datetime
    },
    
    # Search Results Cache (5 minutes TTL)
    "search_results": {
        "query_hash": {
            "results": List[Deal],
            "timestamp": datetime
        }
    }
}
```

#### Cache Invalidation Rules:
1. Reference Data:
   - Invalidate hourly
   - Force refresh on Notion webhook (if implemented)
   - Keep previous version for in-progress sessions

2. Deal Cache:
   - 15-minute TTL for deal data
   - Segment by partner and GEO for partial updates
   - Invalidate specific segments on updates

3. Search Results:
   - 5-minute TTL
   - Hash query parameters for cache key
   - Include reference_data_version in cache key

### 5. Deal Formatting

#### Format Types:
```python
class DealFormat:
    # Selection View Format
    PREVIEW = "{partner} -> {geo} {language} [{sources}] {buying_price}"
    
    # Full Deal Format (Network)
    NETWORK = (
        "{partner} -> {geo} {language} [{sources}] "
        "{network_cpa}+{network_crg}% // {network_cpl}"
    )
    
    # Full Deal Format (Brand)
    BRAND = (
        "{partner} -> {geo} {language} [{sources}] "
        "{brand_cpa}+{brand_crg}% // {brand_cpl}"
    )
    
    # Funnel Format
    FUNNELS = "Funnels: {funnel_list}"
```

#### Price Calculations:
```python
def calculate_network_price(deal: Deal) -> Dict[str, float]:
    return {
        "cpa": deal.buying_cpa + 50 if deal.buying_cpa else None,
        "crg": deal.buying_crg + 0.01 if deal.buying_crg > 0.1 else deal.buying_crg,
        "cpl": deal.buying_cpl + 5 if deal.buying_cpl else None
    }

def calculate_brand_price(deal: Deal) -> Dict[str, float]:
    return {
        "cpa": deal.buying_cpa + 100 if deal.buying_cpa else None,
        "crg": deal.buying_crg,  # Same as buying for brand
        "cpl": deal.buying_cpl + 7 if deal.buying_cpl else None
    }
```

#### Format Helpers:
```python
class DealFormatter:
    @staticmethod
    def format_sources(sources: List[str]) -> str:
        return "|".join(sources)
    
    @staticmethod
    def format_funnels(funnels: List[str]) -> str:
        return ", ".join(funnels)
    
    @staticmethod
    def format_price(deal: Deal, pricing_type: str) -> str:
        if pricing_type == "network":
            prices = calculate_network_price(deal)
        else:
            prices = calculate_brand_price(deal)
            
        if deal.model_type == "CPL":
            return f"{prices['cpl']} CPL"
        else:
            return f"{prices['cpa']}+{prices['crg']}%"
```

## Performance Requirements

1. Response Times:
   - Initial search: < 3 seconds
   - Deal selection: < 500ms
   - Page navigation: < 1 second
   - Deal formatting: < 2 seconds

2. Concurrency:
   - Support multiple users simultaneously
   - Maintain separate session states
   - Handle concurrent Notion queries

3. Error Handling:
   - Graceful degradation on API failures
   - Clear error messages to users
   - Automatic retry for transient failures

## Phase 1 Implementation Priorities

1. Basic search functionality
   - GEO code parsing
   - Simple Notion queries
   - Basic deal display

2. Selection interface
   - Deal selection buttons
   - Pagination controls
   - Basic action buttons

3. Core features
   - Deal preview format
   - Selection management
   - Basic error handling

Future phases can add:
- Advanced natural language processing
- Additional export formats
- Analytics and tracking
- User preferences
- Custom formatting templates
