from notion_client import Client
import logging
import json
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
            
            logger.info(" Notion query: " + json.dumps(query, indent=2))

            # Query the database
            response = self.client.databases.query(**query)
            logger.info(f"Notion response: Found {len(response['results'])} deals")
            logger.info("First deal properties: " + json.dumps(response['results'][0]['properties'] if response['results'] else {}, indent=2))

            # Process and return results
            deals = []
            for page in response['results']:
                properties = page['properties']
                
                # Get partner info
                partner = self._get_title_value(properties.get('⚡ ALL ADVERTISERS | Kitchen', {}))
                
                # Get GEO and language
                geo_code = self._get_title_value(properties.get('GEO-Funnel Code', {}))
                language = self._get_select_value(properties.get('Language', {}))
                geo = f"{geo_code} {language}" if language else geo_code
                
                # Get traffic sources
                traffic_sources = self._get_multi_select_values(properties.get('Sources', {}))
                
                # Get pricing
                pricing_model = self._get_select_value(properties.get('Pricing Model', {}))
                price_value = self._get_number_value(properties.get('Price', {}))
                price_percent = self._get_number_value(properties.get('Price Percent', {}))
                
                # Format pricing based on model
                if pricing_model == 'CPA':
                    price = f"{price_value}+{price_percent}%" if price_percent else str(price_value)
                elif pricing_model == 'CPL':
                    price = f"{price_value} CPL"
                else:
                    price = f"{price_value} {pricing_model}" if price_value else pricing_model
                
                # Get funnels
                funnels = self._get_relation_titles(properties.get('Funnels', {}))
                
                deal = {
                    'partner': partner,
                    'geo': geo,
                    'traffic_source': traffic_sources,
                    'pricing_model': price,
                    'funnels': funnels
                }
                deals.append(deal)

            return deals

        except Exception as e:
            logger.error(f"Error searching deals: {str(e)}")
            return []

    async def search_advertisers(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for advertisers based on provided parameters"""
        try:
            logger.info(f"Searching advertisers with params: {json.dumps(search_params, indent=2)}")
            filter_conditions = []

            # Advertiser filter
            if advertiser := search_params.get('advertiser'):
                advertiser_filter = {
                    "property": "Advertiser",
                    "title": {
                        "contains": advertiser
                    }
                }
                filter_conditions.append(advertiser_filter)
                logger.info(f"Added advertiser filter: {json.dumps(advertiser_filter, indent=2)}")

            # Language filter
            if language := search_params.get('language'):
                language_filter = {
                    "property": "Language",
                    "select": {
                        "equals": language
                    }
                }
                filter_conditions.append(language_filter)
                logger.info(f"Added language filter: {json.dumps(language_filter, indent=2)}")

            # Build final filter
            filter_obj = {"and": filter_conditions} if filter_conditions else {}

            logger.info(f"Final Notion query: {json.dumps(filter_obj, indent=2)}")

            # Query the database
            response = self.client.databases.query(
                database_id=self.database_id,
                filter=filter_obj
            )
            logger.info(f"Found {len(response['results'])} advertisers")

            # Process and return results
            advertisers = []
            for page in response['results']:
                props = page['properties']
                logger.debug(f"Processing advertiser properties: {json.dumps(props, indent=2)}")
                advertiser = {
                    'name': props.get('Advertiser', {}).get('title', [{}])[0].get('text', {}).get('content', 'N/A'),
                    'description': props.get('Description', {}).get('rich_text', [{}])[0].get('text', {}).get('content', 'N/A'),
                    'language': self._get_select_value(props.get('Language', {}))
                }
                logger.debug(f"Processed advertiser: {json.dumps(advertiser, indent=2)}")
                advertisers.append(advertiser)

            logger.info(f"Returning {len(advertisers)} processed advertisers")
            return advertisers

        except Exception as e:
            logger.error(f"Error searching advertisers: {str(e)}", exc_info=True)
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

    def _get_number_value(self, property_obj: Dict) -> float:
        """Extract value from number property."""
        try:
            return property_obj.get('number', 0)
        except (KeyError, TypeError):
            return 0

    def _get_relation_titles(self, property_obj: Dict) -> List[str]:
        """Extract titles from relation property."""
        try:
            relations = property_obj.get('relation', [])
            titles = []
            for relation in relations:
                page_id = relation.get('id')
                if page_id:
                    page = self.client.pages.retrieve(page_id)
                    title = page['properties'].get('Name', {}).get('title', [])
                    if title:
                        titles.append(title[0]['plain_text'])
            return titles
        except Exception as e:
            logger.error(f"Error getting relation titles: {str(e)}")
            return []
