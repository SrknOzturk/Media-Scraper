from typing import List, Optional
from scraper.adapters.base import Pin, SiteAdapter
from scraper.utils.stream import streaming_scroll_and_collect_stepwise


class ArtStationAdapter(SiteAdapter):
    name = "artstation"
    domains = ["artstation.com"]

    CARD = "a.project-image, figure.project-image-container"   # Grid'deki proje kutuları
    IMG  = "img"

    async def pre_open(self, page):
        pass

    async def navigate_board(self, page, url):
        await page.goto(url, wait_until="domcontentloaded")

    async def _build_pin(self, node) -> Optional[Pin]:
        # Proje linkini al
        a = node
        href = await a.get_attribute("href") if a else None
        page_url = href if href and href.startswith("http") else None

        # Thumbnail / full görsel
        img = await node.query_selector(self.IMG)
        if not img:
            return None

        src = await img.get_attribute("src")
        srcset = await img.get_attribute("srcset")
        alt = await img.get_attribute("alt")

        image_url = None
        thumb_url = None

        if srcset:
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
        return pin.page_url or pin.image_url

    async def stream_scroll_and_collect(self, page, max_items: int = 1000) -> List[Pin]:
        return await streaming_scroll_and_collect_stepwise(
            page=page,
            item_selector=self.CARD,
            build_item=self._build_pin,
            make_key=self._make_key,
            max_items=max_items,
            step_ratio=0.75,
            stagnant_tolerance=6
        )
