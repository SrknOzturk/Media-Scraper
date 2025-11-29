# minimal_async_playwright.py
import asyncio
from playwright.async_api import async_playwright

async def main():
    # Playwright runtime'ını başlatır (Chromium/Firefox/WebKit erişimi buradan gelir)
    async with async_playwright() as pw:
        # Chromium tarayıcısını headless modda açar (True = görünmez; False = görünür)
        browser = await pw.chromium.launch(headless=True)
        # Yeni bir "context" açar: çerezler/localStorage vs bu profil içinde izole tutulur
        context = await browser.new_context()
        # Yeni bir sekme (Page) oluşturur
        page = await context.new_page()

        # Verilen URL'ye gider; default bekleme koşulu 'load' (sayfa yükleme olayı)
        await page.goto("https://google.com")
        # Sekmenin başlığını çeker
        title = await page.title()
        # Başlığı stdout'a basar
        print("Page Title:", title)

        # Tarayıcıyı kapatır (önce context, sonra browser kapanır)
        await browser.close()

# asyncio event loop ile main() fonksiyonunu çalıştırır
asyncio.run(main())
