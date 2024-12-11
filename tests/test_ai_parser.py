import asyncio
import json
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai_service import AIService
from models.reference_data import ReferenceData

# Sample reference data for testing
SAMPLE_REFERENCE_DATA = ReferenceData(
    geo_codes={
        # Original codes
        'UK', 'US', 'ES', 'FR', 'DE', 'CH', 'MX', 'JP', 'FI',
        # Nordic countries
        'DK', 'IS', 'NO', 'SE',
        # Additional test countries
        'PL', 'CZ',
        # More test countries
        'CY', 'JO', 'SA', 'MT', 'LK', 'MY', 'ZA',
        # New countries for GEO+language combinations
        'RU', 'SG', 'CA', 'AE', 'BH', 'KW', 'OM', 'QA'
    },
    partner_names={'Sutra', 'TokoMedia', 'MediaBuy', 'AdCombo'},
    traffic_sources={
        'Facebook', 'Google', 'NativeAds', 'MSN', 'Bing',
        'Instagram', 'TikTok', 'SEO', 'Taboola', 'Push',
        'Email'
    }
)

# Test cases with expected outputs
TEST_CASES = [
    {
        'query': 'UK, ES, FI',
        'expected': {
            'geos': ['ES', 'FI', 'UK']  # No geo_languages since none specified
        }
    },
    {
        'query': 'CHfr DE Native',
        'expected': {
            'geos': ['CH', 'DE'],
            'geo_languages': {'CH': 'French', 'DE': 'Native'}
        }
    },
    {
        'query': 'UK ES Sutra MX',
        'expected': {
            'geos': ['ES', 'MX', 'UK'],  # No geo_languages since none specified
            'partners': ['Sutra']
        }
    },
    {
        'query': 'MX JP Sutra TokoMedia',
        'expected': {
            'geos': ['JP', 'MX'],  # No geo_languages since none specified
            'partners': ['Sutra', 'TokoMedia']
        }
    },
    {
        'query': 'CH French DE Native Sutra',
        'expected': {
            'geos': ['CH', 'DE'],
            'geo_languages': {'CH': 'French', 'DE': 'Native'},
            'partners': ['Sutra']
        }
    },
    {
        'query': 'PL CZ DE NORDICS',
        'expected': {
            'geos': ['CZ', 'DE', 'DK', 'FI', 'IS', 'NO', 'PL', 'SE']
        }
    },
    {
        'query': 'CY JO SA MT LK MY ZA English',
        'expected': {
            'geos': ['CY', 'JO', 'LK', 'MT', 'MY', 'SA', 'ZA'],
            'geo_languages': {'ZA': 'English'}
        }
    },
    {
        'query': 'UK Facebook Google',
        'expected': {
            'geos': ['UK'],
            'traffic_sources': ['Facebook', 'Google']
        }
    },
    {
        'query': 'DE Native Push Email',
        'expected': {
            'geos': ['DE'],
            'geo_languages': {'DE': 'Native'},
            'traffic_sources': ['Email', 'Push']
        }
    },
    {
        'query': 'UK ES Sutra Facebook Instagram TikTok',
        'expected': {
            'geos': ['ES', 'UK'],
            'partners': ['Sutra'],
            'traffic_sources': ['Facebook', 'Instagram', 'TikTok']
        }
    },
    {
        'query': 'NORDICS Native SEO NativeAds',
        'expected': {
            'geos': ['DK', 'FI', 'IS', 'NO', 'SE'],
            'geo_languages': {'DK': 'Native', 'FI': 'Native', 'IS': 'Native', 'NO': 'Native', 'SE': 'Native'},
            'traffic_sources': ['NativeAds', 'SEO']
        }
    },
    {
        'query': 'UK fb gg',
        'expected': {
            'geos': ['UK'],
            'traffic_sources': ['Facebook', 'Google']
        }
    },
    {
        'query': 'DE MSN Bing Native Ads',
        'expected': {
            'geos': ['DE'],
            'traffic_sources': ['Bing', 'MSN', 'NativeAds']
        }
    },
    {
        'query': 'UK ES IG Taboola',
        'expected': {
            'geos': ['ES', 'UK'],
            'traffic_sources': ['Instagram', 'Taboola']
        }
    },
    {
        'query': 'NORDICS Facebook|Google SEO',
        'expected': {
            'geos': ['DK', 'FI', 'IS', 'NO', 'SE'],
            'traffic_sources': ['Facebook', 'Google', 'SEO']
        }
    },
    {
        'query': 'UK Native Ads+SEO',
        'expected': {
            'geos': ['UK'],
            'traffic_sources': ['NativeAds', 'SEO']
        }
    },
    {
        'query': 'RUru, SGen, CAen, UKru, GCC, MX Native, BR Native',
        'expected': {
            'geos': ['AE', 'BH', 'BR', 'CA', 'KW', 'MX', 'OM', 'QA', 'RU', 'SA', 'SG', 'UK'],
            'geo_languages': {
                'RU': 'Russian',
                'SG': 'English',
                'CA': 'English',
                'UK': 'Russian',
                'MX': 'Native',
                'BR': 'Native'
            }
        }
    }
]

async def run_tests():
    ai_service = AIService(SAMPLE_REFERENCE_DATA)
    
    print("\nRunning AI Parser Tests\n" + "="*50)
    
    for i, test_case in enumerate(TEST_CASES, 1):
        query = test_case['query']
        expected = test_case['expected']
        
        print(f"\nTest {i}: '{query}'")
        print("-" * 30)
        
        try:
            result = await ai_service.parse_search_query(query)
            
            # Sort lists for comparison
            if 'geos' in result:
                result['geos'].sort()
            if 'partners' in result:
                result['partners'].sort()
            if 'traffic_sources' in result:
                result['traffic_sources'].sort()
            
            if 'geos' in expected:
                expected['geos'].sort()
            if 'partners' in expected:
                expected['partners'].sort()
            if 'traffic_sources' in expected:
                expected['traffic_sources'].sort()
            
            print("Result:")
            print(json.dumps(result, indent=2))
            print("\nExpected:")
            print(json.dumps(expected, indent=2))
            
            matches = result == expected
            print(f"\nPass: {'✅' if matches else '❌'}")
            
            if not matches:
                print("\nDifferences:")
                for key in set(result.keys()) | set(expected.keys()):
                    if key not in result:
                        print(f"Missing key: {key}")
                    elif key not in expected:
                        print(f"Extra key: {key}")
                    elif result[key] != expected[key]:
                        print(f"Mismatch in {key}:")
                        print(f"  Got:      {result[key]}")
                        print(f"  Expected: {expected[key]}")
            
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Pass: ❌")

if __name__ == "__main__":
    asyncio.run(run_tests())
