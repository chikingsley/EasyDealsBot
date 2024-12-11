import os
import asyncio
from dotenv import load_dotenv
from services.notion_service import NotionService
from models.reference_data import ReferenceData

async def test_reference_data():
    print("Testing Reference Data Loading...")
    
    # Initialize NotionService
    notion_service = NotionService(
        notion_token=os.getenv("NOTION_TOKEN"),
        database_id=os.getenv("NOTION_DATABASE_ID")
    )
    
    # Print loaded reference data
    print("\nGEO Codes:")
    print(sorted(notion_service.reference_data.geo_codes))
    
    print("\nTraffic Sources:")
    print(sorted(notion_service.reference_data.traffic_sources))
    
    print("\nPartner Names:")
    print(sorted(notion_service.reference_data.partner_names))
    
    print("\nFunnels:")
    print(sorted(notion_service.reference_data.funnels))
    
    # Test partner ID lookup using first available partner ID
    partner_ids = list(notion_service.reference_data.partner_id_to_name.keys())
    if partner_ids:
        test_partner_id = partner_ids[0]  # Use the first available partner ID
        partner_name = notion_service.reference_data.get_partner_name_by_id(test_partner_id)
        print(f"\nLooking up partner name for ID '{test_partner_id}': {partner_name}")
    else:
        print("\nNo partner IDs available for testing lookup")

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(test_reference_data())
