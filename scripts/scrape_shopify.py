#!/usr/bin/env python3
"""
Shopify product API scraper.
All competitor sites run Shopify — /products.json returns full data:
images, descriptions, variants, prices. No browser needed.
"""

import json
import time
import urllib.request
import urllib.error
import os
from pathlib import Path

OUT = Path(__file__).parent.parent / "research/competitor-prices"
OUT.mkdir(parents=True, exist_ok=True)

SHOPS = {
    "nysapprovedvendor":    "https://nysapprovedvendor.com",
    "emmaspremiumservices": "https://emmaspremiumservices.com",
    "plugforinmates":       "https://plugforinmates.com",
    "cigessentials":        "https://cigessentials.com",
    "skyesthelimit":        "https://skyesthelimitcatalog.com",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def fetch_all_products(base_url: str) -> list[dict]:
    products = []
    page = 1
    while True:
        url = f"{base_url}/products.json?limit=250&page={page}"
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read())
            batch = data.get("products", [])
            if not batch:
                break
            products.extend(batch)
            print(f"  page {page}: {len(batch)} products (total so far: {len(products)})")
            if len(batch) < 250:
                break
            page += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"  Error on page {page}: {e}")
            break
    return products


def normalize(raw: dict, site_name: str, base_url: str) -> dict:
    """Flatten Shopify product into our standard format."""
    variants = raw.get("variants", [])
    images = raw.get("images", [])

    # Price: use lowest variant price
    prices = []
    for v in variants:
        try:
            prices.append(float(v.get("price", 0)))
        except (ValueError, TypeError):
            pass
    price = min(prices) if prices else 0.0
    price_max = max(prices) if prices else 0.0

    # Images: collect all src URLs
    image_urls = [img["src"] for img in images if img.get("src")]

    # Description: strip HTML tags
    body = raw.get("body_html", "") or ""
    import re
    description = re.sub(r"<[^>]+>", " ", body).strip()
    description = re.sub(r"\s+", " ", description)

    # Variants with options
    variant_list = []
    for v in variants:
        variant_list.append({
            "title": v.get("title", ""),
            "price": v.get("price", "0.00"),
            "sku": v.get("sku", ""),
            "available": v.get("available", True),
            "weight": v.get("grams", 0),
        })

    return {
        "id": raw.get("id"),
        "handle": raw.get("handle"),
        "name": raw.get("title", ""),
        "price": price,
        "price_max": price_max,
        "price_display": f"${price:.2f}" if price == price_max else f"${price:.2f}–${price_max:.2f}",
        "description": description[:600] if description else "",
        "image_url": image_urls[0] if image_urls else "",
        "images": image_urls,
        "category": (raw.get("product_type") or "").strip(),
        "tags": raw.get("tags", []) if isinstance(raw.get("tags"), list) else [t.strip() for t in str(raw.get("tags","")).split(",") if t.strip()],
        "variants": variant_list,
        "product_url": f"{base_url}/products/{raw.get('handle','')}",
        "source_site": site_name,
        "available": any(v.get("available", True) for v in variants),
    }


def main():
    all_products = []
    summary = {}

    for slug, base_url in SHOPS.items():
        print(f"\n{'='*50}")
        print(f"Scraping {slug} ({base_url})")
        raw_products = fetch_all_products(base_url)

        normalized = [normalize(p, slug, base_url) for p in raw_products]
        all_products.extend(normalized)

        summary[slug] = {
            "site": slug,
            "base_url": base_url,
            "total": len(normalized),
            "with_images": sum(1 for p in normalized if p["image_url"]),
            "with_descriptions": sum(1 for p in normalized if p["description"]),
            "categories": sorted(set(p["category"] for p in normalized if p["category"])),
        }

        # Save per-site file
        site_path = OUT / f"shopify-{slug}.json"
        with open(site_path, "w") as f:
            json.dump(normalized, f, indent=2)
        print(f"  Saved {len(normalized)} products → {site_path}")

    # Save combined file
    combined_path = OUT / "all-products.json"
    with open(combined_path, "w") as f:
        json.dump(all_products, f, indent=2)

    summary_path = OUT / "shopify-summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*50}")
    print(f"TOTAL: {len(all_products)} products across {len(SHOPS)} sites")
    for slug, s in summary.items():
        print(f"  {slug}: {s['total']} products, {s['with_images']} with images, categories: {s['categories']}")
    print(f"\nAll products → {combined_path}")


if __name__ == "__main__":
    main()
