from urllib.parse import urlparse
# Used to extract the domain (hostname) from a URL.
# Example: urlparse("https://www.pinterest.com/x").netloc → "www.pinterest.com"

from typing import List
# Provides type hints like List[Pin] for clarity and IDE support.


from scraper.browser import open_page, close_page
# Helper functions:
# open_page → launches Playwright + browser + context + page
# close_page → properly closes all resources


from scraper.adapters.base import Pin, SiteAdapter
# Pin → our unified data structure for scraped media items
# SiteAdapter → base class for all site-specific adapters


from scraper.adapters.pinterest import PinterestAdapter
from scraper.adapters.instagram import InstagramAdapter
from scraper.adapters.artstation import ArtStationAdapter
# Import concrete adapter implementations for each supported website.


# List of all registered adapters.
# Each adapter declares which domains it supports, so we can match URLs dynamically.
ADAPTERS: list[SiteAdapter] = [
    PinterestAdapter(),
    InstagramAdapter(),
    ArtStationAdapter(),
]


def pick_adapter(url: str) -> SiteAdapter:
    """
    Selects the appropriate adapter for the given URL based on its domain.
    Example:
        URL containing "pinterest.com" → PinterestAdapter
    """
    host = urlparse(url).netloc.lower()
    # Extract the hostname from the URL and normalize to lowercase.
    # Example: "https://www.Pinterest.com" → "www.pinterest.com"

    for a in ADAPTERS:
        # Each adapter has a `domains` list, such as ["pinterest.com"].
        # We check if any declared domain fragment appears inside the hostname.
        if any(d in host for d in a.domains):
            return a

    # If no adapter matches, raise a clear error.
    raise ValueError(f"No adapter registered for host: {host}")


async def crawl_board(
    url: str,
    max_items: int = 1000,
    headless: bool = True,
    storage_state: str | None = None
) -> List[Pin]:
    """
    High-level crawl function.
    Steps:
        1. Pick the correct adapter for this URL.
        2. Open a browser and page.
        3. Let the adapter:
            - prepare the page (pre_open)
            - navigate to the board/listing
            - scroll until pins are loaded
            - extract all pins
        4. Close the browser (always, even on error).
        5. Return a unified list of Pin objects.
    """

    # Choose the correct adapter: PinterestAdapter, InstagramAdapter, etc.
    adapter = pick_adapter(url)

    # Launch Playwright and open a browser context + page.
    pw, browser, context, page = await open_page(
        headless=headless,
        storage_state=storage_state
    )

    try:
        # Allow the adapter to run any pre-navigation setup (e.g., closing modals).
        await adapter.pre_open(page)

        # Navigate to the target URL and handle cookies/popups.
        await adapter.navigate_board(page, url)

        pins = await adapter.stream_scroll_and_collect(page, max_items=max_items)#Scroll to down and gather pins simultaneously
        return pins

    finally:
        # Ensure resources are always released,
        # even if an exception occurred above.
        await close_page(pw, browser, context)
