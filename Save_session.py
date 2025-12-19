import asyncio
from playwright.async_api import async_playwright

async def save_session():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Login sayfasına git
        await page.goto("https://google.com", wait_until="domcontentloaded")

        # Burada manuel olarak giriş yap!
        # Ya da formu otomatik dolduran kod yazabilirsin.

        print("Lütfen giriş yapın ve giriş tamamlanınca ENTER'a basın...")
        input()

        # Oturumu JSON dosyasına kaydet
        await context.storage_state(path="session.json")
        print("Session logged ✔️  -> session.json kaydedildi")

        await browser.close()

asyncio.run(save_session())
