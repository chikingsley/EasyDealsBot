import os
import logging
import mistralai
from mistralai import Mistral
from typing import Dict, Any
import json

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, message=None):
        self._validate_api_key()
        self.client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
        self.message = message
        self.progress = None  # Will hold ProgressHandler instance
        self.max_retries = 3
        self.base_delay = 1.0
        self.model = "mistral-large-latest"

    def _validate_api_key(self):
        """Validate API key exists"""
        try:
            if not os.getenv("MISTRAL_API_KEY"):
                logger.error("MISTRAL_API_KEY environment variable not set")
                raise ValueError(
                    "MISTRAL_API_KEY environment variable not set. "
                    "Please set it in your .env file."
                )
        except Exception as e:
            logger.error(f"API key validation error: {str(e)}")
            raise

    async def parse_search_query(self, query: str) -> Dict[str, Any]:
        """Parse natural language search query into structured parameters"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a deal search assistant. Convert the user's natural language query into structured search parameters. "
                        "Return only a Python dictionary with these possible keys: 'geo' (list), 'traffic_source' (list), "
                        "'pricing_model' (str), 'partner' (str). Include only keys that are relevant to the query."
                    )
                },
                {"role": "user", "content": query}
            ]

            response = await self.client.chat.complete_async(
                model=self.model,
                messages=messages,
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            # Extract the response content and evaluate it as a Python dict
            response_text = response.choices[0].message.content
            # Clean up the response to ensure it's a valid Python dict
            response_text = response_text.strip().replace("```python", "").replace("```", "").strip()
            
            # Safely evaluate the string as a Python dict
            search_params = eval(response_text)
            
            # Validate the search parameters
            valid_keys = {'geo', 'traffic_source', 'pricing_model', 'partner'}
            search_params = {k: v for k, v in search_params.items() if k in valid_keys}
            
            # Convert single values to lists for consistency
            if 'geo' in search_params and not isinstance(search_params['geo'], list):
                search_params['geo'] = [search_params['geo']]
            if 'traffic_source' in search_params and not isinstance(search_params['traffic_source'], list):
                search_params['traffic_source'] = [search_params['traffic_source']]
            
            return search_params

        except Exception as e:
            logger.error(f"Error parsing search query: {str(e)}")
            # Return empty dict on error to allow graceful fallback
            return {}
