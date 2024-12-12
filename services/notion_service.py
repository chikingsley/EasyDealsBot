from notion_client import Client
import logging
import json
import os
from typing import Dict, List, Any, Optional
from models.reference_data import ReferenceData

logger = logging.getLogger(__name__)

class NotionService:
    def __init__(self, notion_token: str = None, database_id: str = None):
        self.client = Client(auth=notion_token)
        self.database_id = database_id
        self.advertisers_database_id = os.getenv("ADVERTISERS_DATABASE_ID")
        self._load_reference_data()

    def _load_reference_data(self):
        """Load reference data from both Notion databases"""
        try:
            # Load partner data from advertisers database
            advertisers_response = self.client.databases.query(
                database_id=self.advertisers_database_id
            )

            # Query offers database
            offers_response = self.client.databases.query(
                database_id=self.database_id
            )

            # Initialize reference data
            partner_names = set()
            partner_id_to_name = {}
            geo_codes = set()
            traffic_sources = set()
            funnels = set()

            # Process advertisers data
            for page in advertisers_response['results']:
                try:
                    partner_name = page['properties']['Name']['title'][0]['plain_text']
                    partner_id = page['id']
                    partner_names.add(partner_name)
                    partner_id_to_name[partner_id] = partner_name
                except (KeyError, IndexError) as e:
                    logger.warning(f"Error processing advertiser: {str(e)}")

            # Process offers data for GEO codes
            for page in offers_response['results']:
                try:
                    properties = page.get('properties', {})
                    if 'GEO-Funnel Code' in properties:
                        geo_funnel_prop = properties['GEO-Funnel Code']
                        if geo_funnel_prop.get('title') and len(geo_funnel_prop['title']) > 0:
                            geo_funnel_code = geo_funnel_prop['title'][0].get('plain_text', '')
                            # Split by hyphen and take first part, then split by space and take first part
                            if '-' in geo_funnel_code:
                                geo = geo_funnel_code.split('-')[0].strip()
                                if ' ' in geo:
                                    geo = geo.split(' ')[0].strip()
                                if geo:
                                    geo_codes.add(geo)

                    # Extract traffic sources
                    if 'Sources' in properties:
                        sources_prop = properties['Sources']
                        if sources_prop.get('multi_select'):
                            for source in sources_prop['multi_select']:
                                if source.get('name'):
                                    traffic_sources.add(source['name'])

                    # Extract funnels
                    if 'Funnels' in properties:
                        funnels_prop = properties['Funnels']
                        if funnels_prop.get('multi_select'):
                            for funnel in funnels_prop['multi_select']:
                                if funnel.get('name'):
                                    funnels.add(funnel['name'])

                except Exception as e:
                    logger.warning(f"Error processing offer: {str(e)}")

            # Get database schema to extract valid options
            database = self.client.databases.retrieve(self.database_id)
            
            # Extract valid options from database schema
            properties = database.get('properties', {})
            
            # Get Traffic Source options
            source_prop = properties.get('Source', {})
            if source_prop.get('type') == 'select':
                for option in source_prop.get('select', {}).get('options', []):
                    traffic_sources.add(option['name'])

            # Get Funnel/Vertical options
            vertical_prop = properties.get('Vertical', {})
            if vertical_prop.get('type') == 'select':
                for option in vertical_prop.get('select', {}).get('options', []):
                    funnels.add(option['name'])

            # Create reference data object
            self.reference_data = ReferenceData(
                geo_codes=list(geo_codes),
                partner_names=list(partner_names),
                traffic_sources=list(traffic_sources),
                funnels=list(funnels),
                partner_id_to_name=partner_id_to_name
            )

        except Exception as e:
            logger.error(f"Error loading reference data: {str(e)}")
            raise

    def _get_company(self, partner_id: str) -> str:
        """Get partner name from reference data"""
        return self.reference_data.get_partner_name_by_id(partner_id)

    async def search_deals(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for deals in Notion database based on parameters."""
        try:
            filter_conditions = []
            
            # Handle GEOs and their languages
            if 'geos' in search_params and search_params['geos']:
                geo_conditions = []
                for geo in search_params['geos']:
                    # Check if this GEO has a specific language requirement
                    if ('geo_languages' in search_params and 
                        search_params['geo_languages'] and 
                        geo in search_params['geo_languages']):
                        # Add condition for GEO with specific language
                        geo_conditions.append({
                            "and": [
                                {
                                    "property": "GEO",
                                    "formula": {
                                        "string": {
                                            "contains": geo
                                        }
                                    }
                                },
                                {
                                    "property": "Language",
                                    "multi_select": {
                                        "contains": search_params['geo_languages'][geo]
                                    }
                                }
                            ]
                        })
                    else:
                        # Add condition for GEO without language requirement
                        geo_conditions.append({
                            "property": "GEO",
                            "formula": {
                                "string": {
                                    "contains": geo
                                }
                            }
                        })
                
                # Add all GEO conditions as an OR filter
                if geo_conditions:
                    filter_conditions.append({
                        "or": geo_conditions
                    })

            # Handle traffic sources
            if 'traffic_sources' in search_params and search_params['traffic_sources']:
                source_conditions = []
                for source in search_params['traffic_sources']:
                    source_conditions.append({
                        "property": "Sources",
                        "multi_select": {
                            "contains": source
                        }
                    })
                if source_conditions:
                    filter_conditions.append({
                        "or": source_conditions
                    })

            # Handle partners (using relation field)
            if 'partners' in search_params and search_params['partners']:
                partner_conditions = []
                for partner in search_params['partners']:
                    # Find partner ID from name
                    partner_id = None
                    for pid, pname in self.reference_data.partner_id_to_name.items():
                        if pname == partner:
                            partner_id = pid
                            break
                    
                    if partner_id:
                        partner_conditions.append({
                            "property": "⚡ ALL ADVERTISERS | Kitchen",
                            "relation": {
                                "contains": partner_id
                            }
                        })
                if partner_conditions:
                    filter_conditions.append({
                        "or": partner_conditions
                    })

            # Construct the final filter
            query = {
                "database_id": self.database_id,
                "filter": {
                    "and": filter_conditions
                } if filter_conditions else {}
            }
            
            logger.info("Notion query: " + json.dumps(query, indent=2))

            # Query the database
            response = self.client.databases.query(**query)
            logger.info(f"Notion response: Found {len(response['results'])} deals")
            if response['results']:
                logger.info("First deal properties: " + json.dumps(response['results'][0]['properties'], indent=2))

            # Process and return results
            deals = []
            for page in response['results']:
                props = page['properties']
                
                # Helper function to safely get property value
                def get_prop(prop_name: str, prop_type: str = 'title'):
                    prop = props.get(prop_name, {})
                    if prop_type == 'title':
                        return prop.get(prop_type, [{}])[0].get('plain_text', '')
                    elif prop_type == 'rich_text':
                        return prop.get(prop_type, [{}])[0].get('plain_text', '') if prop.get(prop_type) else ''
                    elif prop_type == 'multi_select':
                        return [item.get('name', '') for item in prop.get(prop_type, [])]
                    elif prop_type == 'number':
                        return prop.get(prop_type, 0)
                    return ''

                # Get partner info
                partner = None
                if '⚡ ALL ADVERTISERS | Kitchen' in props:
                    partner_rel = props['⚡ ALL ADVERTISERS | Kitchen']
                    if partner_rel.get('relation') and len(partner_rel['relation']) > 0:
                        partner_id = partner_rel['relation'][0]['id']
                        partner = self._get_company(partner_id)
                
                # Get GEO and Language
                geo = props.get('GEO', {}).get('formula', {}).get('string', '')
                languages = []
                if 'Language' in props:
                    lang_prop = props['Language']
                    if lang_prop.get('multi_select'):
                        languages = [item['name'] for item in lang_prop['multi_select']]
                
                # Get pricing
                # Network pricing
                cpa = props.get('CPA | Network | Selling', {}).get('number')
                crg = props.get('CRG | Network | Selling', {}).get('number')
                cpl = props.get('CPL | Network | Selling', {}).get('number')
                # Brand pricing
                cpa_brand = props.get('CPA | Brand | Selling', {}).get('number')
                crg_brand = props.get('CRG | Brand | Selling', {}).get('number')
                cpl_brand = props.get('CPL | Brand | Selling', {}).get('number')
                # Buying pricing (for reference)
                cpa_buying = props.get('CPA | Buying', {}).get('number')
                crg_buying = props.get('CRG | Buying', {}).get('number')
                cpl_buying = props.get('CPL | Buying', {}).get('number')
                
                # Get priority flags
                internal_priority = props.get('Internal Priority', {}).get('checkbox', False)
                supplier_priority = props.get('Supplier Priority', {}).get('checkbox', False)
                
                # Get funnels
                funnels = []
                if 'Funnels' in props:
                    funnel_prop = props['Funnels']
                    if funnel_prop.get('multi_select'):
                        funnels = [item['name'] for item in funnel_prop['multi_select']]
                
                # Get traffic sources
                traffic_sources = []
                if 'Sources' in props:
                    sources_prop = props['Sources']
                    if sources_prop.get('multi_select'):
                        traffic_sources = [item['name'] for item in sources_prop['multi_select']]
                
                deals.append({
                    'partner': partner,
                    'geo': geo,
                    'language': languages[0] if languages else 'Native',
                    'traffic_sources': traffic_sources,
                    'funnels': funnels,
                    # Network pricing
                    'cpa': cpa,
                    'crg': crg,
                    'cpl': cpl,
                    # Brand pricing
                    'cpa_brand': cpa_brand,
                    'crg_brand': crg_brand,
                    'cpl_brand': cpl_brand,
                    # Buying pricing
                    'cpa_buying': cpa_buying,
                    'crg_buying': crg_buying,
                    'cpl_buying': cpl_buying,
                    # Priority flags
                    'internal_priority': internal_priority,
                    'supplier_priority': supplier_priority
                })

            # Sort deals by priorities first, then GEO and partner
            deals.sort(key=lambda x: (
                not x.get('internal_priority', False),      # Internal priority first (True values first)
                not x.get('supplier_priority', False),      # Then supplier priority
                x.get('geo', ''),                          # Then by GEO
                x.get('partner', '')                       # Finally by partner name
            ))

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
