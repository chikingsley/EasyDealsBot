from typing import List, Dict, Any, Set

class UserSession:
    def __init__(self, deals: List[Dict[str, Any]], current_index: int = 0):
        self.deals = deals
        self.current_index = current_index
        self.selected_deals: Set[int] = set()  # Track selected deal indices
        self.deals_per_page = 5
        self.pricing_mode = "network"  # "network" or "brand"

    def has_deals(self) -> bool:
        """Check if there are any deals in the session."""
        return bool(self.deals)

    def total_deals(self) -> int:
        """Get total number of deals."""
        return len(self.deals)

    def get_current_page(self) -> int:
        """Get current page number (1-based)."""
        return (self.current_index // self.deals_per_page) + 1

    def total_pages(self) -> int:
        """Get total number of pages."""
        return (len(self.deals) + self.deals_per_page - 1) // self.deals_per_page

    def has_next(self) -> bool:
        """Check if there is a next page."""
        return self.current_index + self.deals_per_page < len(self.deals)

    def has_prev(self) -> bool:
        """Check if there is a previous page."""
        return self.current_index >= self.deals_per_page

    def next_page(self) -> None:
        """Move to next page."""
        if self.has_next():
            self.current_index += self.deals_per_page

    def prev_page(self) -> None:
        """Move to previous page."""
        if self.has_prev():
            self.current_index -= self.deals_per_page

    def get_current_page_deals(self) -> List[Dict[str, Any]]:
        """Get deals for the current page."""
        start_idx = (self.get_current_page() - 1) * self.deals_per_page
        end_idx = min(start_idx + self.deals_per_page, len(self.deals))
        return self.deals[start_idx:end_idx]

    def current_deal(self) -> Dict[str, Any]:
        """Get current deal."""
        if not self.has_deals():
            return {}
        return self.deals[self.current_index]

    def toggle_deal_selection(self, deal_index: int) -> bool:
        """Toggle selection state of a deal. Returns new selection state."""
        if 0 <= deal_index < len(self.deals):
            if deal_index in self.selected_deals:
                self.selected_deals.remove(deal_index)
                return False
            else:
                self.selected_deals.add(deal_index)
                return True
        return False

    def is_deal_selected(self, deal_index: int) -> bool:
        """Check if a deal is selected."""
        return deal_index in self.selected_deals

    def get_selected_deals(self) -> List[Dict[str, Any]]:
        """Get all selected deals."""
        return [self.deals[i] for i in sorted(self.selected_deals)]

    def clear_selections(self) -> None:
        """Clear all deal selections."""
        self.selected_deals.clear()

    def next_deal(self) -> None:
        """Move to next deal if available."""
        if self.has_next_deal():
            self.current_index += 1

    def prev_deal(self) -> None:
        """Move to previous deal if available."""
        if self.has_prev_deal():
            self.current_index -= 1

    def has_next_deal(self) -> bool:
        """Check if there is a next deal."""
        return self.has_deals() and self.current_index < len(self.deals) - 1

    def has_prev_deal(self) -> bool:
        """Check if there is a previous deal."""
        return self.has_deals() and self.current_index > 0

    def toggle_pricing_mode(self) -> str:
        """Toggle between network and brand pricing. Returns new mode."""
        self.pricing_mode = "brand" if self.pricing_mode == "network" else "network"
        return self.pricing_mode

    def format_deal_for_display(self, deal: Dict[str, Any], include_partner: bool = True) -> str:
        """Format a deal for display with current pricing mode."""
        # Get pricing based on mode
        if self.pricing_mode == "brand":
            price = deal.get('cpa_brand', '')
            crg = deal.get('crg_brand', '')
            cpl = deal.get('cpl_brand', '')
        else:  # network
            price = deal.get('cpa', '')
            crg = deal.get('crg', '')
            cpl = deal.get('cpl', '')

        # Format the basic info
        parts = []
        if include_partner:
            parts.append(deal.get('partner', 'N/A'))
        parts.append(f"{deal.get('geo', 'N/A')} {deal.get('language', 'Native')}")
        
        result = " -> ".join(parts)
        
        # Add traffic sources
        traffic_sources = deal.get('traffic_sources', [])
        if traffic_sources:
            traffic_str = ' | '.join(traffic_sources) if isinstance(traffic_sources, list) else traffic_sources
            result += f" [{traffic_str}]"
        
        # Add pricing
        pricing_parts = []
        if price:
            cpa_str = f"${price}"
            if crg:
                cpa_str += f"+{int(float(crg)*100)}%"
            pricing_parts.append(cpa_str)
        if cpl:
            pricing_parts.append(f"${cpl} CPL")
        
        if pricing_parts:
            result += f" {' | '.join(pricing_parts)}"
        
        # Add funnels on new line if present
        funnels = deal.get('funnels', [])
        if funnels:
            if isinstance(funnels, list):
                result += f"\nFunnels: {' | '.join(funnels)}"
            else:
                result += f"\nFunnels: {funnels}"
        
        return result

    def format_deal_button(self, deal: Dict[str, Any], absolute_idx: int, is_selected: bool) -> str:
        """Format a deal for button display with priority stars."""
        emoji = "✅" if is_selected else "⭕️"
        
        # Basic info: GEO-Partner-Source
        partner = deal.get('partner', 'N/A')
        geo = deal.get('geo', 'N/A')
        traffic_sources = deal.get('traffic_sources', [])
        traffic_str = ' | '.join(traffic_sources) if isinstance(traffic_sources, list) else traffic_sources
        
        button_text = f"{emoji} {geo}-{partner}-{traffic_str}"
        
        # Add priority stars if present
        stars = ""
        if deal.get('supplier_priority'):
            stars += "☆"
        if deal.get('internal_priority'):
            stars += "🌟"
        
        if stars:
            button_text += f" {stars}"
        
        # Truncate if too long (leaving room for stars)
        max_length = 45 if stars else 50
        if len(button_text) > max_length:
            button_text = button_text[:max_length-3] + "..."
            
        return button_text
