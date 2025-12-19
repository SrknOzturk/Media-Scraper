import random
from typing import Awaitable, Callable, List, Optional, Set, TypeVar
from playwright._impl._errors import TargetClosedError, Error as PWError

T = TypeVar("T")

# Type hints for better IDE support
BuildItem = Callable[..., Awaitable[Optional[T]]] 
MakeKey   = Callable[[T], Optional[str]]           

async def streaming_scroll_and_collect_stepwise(
    page,
    item_selector: str,
    build_item: BuildItem,
    make_key: MakeKey,
    *,
    max_items: int = 1000,
    max_rounds: int = 3000,
    step_ratio: float = 0.6,
    stagnant_tolerance: int = 15,
    wait_min_ms: int = 800,
    wait_jitter_ms: int = 1500,
) -> List[T]:
    seen: Set[str] = set()
    out: List[T] = []
    stagnant_counter = 0  
    last_total_found = 0  
    working_on = 0

    # Start at top & disable smooth scroll
    await page.evaluate("() => { window.scrollTo(0, 0); }")

    # Compute scroll step from viewport height
    viewport_h = await page.evaluate("() => window.innerHeight || 900")
    step_px = max(200, int(viewport_h * step_ratio))

    for round_idx in range(max_rounds):
        try:
            # 1) Round-scoped live locator
            loc = page.locator(item_selector)
            count = await loc.count()
        except TargetClosedError:
            break

        print(f"\n--- Round {round_idx} | Detected nodes in view: {count} ---")

        # Iterate over each card in the current view
        for i in range(count):
            working_on += 1
            node_loc = loc.nth(i)

            # 2a) Wait for media attachment
            try:
                media_loc = node_loc.locator("img, picture source, video, [style*='background-image']")
                await media_loc.first.wait_for(state="attached", timeout=800)
            except:
                pass

            # 2b) Convert to ElementHandle
            try:
                node_handle = await node_loc.element_handle()
                if node_handle is None: continue
            except:
                continue

            # 3) Build item via Adapter
            try:
                item = await build_item(node_handle, page)
                if item is None:
                    continue
                
                # 4) Dedupe and collect with ID assignment
                key = make_key(item)
                if not key:
                    continue

                if key in seen:
                    # Find the existing item's ID to report the conflict
                    existing_item = next((x for x in out if make_key(x) == key), None)
                    matched_id = existing_item.id if existing_item else "Unknown"
                    print(f"[DUPE] Node {working_on:03}: Conflicts with ID {matched_id}. Skipping.")
                    continue

                # SUCCESS: Assign sequential ID starting from 0
                item.id = len(out) 
                seen.add(key)
                out.append(item)
                
                print(f"[NEW ] Node {working_on:03}: Assigned ID {item.id} | Saved Total: {len(out)}")

            except TargetClosedError:
                return out
            except Exception as e:
                print(f"[ERR ] Node {working_on:03}: Critical Error -> {e}")
                continue

            if len(out) >= max_items:
                print(f"\n[DONE] Target reached: {len(out)} items collected.")
                return out

        # --- 5) STAGNANT CHECK ---
        if len(out) <= last_total_found:
            stagnant_counter += 1
            print(f"[*] No new unique items this round. Stagnant: {stagnant_counter}/{stagnant_tolerance}")
        else:
            stagnant_counter = 0  
            last_total_found = len(out)

        if stagnant_counter >= stagnant_tolerance:
            print(f"\n[TERMINATE] No new items found for {stagnant_tolerance} rounds. Ending crawl.")
            break

        # 6) Scroll and human-like wait
        await page.evaluate("(y) => window.scrollBy(0, y)", step_px)
        delay = wait_min_ms + random.randint(0, wait_jitter_ms)
        await page.wait_for_timeout(delay)

    return out