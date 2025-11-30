from playwright.async_api import async_playwright
# Import the asynchronous Playwright API.
# This allows us to launch and control the browser using async/await.


CHROME_ARGS = [
    "--disable-blink-features=AutomationControlled",
    # Helps reduce bot detection by disabling Chrome's automation flags
    # (e.g., prevents navigator.webdriver from being automatically set to True).

    "--no-sandbox",
    # Required inside Docker, CI/CD pipelines, or restricted environments.
    # Prevents Chromium from crashing due to sandbox permission issues.

    "--disable-dev-shm-usage",
    # Fixes shared memory issues inside containers (e.g., Docker),
    # where /dev/shm may be too small, causing Chromium to crash.
]


UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.0.0 Safari/537.36"
)
# Custom User-Agent string.
# Playwright's default UA exposes automation → many websites block it.
# A real Chrome Windows UA reduces suspicion and improves scraping success.


async def open_page(headless: bool = True, storage_state: str | None = None):
    """
    Launches Playwright, opens a Chromium browser, creates a browser context,
    and finally opens a new page. Returns all four objects for later cleanup.

    Returns:
        pw: Playwright instance
        browser: Chromium browser object
        context: Browser context (cookies, localStorage, session)
        page: Actual browser tab for navigation and scraping
    """

    pw = await async_playwright().start()
    # Start the Playwright engine.
    # Without this, no browser instances can be launched.

    browser = await pw.chromium.launch(headless=headless, args=CHROME_ARGS)
    # Launch a Chromium browser instance.
    # headless=True  → browser runs without a visible UI (faster).
    # headless=False → full visible UI (useful for debugging).
    # CHROME_ARGS adds anti-bot and stability flags.

    context = await browser.new_context(
        storage_state=storage_state if storage_state else None,
        # Optional: Load saved cookies / localStorage from a JSON file.
        # This is required for login-required sites (Instagram, Pinterest, etc.).
        # Using saved storage_state avoids having to login manually each run.

        user_agent=UA,
        # Override default User-Agent to appear as a real Chrome desktop browser.

        viewport={"width": 1366, "height": 900}
        # Set a desktop viewport.
        # Many websites switch to mobile DOM below ~800px width, which breaks selectors.
    )

    page = await context.new_page()
    # Open a new tab/page inside the created browser context.
    # All navigation, scrolling, and scraping actions will happen here.

    return pw, browser, context, page
    # Return everything so the caller can properly close all resources later.


async def close_page(pw, browser, context):
    """
    Properly closes Playwright resources.
    This prevents memory leaks, zombie browser processes, and resource locks.
    """

    await context.close()
    # Closes all pages/tabs under this context.
    # Finalizes cookie/localStorage writes.

    await browser.close()
    # Completely closes the Chromium process.
    # If not closed, you may end up with background zombie processes consuming RAM/CPU.

    await pw.stop()
    # Shuts down the Playwright engine itself.
    # Required to stop internal Node.js processes that Playwright spawns.
