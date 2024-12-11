import os
import logging
import json
import re
from typing import Dict, Any, List, Set
from mistralai import Mistral
from models.reference_data import ReferenceData

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, reference_data: ReferenceData = None):
        self._validate_api_key()
        self.client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
        self.model = "mistral-large-latest"
        self.reference_data = reference_data

    def _validate_api_key(self):
        if not os.getenv("MISTRAL_API_KEY"):
            raise ValueError("MISTRAL_API_KEY environment variable not set")

    def _extract_geo_codes(self, text: str) -> List[str]:
        """Extract GEO codes using pattern matching"""
        # Find all 2-3 letter uppercase codes
        candidates = re.findall(r'\b[A-Z]{2,3}\b', text.upper())
        # Only keep ones that exist in our reference data
        return [geo for geo in candidates if geo in self.reference_data.geo_codes] if self.reference_data else []

    def _extract_traffic_sources(self, text: str) -> List[str]:
        """Extract traffic sources using pattern matching"""
        if not self.reference_data:
            return []
        
        # Look for exact matches of known traffic sources
        found_sources = []
        text_lower = text.lower()
        for source in self.reference_data.traffic_sources:
            if source.lower() in text_lower:
                found_sources.append(source)
        return found_sources

    def _extract_partner_names(self, text: str) -> List[str]:
        """Extract partner names using pattern matching"""
        if not self.reference_data:
            return []
        
        # Look for exact matches of known partner names
        found_partners = []
        text_lower = text.lower()
        for partner in self.reference_data.partner_names:
            if partner.lower() in text_lower:
                found_partners.append(partner)
        return found_partners

    async def parse_search_query(self, query: str) -> Dict[str, Any]:
        """Parse natural language search query into structured parameters"""
        try:
            logger.info(" Query: " + query)
            
            # Try pattern matching first
            result = {}
            
            # Extract GEO codes
            geo_codes = self._extract_geo_codes(query)
            if geo_codes:
                result['geo'] = geo_codes
            
            # Extract traffic sources
            traffic_sources = self._extract_traffic_sources(query)
            if traffic_sources:
                result['traffic_source'] = traffic_sources
            
            # Extract partner names
            partners = self._extract_partner_names(query)
            if partners:
                result['partner'] = partners[0]  # Use first match
            
            # Extract pricing model using simple pattern
            if re.search(r'\bcpa\b', query.lower()):
                result['pricing_model'] = 'CPA'
            elif re.search(r'\bcpl\b', query.lower()):
                result['pricing_model'] = 'CPL'
            elif re.search(r'\bcrg\b', query.lower()):
                result['pricing_model'] = 'CRG'
            
            # If we found everything through pattern matching, return it
            if result.get('geo') or result.get('traffic_source') or result.get('partner') or result.get('pricing_model'):
                logger.info(" Pattern matching result: " + json.dumps(result))
                return result
            
            # If pattern matching didn't find anything, use Mistral
            logger.info(" Using Mistral for natural language understanding")
            
            system_message = (
                "You are a deal search assistant. Extract search parameters from the user's query.\n"
                "Return a JSON object with these fields:\n"
                "- geo: list of GEO codes (e.g., ['UK', 'US', 'IN', 'FI']). Always use standard 2-letter country codes in uppercase.\n"
                "  Valid GEO codes: " + ", ".join(sorted(self.reference_data.geo_codes)) + "\n"
                "- traffic_source: list of traffic sources. Valid sources: " + ", ".join(sorted(self.reference_data.traffic_sources)) + "\n"
                "- pricing_model: pricing model (CPA, CPL, CRG)\n"
                "- partner: partner name if specified. Valid partners: " + ", ".join(sorted(self.reference_data.partner_names)) + "\n"
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
                ai_result = json.loads(content)
                # Merge AI results with pattern matching results, preferring pattern matching
                for key, value in ai_result.items():
                    if key not in result:
                        result[key] = value
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Mistral response: {str(e)}")
                return result

        except Exception as e:
            logger.error(f"Error in AI service: {str(e)}")
            return {}
