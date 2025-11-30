# Playwright_project/scraper/utils/stream.py

import random
from typing import Awaitable, Callable, List, Optional, Set, TypeVar
from playwright._impl._errors import TargetClosedError, Error as PWError

T = TypeVar("T")

BuildItem = Callable[..., Awaitable[Optional[T]]]   # async: (ElementHandle, page) -> Optional[T]
MakeKey   = Callable[[T], Optional[str]]            # sync: item -> unique key


async def streaming_scroll_and_collect_stepwise(
    page,
    item_selector: str,
    build_item: BuildItem,
    make_key: MakeKey,
    *,
    max_items: int = 1000,
    max_rounds: int = 300,
    step_ratio: float = 0.8,
    stagnant_tolerance: int = 5,
    wait_min_ms: int = 500,
    wait_jitter_ms: int = 500,
) -> List[T]:
    seen: Set[str] = set()
    out: List[T] = []
    stagnant, last_total = 0, 0
    counter = 0

    # Start at top & avoid smooth scrolling (reduces reflow races)
    await page.evaluate("() => { window.scrollTo(0, 0); }")
    try:
        await page.add_style_tag(content="html { scroll-behavior: auto !important; }")
    except Exception:
        pass

    viewport_h = await page.evaluate("() => window.innerHeight || 900")
    step_px = max(200, int(viewport_h * step_ratio))

    for _ in range(max_rounds):
        try:
            # Use a Locator — it re-resolves on every action (resilient to DOM changes)
            loc = page.locator(item_selector)
            count = await loc.count()
        except TargetClosedError:
            break

        counter += count
        print(counter)  # your debug counter

        for i in range(count):
            node_loc = loc.nth(i)

            # Try to bring it into view; ignore if it detaches meanwhile.
            try:
                await node_loc.scroll_into_view_if_needed(timeout=1000)
            except PWError:
                continue
            except Exception:
                pass

            # Tiny settle time for lazy-load
            await page.wait_for_timeout(100)

            # Convert to ElementHandle as late as possible
            try:
                node_handle = await node_loc.element_handle()
                if node_handle is None:
                    continue
            except PWError:
                continue
            except Exception:
                continue

            # Build item (adapter parses selectors off the handle)
            try:
                item = await build_item(node_handle, page)
            except TargetClosedError:
                return out
            except Exception:
                continue

            if item is None:
                continue

            key = make_key(item)
            if not key or key in seen:
                continue

            seen.add(key)
            out.append(item)
            if len(out) >= max_items:
                return out

        # Growth check
        if len(seen) <= last_total:
            stagnant += 1
        else:
            stagnant = 0
            last_total = len(seen)

        if stagnant >= stagnant_tolerance:
            break

        # Small downward step and human-like wait
        await page.evaluate("(y) => window.scrollBy(0, y)", step_px)
        delay = wait_min_ms + random.randint(0, wait_jitter_ms)
        await page.wait_for_timeout(delay)

    return out
