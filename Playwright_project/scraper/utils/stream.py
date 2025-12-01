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

    # Start at top & disable smooth scroll to reduce long reflow windows
    await page.evaluate("() => { window.scrollTo(0, 0); }")

    # Compute scroll step from viewport height
    viewport_h = await page.evaluate("() => window.innerHeight || 900")
    step_px = max(200, int(viewport_h * step_ratio))

    for _ in range(max_rounds):
        try:
            # 1) Round-scoped live locator for ALL cards that match selector
            loc = page.locator(item_selector)
            count = await loc.count()
        except TargetClosedError:
            break

        counter += count
        print(counter)  # your running debug counter for how many nodes we touched

        # Iterate over each card via a child locator that stays live
        for i in range(count):
            node_loc = loc.nth(i)  # 2) Per-card live locator

            # 2a) Wait up to 800ms for any real media INSIDE the card to be attached.
            #     This mitigates 'NOIMAGE' / missing src/srcset due to lazy mount.
            try:
                media_loc = node_loc.locator("img, picture source, video, [style*='background-image']")
                await media_loc.first.wait_for(state="attached", timeout=800)
            except Exception:
                pass  # if nothing appears, we still try to parse (may be a skeleton/ad)

            # 2b) Bring the card into view so lazy-load can populate attributes
            try:
                await node_loc.scroll_into_view_if_needed(timeout=1000)
            except PWError:
                continue  # card remounted; skip this index
            except Exception:
                pass

            # Small settle time for lazy-loaded attributes (src/srcset/currentSrc)
            await page.wait_for_timeout(100)

            # 2c) Convert to ElementHandle as late as possible (minimize detachment window)
            try:
                node_handle = await node_loc.element_handle()
                if node_handle is None:
                    continue
            except PWError:
                continue
            except Exception:
                continue

            # 3) Let the adapter parse this card into an item (Pin)
            try:
                item = await build_item(node_handle, page)
            except TargetClosedError:
                return out
            except Exception:
                continue

            if item is None:
                continue

            # 4) Dedupe and collect
            key = make_key(item)
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(item)

            if len(out) >= max_items:
                return out

        # 5) Growth check: stop after several rounds with no new items
        if len(seen) <= last_total:
            stagnant += 1
        else:
            stagnant = 0
            last_total = len(seen)

        if stagnant >= stagnant_tolerance:
            break

        # 6) Small scroll step + human-like wait before next round
        await page.evaluate("(y) => window.scrollBy(0, y)", step_px)
        delay = wait_min_ms + random.randint(0, wait_jitter_ms)
        await page.wait_for_timeout(delay)

    return out
