from typing import Set, Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class ReferenceData:
    def __init__(self, geo_codes: List[str] = None, partner_names: List[str] = None,
                 traffic_sources: List[str] = None, funnels: List[str] = None,
                 partner_id_to_name: Dict[str, str] = None):
        """Initialize reference data with provided values"""
        self.geo_codes = set(geo_codes or [])
        self.partner_names = set(partner_names or [])
        self.traffic_sources = set(traffic_sources or [])
        self.funnels = set(funnels or [])
        self.partner_id_to_name = partner_id_to_name or {}

    def load_from_notion_response(self, pages: list[Dict[str, Any]]) -> None:
        """Load reference data from Notion database query response"""
        try:
            for page in pages:
                properties = page.get('properties', {})
                
                # Extract GEO from GEO-Funnel Code
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
                                self.geo_codes.add(geo)
                
                # Extract partner names
                if '⚡ ALL ADVERTISERS | Kitchen' in properties:
                    partner_rel = properties['⚡ ALL ADVERTISERS | Kitchen']
                    if partner_rel.get('relation') and len(partner_rel['relation']) > 0:
                        partner_id = partner_rel['relation'][0]['id']
                        if 'Partner' in properties:
                            partner_prop = properties['Partner']
                            if partner_prop.get('formula') and partner_prop['formula'].get('string'):
                                partner_name = partner_prop['formula']['string']
                                self.partner_names.add(partner_name)
                                self.partner_id_to_name[partner_id] = partner_name
                
                # Extract traffic sources
                if 'Sources' in properties:
                    sources_prop = properties['Sources']
                    if sources_prop.get('multi_select'):
                        for source in sources_prop['multi_select']:
                            if source.get('name'):
                                self.traffic_sources.add(source['name'])
                
                # Extract funnels
                if 'Funnels' in properties:
                    funnels_prop = properties['Funnels']
                    if funnels_prop.get('multi_select'):
                        for funnel in funnels_prop['multi_select']:
                            if funnel.get('name'):
                                self.funnels.add(funnel['name'])
            
            logger.info(f"Loaded reference data:")
            logger.info(f"- {len(self.geo_codes)} GEO codes")
            logger.info(f"- {len(self.partner_names)} partner names")
            logger.info(f"- {len(self.traffic_sources)} traffic sources")
            logger.info(f"- {len(self.funnels)} funnels")
            
        except Exception as e:
            logger.error(f"Error loading reference data: {str(e)}")
            raise

    def get_partner_name_by_id(self, partner_id: str) -> Optional[str]:
        """Get partner name by ID"""
        return self.partner_id_to_name.get(partner_id)
