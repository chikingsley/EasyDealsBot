from notion_client import Client
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class NotionService:
    def __init__(self, notion_token: str, database_id: str):
        self.client = Client(auth=notion_token)
        self.database_id = database_id

    async def search_deals(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for deals in Notion database based on parameters."""
        try:
            filter_conditions = []
            
            # Add geo filter
            if 'geo' in search_params and search_params['geo']:
                filter_conditions.append({
                    "property": "GEO-Funnel Code",
                    "title": {
                        "contains": search_params['geo'][0].upper()  # Using first geo for now
                    }
                })

            # Add traffic source filter
            if 'traffic_source' in search_params and search_params['traffic_source']:
                filter_conditions.append({
                    "property": "Sources",
                    "multi_select": {
                        "contains": search_params['traffic_source'][0]  # Using first source
                    }
                })

            # Add pricing model filter
            if 'pricing_model' in search_params and search_params['pricing_model']:
                filter_conditions.append({
                    "property": "Pricing Model",
                    "select": {
                        "equals": search_params['pricing_model'].upper()
                    }
                })

            # Add partner filter
            if 'partner' in search_params and search_params['partner']:
                filter_conditions.append({
                    "property": "⚡ ALL ADVERTISERS | Kitchen",
                    "relation": {
                        "contains": search_params['partner']
                    }
                })

            # Construct the final filter
            query = {
                "database_id": self.database_id,
                "filter": {
                    "and": filter_conditions
                } if filter_conditions else {}
            }

            # Query the database
            response = self.client.databases.query(**query)

            # Process and return results
            deals = []
            for page in response['results']:
                properties = page['properties']
                deal = {
                    'partner': self._get_title_value(properties.get('⚡ ALL ADVERTISERS | Kitchen', {})),
                    'geo': self._get_title_value(properties.get('GEO-Funnel Code', {})),
                    'traffic_source': self._get_multi_select_values(properties.get('Sources', {})),
                    'pricing_model': self._get_select_value(properties.get('Pricing Model', {})),
                    'description': self._get_rich_text_value(properties.get('Description', {}))
                }
                deals.append(deal)

            return deals

        except Exception as e:
            logger.error(f"Error searching deals: {str(e)}")
            return []

    def _get_rich_text_value(self, property_obj: Dict) -> str:
        """Extract value from rich text property."""
        try:
            rich_text = property_obj.get('rich_text', [])
            return rich_text[0]['plain_text'] if rich_text else ''
        except (KeyError, IndexError):
            return ''

    def _get_multi_select_values(self, property_obj: Dict) -> List[str]:
        """Extract values from multi_select property."""
        try:
            multi_select = property_obj.get('multi_select', [])
            return [option['name'] for option in multi_select]
        except (KeyError, TypeError):
            return []

    def _get_select_value(self, property_obj: Dict) -> str:
        """Extract value from select property."""
        try:
            select = property_obj.get('select', {})
            return select.get('name', '') if select else ''
        except (KeyError, TypeError):
            return ''

    def _get_title_value(self, property_obj: Dict) -> str:
        """Extract value from title property."""
        try:
            title = property_obj.get('title', [])
            return title[0]['plain_text'] if title else ''
        except (KeyError, IndexError):
            return ''

    async def search_advertisers(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for advertisers based on provided parameters"""
        try:
            filter_conditions = []

            # Advertiser filter
            if advertiser := search_params.get('advertiser'):
                filter_conditions.append({
                    "property": "Advertiser",
                    "title": {
                        "contains": advertiser
                    }
                })

            # Build final filter
            filter_obj = {"and": filter_conditions} if filter_conditions else {}

            # Query the database
            response = self.client.databases.query(
                database_id=self.database_id,
                filter=filter_obj
            )

            # Process and return results
            advertisers = []
            for page in response['results']:
                props = page['properties']
                advertiser = {
                    'name': props.get('Advertiser', {}).get('title', [{}])[0].get('text', {}).get('content', 'N/A'),
                    'description': props.get('Description', {}).get('rich_text', [{}])[0].get('text', {}).get('content', 'N/A')
                }
                advertisers.append(advertiser)

            return advertisers

        except Exception as e:
            logger.error(f"Error searching advertisers: {str(e)}")
            return []
