from typing import List, Dict, Any

class UserSession:
    def __init__(self, deals: List[Dict[str, Any]], current_index: int = 0):
        self.deals = deals
        self.current_index = current_index

    def has_deals(self) -> bool:
        """Check if there are any deals in the session."""
        return bool(self.deals)

    def total_deals(self) -> int:
        """Get total number of deals."""
        return len(self.deals)

    def current_deal(self) -> Dict[str, Any]:
        """Get current deal."""
        if not self.has_deals():
            return {}
        return self.deals[self.current_index]

    def next_deal(self) -> None:
        """Move to next deal if available."""
        if self.has_next():
            self.current_index += 1

    def prev_deal(self) -> None:
        """Move to previous deal if available."""
        if self.has_prev():
            self.current_index -= 1

    def has_next(self) -> bool:
        """Check if there is a next deal."""
        return self.has_deals() and self.current_index < len(self.deals) - 1

    def has_prev(self) -> bool:
        """Check if there is a previous deal."""
        return self.has_deals() and self.current_index > 0
