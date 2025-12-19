import asyncio
from playwright.async_api import async_playwright

async def save_pinterest_session():
    """
    Opens a browser for manual login and saves the authentication state.
    Run this once to bypass the 'Login to see more' popup.
    """
    async with async_playwright() as p:
        # Launch browser in headed mode so you can interact with it
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print("Navigating to Pinterest...")
        await page.goto("https://www.pinterest.com/login/")
        
        print("\n[ACTION REQUIRED]: Please log in manually in the browser window.")
        print("Once you are logged in and see your home feed, come back here.")
        
        input("\nPress Enter here AFTER you have successfully logged in...")
        
        # Save the storage state (cookies, localStorage, etc.)
        await context.storage_state(path="auth.json")
        print("\n[SUCCESS]: Session saved to 'auth.json'. You can now run the crawler.")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(save_pinterest_session())