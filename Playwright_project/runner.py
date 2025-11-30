import argparse
import asyncio
import json
from pathlib import Path

from scraper.dispatcher import crawl_board
from scraper.utils.download import download_pins

def parse_args():
    p = argparse.ArgumentParser(description="Multi-site pin crawler")
    p.add_argument("--url", required=True, help="Board/hashtag/listing URL")
    p.add_argument("--max-items", type=int, default=1000, help="Max items to pull")
    p.add_argument("--headless", action="store_true", help="Run headless browser")
    p.add_argument("--storage-state", type=str, default=None,
                   help="Playwright storage_state json (for sites needing login)")
    p.add_argument("--out-json", type=str, default="pins.json", help="Output JSON path")
    p.add_argument("--download-dir", type=str, default=None,
                   help="If set, downloads images to this folder (async)")
    return p.parse_args()

async def main():
    args = parse_args()
    pins = await crawl_board(
        url=args.url,
        max_items=args.max_items,
        headless=args.headless,
        storage_state=args.storage_state
    )

    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump([p.__dict__ for p in pins], f, ensure_ascii=False, indent=2)

    print(f"[OK] Extracted {len(pins)} pins → {args.out_json}")

    if args.download_dir:
        await download_pins(pins, out_dir=args.download_dir)
        print(f"[OK] Downloaded to: {args.download_dir}")

if __name__ == "__main__":
    asyncio.run(main())
