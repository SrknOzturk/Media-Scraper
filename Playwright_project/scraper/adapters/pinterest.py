import re
from typing import List, Optional
from scraper.adapters.base import Pin, SiteAdapter
from scraper.utils.stream import streaming_scroll_and_collect_stepwise


class PinterestAdapter(SiteAdapter):
    name = "pinterest"
    domains = ["pinterest.com"]

    PIN  = "div[data-test-id='pinWrapper'], div[data-test-id='pin']"
    LINK = "a[href^='/pin/']"
    IMG  = "img"

    _PINIMG_SIZE_DIR_RE = re.compile(r"/(\d+)x/")     # matches “…/236x/…”, “…/564x/…”
    _PINIMG_HOST_RE     = re.compile(r"^https?://i\.pinimg\.com/")  # restricts to i.pinimg.com

    async def pre_open(self, page):
        await page.goto("about:blank")

    async def navigate_board(self, page, url):
        await page.goto(url, wait_until="domcontentloaded")
        for sel in [
            "button[aria-label='Accept all']",
            "button:has-text('Accept all')",
            "div[role='dialog'] button:has-text('Accept')",
            "button:has-text('Allow all cookies')",
        ]:
            try:
                await page.click(sel, timeout=1500)
            except:
                pass
        try:
            await page.wait_for_selector(self.PIN, timeout=8000)
        except:
            await page.wait_for_timeout(1500)

    def _largest_from_srcset(self, srcset: str) -> Optional[str]:
        # Parse "url width, url width, ..." → pick max width
        best_url, best_w = None, -1
        for chunk in srcset.split(","):
            part = chunk.strip()
            if not part:
                continue
            pieces = part.split()
            url = pieces[0]
            w = -1
            if len(pieces) > 1 and pieces[1].endswith("w"):
                try:
                    w = int(pieces[1][:-1])
                except:
                    w = -1
            if w > best_w:
                best_w, best_url = w, url
        return best_url

    def _try_upscale_pinimg(self, url: Optional[str]) -> Optional[str]:
        # If it’s a pinimg URL with “…/<size>x/…”, replace size with “originals”
        if not url or not self._PINIMG_HOST_RE.match(url):
            return url
        return self._PINIMG_SIZE_DIR_RE.sub("/originals/", url)

    async def _build_pin(self, node, page) -> Optional[Pin]:
        # Detail link
        a = await node.query_selector(self.LINK)
        href = await a.get_attribute("href") if a else None
        page_url = f"https://www.pinterest.com{href}" if (href and href.startswith("/")) else href

        # Image element
        img = await node.query_selector(self.IMG)
        if not img:
            print("NOIMAGE")
            print(node)
            return None

        # Prefer the largest declared candidate in srcset; also check data-* fallbacks
        srcset  = await img.get_attribute("srcset") or await img.get_attribute("data-srcset")
        src     = await img.get_attribute("src")    or await img.get_attribute("data-src")
        alt     = await img.get_attribute("alt")

        # 1) Try srcset max width
        image_url = self._largest_from_srcset(srcset) if srcset else None
        print("LARGEST"+str(image_url))
        # 2) Fallback: use src
        if not image_url:
            image_url = src
            print("SOURCE",str(image_url))

        # 3) If it’s a pinimg downsized path, try to upgrade “…/<size>x/…” → “…/originals/…”
        image_url = self._try_upscale_pinimg(image_url)

        # 4) Keep a smaller variant as thumb when possible
        thumb_url = None
        if src and src != image_url:
            thumb_url = src

        if not image_url:
            print("NONE")
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
            item_selector=self.PIN,
            build_item=self._build_pin,
            make_key=self._make_key,
            max_items=max_items,
            step_ratio=0.6,
            stagnant_tolerance=8,
            wait_min_ms=700,
            wait_jitter_ms=800,
            max_rounds=5
        )
