#!/usr/bin/env python3
"""
Competitor scraper for Vender Resale project.
Scrapes products, prices, and image URLs from competitor prison package vendors.
"""

import asyncio
import json
import os
import re
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../docs/competitor-data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SITES = {
    "nysapprovedvendor": {
        "urls": [
            "https://nysapprovedvendor.com/",
            "https://nysapprovedvendor.com/shop/",
            "https://nysapprovedvendor.com/products/",
        ],
        "name": "NYS Approved Vendor",
    },
    "plugforinmates": {
        "urls": [
            "https://plugforinmates.com/",
            "https://plugforinmates.com/collections/all",
            "https://plugforinmates.com/shop/",
        ],
        "name": "Plug For Inmates",
    },
    "cigessentials": {
        "urls": [
            "https://cigessentials.com/",
            "https://cigessentials.com/shop/",
            "https://cigessentials.com/collections/",
        ],
        "name": "CIG Essentials",
    },
    "emmaspremiumservices": {
        "urls": [
            "https://emmaspremiumservices.com/",
            "https://emmaspremiumservices.com/shop/",
            "https://emmaspremiumservices.com/collections/all",
        ],
        "name": "Emma's Premium Services",
    },
}

PRICE_PATTERN = re.compile(r'\$\s*(\d+(?:\.\d{2})?)')
IMG_PATTERN = re.compile(r'!\[([^\]]*)\]\((https?://[^\)]+)\)')


def extract_products_from_markdown(markdown: str, source_url: str) -> list[dict]:
    """Parse products from crawl4ai markdown output."""
    products = []
    lines = markdown.split('\n')

    current_product = {}
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            if current_product.get('name') and current_product.get('price'):
                products.append(current_product)
                current_product = {}
            continue

        # Price detection
        price_match = PRICE_PATTERN.search(line)
        if price_match:
            if current_product.get('name'):
                current_product['price'] = float(price_match.group(1))
                current_product['price_raw'] = line
            else:
                # Price before name — look back
                for prev in reversed(lines[max(0, i-5):i]):
                    prev = prev.strip()
                    if prev and not PRICE_PATTERN.search(prev) and len(prev) > 3:
                        current_product['name'] = prev
                        current_product['price'] = float(price_match.group(1))
                        current_product['price_raw'] = line
                        break

        # Image detection
        img_match = IMG_PATTERN.search(line)
        if img_match:
            if not current_product.get('image'):
                current_product['image_alt'] = img_match.group(1)
                current_product['image_url'] = img_match.group(2)

        # Product name heuristic: short bold lines or heading-style lines
        if line.startswith('##') or line.startswith('###'):
            if current_product.get('name') and current_product.get('price'):
                products.append(current_product)
                current_product = {}
            current_product['name'] = line.lstrip('#').strip()

        current_product['source_url'] = source_url

    if current_product.get('name') and current_product.get('price'):
        products.append(current_product)

    return products


async def crawl_site(slug: str, site_info: dict) -> dict:
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-extensions", "--no-sandbox"],
    )
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_for_images=True,
        page_timeout=30000,
        scan_full_page=True,
        scroll_delay=0.5,
    )

    results = {
        "site": site_info["name"],
        "slug": slug,
        "pages_crawled": [],
        "products": [],
        "raw_markdown": {},
        "errors": [],
    }

    async with AsyncWebCrawler(config=browser_config) as crawler:
        for url in site_info["urls"]:
            try:
                print(f"  Crawling: {url}")
                result = await crawler.arun(url=url, config=run_config)
                if result.success:
                    results["pages_crawled"].append(url)
                    md = result.markdown or ""
                    results["raw_markdown"][url] = md[:8000]  # cap per page
                    products = extract_products_from_markdown(md, url)
                    results["products"].extend(products)
                    print(f"    OK — {len(products)} products found, markdown len={len(md)}")
                else:
                    results["errors"].append({"url": url, "error": result.error_message})
                    print(f"    FAIL: {result.error_message}")
            except Exception as e:
                results["errors"].append({"url": url, "error": str(e)})
                print(f"    EXCEPTION: {e}")

    # Deduplicate products by name
    seen = set()
    deduped = []
    for p in results["products"]:
        key = p.get("name", "").lower().strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(p)
    results["products"] = deduped

    return results


async def main():
    print("=== Vender Resale Competitor Scraper ===\n")

    tasks = [crawl_site(slug, info) for slug, info in SITES.items()]
    all_results = await asyncio.gather(*tasks, return_exceptions=True)

    summary = {}
    for i, (slug, site_info) in enumerate(SITES.items()):
        result = all_results[i]
        if isinstance(result, Exception):
            print(f"\nERROR for {slug}: {result}")
            summary[slug] = {"error": str(result)}
            continue

        out_path = os.path.join(OUTPUT_DIR, f"{slug}.json")
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)

        count = len(result.get("products", []))
        summary[slug] = {
            "name": site_info["name"],
            "products_found": count,
            "pages_crawled": len(result.get("pages_crawled", [])),
            "errors": len(result.get("errors", [])),
            "output": out_path,
        }
        print(f"\n{site_info['name']}: {count} products → {out_path}")

    # Write summary
    summary_path = os.path.join(OUTPUT_DIR, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary written to {summary_path}")


if __name__ == "__main__":
    asyncio.run(main())
