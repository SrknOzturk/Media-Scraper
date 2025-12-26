from typing import Dict, Any
from scraper.dispatcher import  pick_adapter
from agents.state import AgentState
from scraper.browser import open_page
import random

# global_browser.py (Singleton Tasarımı)
_browser_instance = None

async def get_page(storage_state):
    global _browser_instance
    if _browser_instance is None:
        # İlk kez başlat ve açık tut
        pw, browser, context, page = await open_page(headless=True, storage_state=storage_state)
        _browser_instance = (pw, browser, context, page)
    return _browser_instance

async def navigation_node(state: AgentState):
    # Singleton üzerinden canlı sayfayı al [cite: 20]
    pw, browser, context, page = await get_page("auth.json")
    url = state["url"] if isinstance(state["url"], str) else state["url"][0]

    try:
        # İlk turda sayfayı aç [cite: 13, 14]
        if state["round_idx"] == 0:
            adapter = pick_adapter(url)
            await adapter.pre_open(page)
            await adapter.navigate_board(page, url)
        
        # Sadece kaydır ve içeriğin yüklenmesini bekle [cite: 13]
        viewport_h = await page.evaluate("() => window.innerHeight || 900")
        step_px = int(viewport_h * 0.6) 
        await page.evaluate(f"window.scrollBy(0, {step_px})")
        
        await page.wait_for_timeout(random.randint(1000, 2000))

        return {
            "round_idx": state["round_idx"] + 1,
            "is_complete": False
        }
    except Exception as e:
        return {"error_count": state["error_count"] + 1}