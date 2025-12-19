import asyncio
from playwright.async_api import async_playwright
import json

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.0.0 Safari/537.36"
)

PIN_WRAPPER = "div[data-test-id='pinWrapper']"

async def close_overlays(page):
    # Try to close cookie/consent or login popups if present (best-effort)
    candidates = [
        "button[aria-label='Accept all']",          # cookie banner (possible)
        "button[aria-label='Accept All']",          # variant
        "button:has-text('Accept all')",            # general
        "div[role='dialog'] button:has-text('Accept')",
        "div[role='dialog'] button:has-text('I agree')",
        "div[role='dialog'] button[aria-label='Close']",
        "button[aria-label='Close']",
    ]
    for sel in candidates:
        try:
            if await page.is_visible(sel, timeout=500):
                await page.click(sel, timeout=500)
        except:
            pass

async def gentle_scroll(page, steps=4, pause_ms=600):
    for _ in range(steps):
        await page.mouse.wheel(0, 1500)
        await page.wait_for_timeout(pause_ms)

async def scrape_pins(query: str, max_pins: int = 40):
    search_url = f"https://www.pinterest.com/search/pins/?q={query}&rs=typed"
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()

        await page.goto(search_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)

        await close_overlays(page)

        # Ensure at least one pin appears
        await page.wait_for_selector(PIN_WRAPPER, timeout=15000)

        # Help lazy-loaded images render
        await gentle_scroll(page, steps=6, pause_ms=700)

        try:
            pins = await page.query_selector_all(PIN_WRAPPER)
            for i, pin in enumerate(pins):
                if len(results) >= max_pins:
                    break

                try:
                    title_link = await pin.query_selector("a")
                    if not title_link:
                        # No link found; skip this card
                        continue

                    pin_url = await title_link.get_attribute("href")
                    title = await title_link.get_attribute("aria-label")

                    img_el = await title_link.query_selector("img")
                    if not img_el:
                        # Sometimes the image is deeper or not present yet
                        img_el = await pin.query_selector("img")
                    if not img_el:
                        # Still no image; skip safely
                        continue

                    # Prefer src; fall back to srcset (take the last/highest-res entry)
                    img_src = await img_el.get_attribute("src")
                    if not img_src:
                        srcset = await img_el.get_attribute("srcset")
                        if srcset:
                            # srcset: "url1 200w, url2 400w, ..."
                            last = srcset.split(",")[-1].strip()
                            img_src = last.split(" ")[0]

                    # Build absolute URL if href is relative
                    if pin_url and pin_url.startswith("/"):
                        pin_url = f"https://www.pinterest.com{pin_url}"

                    results.append(
                        {"title": title, "url": pin_url, "img": img_src}
                    )

                except Exception as per_pin_err:
                    # Log and continue instead of crashing
                    print(f"[WARN] Failed on one pin: {per_pin_err}")
                    continue

        except Exception as e:
            print(f"[ERROR] Failed to scrape pins at {search_url}: {e}")
        finally:
            await browser.close()

    return results

async def main():
    search_query = "Shrek"
    data = await scrape_pins(search_query, max_pins=60)
    with open(f"{search_query}-results.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Saved {len(data)} pins to {search_query}-results.json")

if __name__ == "__main__":
    asyncio.run(main())
