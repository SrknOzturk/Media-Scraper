from typing import List, Optional
from scraper.adapters.base import Pin, SiteAdapter
from scraper.utils.stream import streaming_scroll_and_collect_stepwise


class InstagramAdapter(SiteAdapter):
    name = "instagram"                                      # Pin kaynağı
    domains = ["instagram.com"]                             # Bu adapter hangi domain'e hitap ediyor

    GRID_LINK = "a[href*='/p/'], a[href*='/reel/']"         # Post + Reel grid tile selector
    IMG = "img"                                             # Instagram grid görselleri <img> içinde gelir

    async def pre_open(self, page):
        pass                                                # Login/cookie için storage_state kullanılabiliyor

    async def navigate_board(self, page, url):
        await page.goto(url, wait_until="domcontentloaded")

        # Basit cookie izinlerini kapatma (varsa)
        for sel in [
            "button:has-text('Only allow essential cookies')",
            "button:has-text('Allow all cookies')",
            "button:has-text('Accept')"
        ]:
            try:
                await page.click(sel, timeout=1500)
            except:
                pass

    async def _build_pin(self, node) -> Optional[Pin]:
        # 1) Post/Reel linki
        href = await node.get_attribute("href")
        if not href:
            return None

        if href.startswith("/"):
            page_url = f"https://www.instagram.com{href}"
        elif href.startswith("http"):
            page_url = href
        else:
            page_url = None

        # 2) Fotoğraf/thumbnail
        img = await node.query_selector(self.IMG)
        if not img:
            return None

        src = await img.get_attribute("src")
        srcset = await img.get_attribute("srcset")
        alt = await img.get_attribute("alt")

        image_url = None
        thumb_url = None

        if srcset:
            # En büyük kalite genelde son srcset entry
            try:
                image_url = srcset.split(",")[-1].split(" ")[0]
                thumb_url = src
            except:
                image_url = src
        else:
            image_url = src

        if not image_url:
            return None

        board_url = await node.evaluate("() => window.location.href")

        return Pin(
            source=self.name,
            board_url=board_url,
            page_url=page_url,
            image_url=image_url,
            thumb_url=thumb_url,
            title=None,
            alt_text=alt
        )

    def _make_key(self, pin: Pin) -> Optional[str]:
        # En stabil key → sayfa URL'si
        return pin.page_url or pin.image_url

    async def stream_scroll_and_collect(self, page, max_items: int = 1000) -> List[Pin]:
        return await streaming_scroll_and_collect_stepwise(
            page=page,
            item_selector=self.GRID_LINK,
            build_item=self._build_pin,
            make_key=self._make_key,
            max_items=max_items,
            step_ratio=0.75,
            stagnant_tolerance=6
        )
