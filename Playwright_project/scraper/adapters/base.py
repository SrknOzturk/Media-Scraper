from dataclasses import dataclass                 # dataclass creates lightweight, readable data objects
from typing import Optional, Dict, Any, List      # type hints for optional fields and generic lists

@dataclass
class Pin:                                         # Represents one scraped media item (unified schema)
    source: str                                   # Name of the website (e.g., "pinterest", "instagram")
    board_url: str                                # The URL where the crawl began (context)
    page_url: Optional[str]                       # Link to the pin's detail page (may be None)
    image_url: str                                # Direct image URL (required for downloading)
    thumb_url: Optional[str]                      # Smaller version of the image (if available)
    title: Optional[str]                          # Title or caption (optional)
    alt_text: Optional[str]                       # ALT text from <img> (optional)

class SiteAdapter:                                # Abstract base class for all site-specific adapters
    name: str = "base"                            # Human-readable adapter name (override per site)
    domains: List[str] = []                       # Domain patterns handled by this adapter

    async def pre_open(self, page): ...           # Runs before navigation (setup, remove modals, etc.)

    async def navigate_board(self, page, url): ...# Loads the page and handles site-specific popups

    async def stream_scroll_and_collect(          # Main streaming function: scroll + capture items
        self, page, max_items: int = 1000         # Limit the number of items to collect
    ) -> List[Pin]:
        """Implement in concrete adapters: scroll + snapshot + dedupe + stop."""
        raise NotImplementedError                 # Must be overridden in each adapter implementation
