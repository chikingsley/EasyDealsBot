import os
import logging
import json
import re
from typing import Dict, Any, List, Set, Tuple
from mistralai import Mistral
from models.reference_data import ReferenceData

logger = logging.getLogger(__name__)

class AIService:
    # Core traffic source mappings - everything else will be matched case-insensitive
    TRAFFIC_SOURCE_ALIASES = {
        # Facebook aliases
        'fb': 'Facebook',
        'FB': 'Facebook',
        'facebook': 'Facebook',
        
        # Google aliases
        'gg': 'Google',
        'GG': 'Google',
        'google': 'Google',
        
        # Microsoft/Bing aliases
        'msn': 'MSN',
        'MSN': 'MSN',
        'bing': 'Bing',
        'Bing': 'Bing',
        
        # Instagram aliases
        'ig': 'Instagram',
        'IG': 'Instagram',
        'instagram': 'Instagram',
        'insta': 'Instagram',
        
        # Native Ads - all variations
        'native ads': 'NativeAds',
        'Native Ads': 'NativeAds',
        'native Ads': 'NativeAds',
        'NativeAds': 'NativeAds',
        'NATIVE ADS': 'NativeAds',
        
        # Taboola
        'taboola': 'Taboola',
        'Taboola': 'Taboola',
        
        # TikTok
        'tiktok': 'TikTok',
        'TikTok': 'TikTok',
        'tt': 'TikTok',
        'TT': 'TikTok',
        
        # SEO
        'seo': 'SEO',
        'SEO': 'SEO',

        # Push
        'push': 'Push',
        'Push': 'Push',
        'pushnotif': 'Push',
        'pushnotification': 'Push',
        
        # Email
        'email': 'Email',
        'Email': 'Email',
        'mail': 'Email',
        'Mail': 'Email',
    }

    def __init__(self, reference_data: ReferenceData = None):
        self._validate_api_key()
        self.client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
        self.model = "mistral-large-latest"
        self.reference_data = reference_data
        
        # Pre-construct the system message with reference data
        self.system_message = (
            "You are a deal search assistant specialized in parsing search queries. "
            "You have access to these valid reference values:\n\n"
            f"GEO CODES: {', '.join(sorted(self.reference_data.geo_codes)) if self.reference_data else ''}\n"
            f"TRAFFIC SOURCES: {', '.join(sorted(self.reference_data.traffic_sources)) if self.reference_data else ''}\n"
            f"PARTNERS: {', '.join(sorted(self.reference_data.partner_names)) if self.reference_data else ''}\n\n"
            "RULES:\n"
            "1. Only use the valid GEO codes, traffic sources, and partners listed above\n"
            "2. Return GEO codes in uppercase 2-letter format\n"
            "3. If a GEO has no explicit language, use 'Native'\n"
            "4. GEO with language can be specified as 'CHfr' (Swiss French) or 'CH French'\n"
            "5. Multiple values can be specified for any field\n\n"
            "Return a JSON object with these fields (omit if not found in query):\n"
            "- geos: list of GEO codes\n"
            "- geo_languages: map of GEO codes to languages\n"
            "- partners: list of partner names\n"
            "- traffic_sources: list of traffic sources"
        )

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
        
        found_sources = set()
        
        # First check for multi-word sources (like "Native Ads")
        # This needs to happen before we split the text to avoid breaking up phrases
        lower_text = text.lower()
        for source, normalized in self.TRAFFIC_SOURCE_ALIASES.items():
            if source.lower() in lower_text:
                found_sources.add(normalized)
        
        # Then check individual parts
        parts = [p.strip() for p in re.split(r'[,\s|+]+', text) if p.strip()]
        
        for i, part in enumerate(parts):
            part_lower = part.lower()
            
            # Skip if it's a GEO code
            if part.upper() in self.reference_data.geo_codes:
                continue
                
            # Skip if it's a partner name
            if any(partner.lower() == part_lower for partner in self.reference_data.partner_names):
                continue
                
            # Skip language indicators
            if part_lower in {'native', 'english', 'french', 'spanish', 'german', 'russian'}:
                # Only skip if it's actually being used as a language (after a GEO)
                if i > 0 and parts[i-1].upper() in self.reference_data.geo_codes:
                    continue
                # If "native" isn't being used as a language, it might be part of "Native Ads"
                if part_lower == 'native':
                    # Look ahead for "ads"
                    if i + 1 < len(parts) and parts[i+1].lower() in {'ads', 'ad'}:
                        found_sources.add('NativeAds')
                        continue
            
            # Check if it's a known source (case-insensitive)
            for source in self.reference_data.traffic_sources:
                if source.lower() == part_lower:
                    found_sources.add(source)
                    break
        
        return sorted(list(found_sources))

    def _extract_partner_names(self, text: str) -> List[str]:
        """Extract partner names using pattern matching"""
        if not self.reference_data:
            return []
        
        # Look for exact matches of known partner names
        found_partners = []
        # Split by common separators first
        parts = [p.strip() for p in re.split(r'[,\s]+', text) if p.strip()]
        
        # Check each part against known partners
        for part in parts:
            part_lower = part.lower()
            for partner in self.reference_data.partner_names:
                if partner.lower() == part_lower:
                    found_partners.append(partner)
        
        return found_partners

    def _expand_region(self, region: str) -> List[str]:
        """Expand region code into its constituent country codes"""
        REGION_MAPPING = {
            'NORDICS': ['DK', 'FI', 'IS', 'NO', 'SE'],
            'BALTICS': ['EE', 'LV', 'LT'],
            'GCC': ['AE', 'BH', 'KW', 'OM', 'QA', 'SA'],
            'LATAM': ['AR', 'BO', 'BR', 'CL', 'CO', 'CR', 'CU', 'DO', 'EC', 
                     'SV', 'GT', 'HN', 'MX', 'NI', 'PA', 'PY', 'PE', 'UY', 'VE']
        }
        return sorted(REGION_MAPPING.get(region.upper(), []))

    def _normalize_language(self, lang: str) -> str:
        """Normalize language codes to full names"""
        LANGUAGE_MAP = {
            # Common languages
            'native': 'Native',
            'english': 'English', 'en': 'English',
            'french': 'French', 'fr': 'French',
            'spanish': 'Spanish', 'es': 'Spanish',
            'german': 'German', 'de': 'German',
            'russian': 'Russian', 'ru': 'Russian',
            
            # Additional languages
            'portuguese': 'Portuguese', 'pt': 'Portuguese',
            'italian': 'Italian', 'it': 'Italian',
            'dutch': 'Dutch', 'nl': 'Dutch',
            'polish': 'Polish', 'pl': 'Polish',
            'turkish': 'Turkish', 'tr': 'Turkish',
            'arabic': 'Arabic', 'ar': 'Arabic',
            'chinese': 'Chinese', 'zh': 'Chinese',
            'japanese': 'Japanese', 'ja': 'Japanese',
            'korean': 'Korean', 'ko': 'Korean',
            
            # Aliases
            'nat': 'Native',
            'eng': 'English',
            'fra': 'French',
            'esp': 'Spanish',
            'deu': 'German',
            'rus': 'Russian',
            'por': 'Portuguese',
            'ita': 'Italian',
            'nld': 'Dutch',
            'pol': 'Polish',
            'tur': 'Turkish',
            'ara': 'Arabic',
            'chn': 'Chinese',
            'jpn': 'Japanese',
            'kor': 'Korean'
        }
        return LANGUAGE_MAP.get(lang.lower(), 'Native')

    def _extract_geo_with_language(self, text: str) -> Tuple[List[str], Dict[str, str]]:
        """Extract GEO codes and their associated languages"""
        if not self.reference_data:
            return [], {}
        
        geos = set()  # Using set to avoid duplicates
        geo_languages = {}
        
        # Split by common separators
        parts = [p.strip() for p in re.split(r'[,\s|+]+', text) if p.strip()]
        print(f"Parts: {parts}")  # Debug
        
        i = 0
        while i < len(parts):
            part = parts[i]
            print(f"Processing part {i}: {part}")  # Debug
            
            # Handle region expansions (NORDICS, GCC, etc.)
            expanded_geos = self._expand_region(part)
            if expanded_geos:
                geos.update(expanded_geos)
                print(f"Added expanded geos: {expanded_geos}")  # Debug
                
                # Look ahead for language
                if i + 1 < len(parts):
                    next_part = parts[i+1].lower()
                    # Check if this "native" is actually part of "Native Ads"
                    if next_part == 'native' and i + 2 < len(parts) and parts[i+2].lower() in {'ads', 'ad'}:
                        i += 1
                    elif next_part in self._normalize_language(next_part).lower():
                        lang = self._normalize_language(next_part)
                        for country in expanded_geos:
                            geo_languages[country] = lang
                        i += 2
                        continue
                
                i += 1
                continue
            
            # Handle combined format (e.g., CHfr, RUru)
            geo_lang_match = re.match(r'^([A-Z]{2})((?:[a-z]{2}|nat))$', part, re.IGNORECASE)
            if geo_lang_match and geo_lang_match.group(1).upper() in self.reference_data.geo_codes:
                geo = geo_lang_match.group(1).upper()
                geos.add(geo)
                lang_code = geo_lang_match.group(2).lower()
                geo_languages[geo] = self._normalize_language(lang_code)
                print(f"Added combined geo+lang: {geo}={geo_languages[geo]}")  # Debug
                i += 1
                continue
            
            # Handle regular GEO codes with language
            if part.upper() in self.reference_data.geo_codes:
                geo = part.upper()
                geos.add(geo)
                print(f"Added geo: {geo}")  # Debug
                
                # Look ahead for language
                if i + 1 < len(parts):
                    next_part = parts[i+1].lower()
                    next_lang = self._normalize_language(next_part)
                    print(f"Looking at next part for {geo}: {next_part} -> {next_lang}")  # Debug
                    
                    # Check if next part is a valid language
                    if next_part in next_lang.lower():
                        # Check if this "native" is actually part of "Native Ads"
                        if next_part == 'native' and i + 2 < len(parts) and parts[i+2].lower() in {'ads', 'ad'}:
                            print(f"Skipping Native Ads for {geo}")  # Debug
                            i += 1
                        else:
                            geo_languages[geo] = next_lang
                            print(f"Added language for {geo}: {next_lang}")  # Debug
                            i += 2
                            continue
                
                i += 1
                continue
            
            i += 1
        
        print(f"\nFinal state:")  # Debug
        print(f"Geos: {sorted(list(geos))}")  # Debug
        print(f"Languages: {geo_languages}")  # Debug
        return sorted(list(geos)), geo_languages

    async def parse_search_query(self, query: str) -> Dict[str, Any]:
        """Parse natural language search query into structured parameters"""
        try:
            logger.info(" Query: " + query)
            
            # Use Mistral as primary parser
            messages = [
                {"role": "system", "content": self.system_message},
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
                result = json.loads(content)
                
                # Validate and normalize Mistral's output using pattern matching
                if 'geos' in result:
                    validated_geos = [
                        geo for geo in result['geos'] 
                        if geo in self.reference_data.geo_codes
                    ]
                    if validated_geos:
                        result['geos'] = validated_geos
                    else:
                        del result['geos']
                
                if 'traffic_sources' in result:
                    validated_sources = [
                        source for source in result['traffic_sources']
                        if source in self.reference_data.traffic_sources
                    ]
                    if validated_sources:
                        result['traffic_sources'] = validated_sources
                    else:
                        del result['traffic_sources']
                
                if 'partners' in result:
                    validated_partners = [
                        partner for partner in result['partners']
                        if partner in self.reference_data.partner_names
                    ]
                    if validated_partners:
                        result['partners'] = validated_partners
                    else:
                        del result['partners']
                
                # If Mistral failed to find anything, fall back to pattern matching
                if not result:
                    return self._fallback_pattern_matching(query)
                
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Mistral response: {str(e)}")
                return self._fallback_pattern_matching(query)

        except Exception as e:
            logger.error(f"Error in AI service: {str(e)}")
            return {}

    def _fallback_pattern_matching(self, query: str) -> Dict[str, Any]:
        """Fallback to pattern matching if Mistral fails"""
        result = {}
        
        geo_result = self._extract_geo_with_language(query)
        if geo_result[0]:
            result['geos'] = geo_result[0]
        if geo_result[1]:
            result['geo_languages'] = geo_result[1]
        
        traffic_sources = self._extract_traffic_sources(query)
        if traffic_sources:
            result['traffic_sources'] = traffic_sources
        
        partners = self._extract_partner_names(query)
        if partners:
            result['partners'] = partners
            
        return result
