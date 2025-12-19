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
            #print("SRCSET:",str(srcset))
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

    # scraper/adapters/pinterest.py içindeki ilgili fonksiyonlar

    async def _build_pin(self, node, page) -> Optional[Pin]:
        # 1) Detay linkini al
        a = await node.query_selector("a")
        href = await a.get_attribute("href") if a else None
        
        page_url = None
        if href:
            page_url = f"https://www.pinterest.com{href}" if href.startswith("/") else href

        # --- VİDEO VE MEDYA TİPİ KONTROLÜ ---
        media_type = "image"
        video_url = None
        
        # Grid içindeki video elementini ara
        video_el = await node.query_selector(self.VIDEO)
        if video_el:
            media_type = "video"
            # Video kaynağını al (genellikle 'src' özniteliğindedir)
            video_url = await video_el.get_attribute("src")

        # --- GÖRSEL ÇEKME (Video olsa bile poster/kapak resmi için img gereklidir) ---
        img = await node.query_selector(self.IMG)
        
        # Eğer ne resim ne video bulunamadıysa atla
        if not img and not video_url:
            return None

        image_url = None
        thumb_url = None
        alt = "Pinterest Media"

        if img:
            srcset = await img.get_attribute("srcset") or await img.get_attribute("data-srcset")
            src = await img.get_attribute("src") or await img.get_attribute("data-src")
            alt = await img.get_attribute("alt") or alt

            # En yüksek kalite resmi al
            image_url = self._largest_from_srcset(srcset) if srcset else src
            image_url = self._try_upscale_pinimg(image_url)
            thumb_url = src
        
        # Eğer resim URL'si bulunamadıysa ve video URL'si de yoksa geçersizdir
        if not image_url and not video_url:
            return None

        return Pin(
            id=0,
            source=self.name,
            board_url=page.url,
            page_url=page_url or image_url, # Benzersiz key için
            image_url=image_url,           # Video durumunda bu 'kapak resmi' olur
            thumb_url=thumb_url,
            title=None,
            alt_text=alt,
            media_type=media_type,         # 'video' veya 'image'
            video_url=video_url            # Varsa video linki, yoksa None
        )

    def _make_key(self, pin: Pin) -> Optional[str]:
        # Bu fonksiyonun sonucunu stream.py içinde kontrol ediyoruz.
        key = pin.page_url or pin.image_url
        #if not key:
            #print("[!] Warning: Could not generate a unique key for this Pin.")
        return key

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
            wait_min_ms=1000,
            wait_jitter_ms=800,
            max_rounds=50
        )