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
    VIDEO = "video"  # <--- YENİ: Video elementi seçicisi

    _PINIMG_SIZE_DIR_RE = re.compile(r"/(\d+)x/")
    _PINIMG_HOST_RE     = re.compile(r"^https?://i\.pinimg\.com/")

    async def pre_open(self, page):
        await page.goto("about:blank")

    async def navigate_board(self, page, url):
        await page.goto(url, wait_until="domcontentloaded")
        # Cookie kapatma mantığı (mevcut kodunuzdaki gibi)
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
        # Gelen veri: "url1 1x, url2 2x, url3 3x, url4 4x"
        # Mantık: Virgülle ayır -> En sonuncuyu al -> URL kısmını çek.
        try:
            print("SRCSET:",str(srcset))
            if not srcset:
                return None
            
            # 1. Virgüllerden ayırıp listeye çevir
            candidates = srcset.split(",")
            
            # 2. Listenin son elemanını al (en yüksek kalite varsayımıyla)
            last_candidate = candidates[-1].strip()
            
            # 3. "https://...jpg 4x" stringinden sadece URL kısmını (ilk parça) al
            return last_candidate.split()[0]
            
        except Exception:
            # Beklenmedik bir format olursa None dön, build_pin zaten src'yi kullanacak
            return None

    def _try_upscale_pinimg(self, url: Optional[str]) -> Optional[str]:
        # Mevcut kodunuzdaki mantık aynen kalacak
        if not url or not self._PINIMG_HOST_RE.match(url):
            return url
        return self._PINIMG_SIZE_DIR_RE.sub("/originals/", url)

    async def _build_pin(self, node, page) -> Optional[Pin]:
        # 1) Detay linkini al
        a = await node.query_selector(self.LINK)
        href = await a.get_attribute("href") if a else None
        page_url = f"https://www.pinterest.com{href}" if (href and href.startswith("/")) else href

        # --- VİDEO KONTROLÜ ---
        media_type = "image"
        video_url = None
        
        # Grid kartının içinde <video> etiketi var mı?
        video_el = await node.query_selector(self.VIDEO)
        if video_el:
            print("VIDEO",str(video_url))
            media_type = "video"
            src_v = await video_el.get_attribute("src")
            # src bazen "blob:..." olabilir, bu durumda indirmek zordur ama 
            # en azından bunun bir video olduğunu biliyoruz.
            if src_v:
                video_url = src_v

        # 2) Görseli (veya video kapağını) al
        # Video olsa bile Pinterest bir <img> (poster) gösterir, onu almalıyız.
        img = await node.query_selector(self.IMG)
        
        # Eğer ne video ne resim bulabildiysek bu pini atla
        if not img and not video_url:
            return None

        # -- Resim URL Çıkarma (Mevcut mantık) --
        image_url = None
        thumb_url = None
        alt = None

        if img:
            srcset = await img.get_attribute("srcset") or await img.get_attribute("data-srcset")
            src = await img.get_attribute("src")    or await img.get_attribute("data-src")
            alt = await img.get_attribute("alt")

            # srcset içinden en büyüğünü seç
            image_url = self._largest_from_srcset(srcset) if srcset else None
            print("LARGE:",str(image_url))
            
            # Bulamazsa src'ye dön
            if not image_url:
                image_url = src
                print("SOURCE:",str(image_url))

            # Kalite yükseltmeyi dene (236x -> originals)
            image_url = self._try_upscale_pinimg(image_url)
            print("NEW UPGRADED URL:",str(image_url))
            print()
            # Thumbnail olarak src'yi sakla
            if src and src != image_url:
                thumb_url = src
        
        # Eğer ana görsel URL'i yoksa ve video da yoksa boş dön
        if not image_url and not video_url:
            return None

        board_url = await node.evaluate("() => window.location.href")

        return Pin(
            source=self.name,
            board_url=board_url,
            page_url=page_url,
            image_url=image_url,    # Videoyla bu 'poster' (kapak resmi) olur
            thumb_url=thumb_url,
            title=None,
            alt_text=alt,
            media_type=media_type,  # Yeni alan: 'video' veya 'image'
            video_url=video_url     # Yeni alan: Varsa video linki
        )

    def _make_key(self, pin: Pin) -> Optional[str]:
        return pin.page_url or pin.image_url

    async def stream_scroll_and_collect(self, page, max_items: int = 1000) -> List[Pin]:
        # Mevcut çağrınız aynı kalıyor
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