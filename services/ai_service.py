import os
import logging
import json
from typing import Dict, Any
from mistralai import Mistral

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, message=None):
        self._validate_api_key()
        self.client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
        self.model = "mistral-large-latest"

    def _validate_api_key(self):
        if not os.getenv("MISTRAL_API_KEY"):
            raise ValueError("MISTRAL_API_KEY environment variable not set")

    async def parse_search_query(self, query: str) -> Dict[str, Any]:
        """Parse natural language search query into structured parameters"""
        try:
            logger.info(" Query to Mistral: " + query)
            
            system_message = (
                "You are a deal search assistant. Extract search parameters from the user's query.\n"
                "Return a JSON object with these fields:\n"
                "- geo: list of GEO codes (e.g., ['UK', 'US'])\n"
                "- traffic_source: list of traffic sources (e.g., ['Facebook', 'Google'])\n"
                "- pricing_model: pricing model (e.g., 'CPA', 'CPL')\n"
                "- partner: partner name if specified\n"
                "If a field is not mentioned in the query, omit it from the JSON."
            )

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": query}
            ]
            
            response = await self.client.chat.complete_async(
                model=self.model,
                messages=messages,
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            logger.info(" Mistral response: " + content)

            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Mistral response: {str(e)}")
                return {}

        except Exception as e:
            logger.error(f"Error in AI service: {str(e)}")
            return {}
