from typing import TypedDict, Annotated, List, Dict, Any, Union
import operator
from scraper.adapters.base import Pin

class AgentState(TypedDict):
    prompt: str
    url: str
    # HTML taşımıyoruz, sadece koordinasyon verileri
    raw_media_urls: Annotated[List[Pin], operator.add] 
    stagnant_counter: int # Üst üste kaç tur yeni veri gelmedi?
    round_idx: int        # Kaçıncı kaydırma turundayız?
    is_complete: bool
    error_count: int