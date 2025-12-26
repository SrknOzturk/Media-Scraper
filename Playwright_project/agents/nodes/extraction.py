from typing import List
from scraper.adapters.pinterest import PinterestAdapter
from scraper.dispatcher import  pick_adapter
from agents.nodes.navigation import get_page
from agents.state import AgentState


async def extraction_node(state: AgentState):
    # Canlı sayfaya doğrudan erişim [cite: 15]
    pw, browser, context, page = await get_page("auth.json")
    adapter = pick_adapter(state["url"])
    
    # Senin paylaştığın 'streaming_scroll_and_collect_stepwise' içindeki 
    # tek bir 'round' mantığını burada uyguluyoruz
    item_selector = adapter.PIN
    
    # Mevcut görünümdeki node'ları bul
    loc = page.locator(item_selector)
    count = await loc.count()
    
    new_pins = []
    current_seen_keys = {pin.image_url for pin in state["raw_media_urls"]} # Tekilleştirme [cite: 30]

    for i in range(count):
        node_handle = await loc.nth(i).element_handle()
        # build_item senin adapter'ındaki mantığı kullanır [cite: 15]
        pin = await adapter.build_item(node_handle, page) 
        
        if pin and pin.image_url not in current_seen_keys:
            new_pins.append(pin)
            current_seen_keys.add(pin.image_url)

    # Stagnant (durağanlık) kontrolü [cite: 63]
    stagnant_inc = 1 if len(new_pins) == 0 else -state["stagnant_counter"]

    return {
        "raw_media_urls": new_pins, # operator.add ile listeye eklenir
        "stagnant_counter": state["stagnant_counter"] + stagnant_inc
    }