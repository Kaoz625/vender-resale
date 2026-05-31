#!/usr/bin/env python3
"""
Perplexity-powered price research for Vender Resale products.
Finds cheapest online prices with direct purchase links.
Run: python3 scripts/price_research.py [--limit 50] [--category "Beef"]

Saves results to research/price-research/YYYY-MM-DD-prices.json
"""
import json, os, sys, time, argparse
from pathlib import Path
from datetime import date
import urllib.request, urllib.error

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "research/price-research"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TODAY = date.today().isoformat()
RESULTS_FILE = DATA_DIR / f"{TODAY}-prices.json"

# Load API key
API_KEY = os.environ.get("PERPLEXITY_API_KEY")
if not API_KEY:
    env_file = Path.home() / ".credentials/api-keys.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("PERPLEXITY_API_KEY="):
                API_KEY = line.split("=", 1)[1].strip().strip('"')
                break

if not API_KEY:
    print("ERROR: No PERPLEXITY_API_KEY found")
    sys.exit(1)


def search_cheapest_price(product_name: str) -> dict:
    """Query Perplexity for cheapest price + buy link for a product."""
    prompt = (
        f'Find the cheapest current online price for this exact product: "{product_name}". '
        f'Search grocery stores, Amazon, Walmart, warehouse clubs (Costco, Sam\'s Club), '
        f'restaurant supply stores, and wholesale distributors. '
        f'Return ONLY a JSON object with these fields: '
        f'{{"cheapest_price": 9.99, "store": "Walmart", "url": "https://...", '
        f'"unit_price": 1.25, "unit": "oz", "notes": "24-pack"}}. '
        f'If not found, return {{"cheapest_price": null, "store": null, "url": null, "notes": "not found"}}. '
        f'No explanation, just the JSON.'
    )

    payload = json.dumps({
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "You are a price comparison tool. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 200,
        "search_recency_filter": "month",
    }).encode()

    req = urllib.request.Request(
        "https://api.perplexity.ai/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read())
        content = result["choices"][0]["message"]["content"].strip()
        # Extract JSON from response
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        return {"cheapest_price": None, "store": None, "url": None, "notes": "parse error"}
    except Exception as e:
        return {"cheapest_price": None, "store": None, "url": None, "notes": str(e)[:100]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50, help="Max products to research")
    parser.add_argument("--category", type=str, default=None, help="Filter by top_category")
    parser.add_argument("--resume", action="store_true", help="Skip already-researched products")
    args = parser.parse_args()

    # Load catalog
    with open(ROOT / "data/catalog.json") as f:
        catalog = json.load(f)

    # Filter by category if specified
    if args.category:
        catalog = [p for p in catalog if
                   args.category.lower() in p.get("top_category", "").lower() or
                   args.category.lower() in p.get("category", "").lower()]
        print(f"Filtered to {len(catalog)} products in '{args.category}'")

    # Load existing results if resuming
    existing = {}
    if args.resume and RESULTS_FILE.exists():
        with open(RESULTS_FILE) as f:
            existing = {r["product_id"]: r for r in json.load(f)}
        print(f"Resuming — {len(existing)} already done")

    results = list(existing.values())
    done_ids = set(existing.keys())

    # Pick top products across categories (spread the limit evenly)
    to_research = [p for p in catalog if p["id"] not in done_ids][:args.limit]

    print(f"\nResearching {len(to_research)} products...")
    print(f"Results will be saved to: {RESULTS_FILE}\n")

    for i, product in enumerate(to_research):
        name = product["name"]
        print(f"[{i+1}/{len(to_research)}] {name[:60]}...")

        price_data = search_cheapest_price(name)

        result = {
            "product_id": product["id"],
            "product_name": name,
            "our_price": product["price"],
            "category": product["category"],
            "top_category": product["top_category"],
            "source_site": product["source"],
            **price_data,
            "margin_if_bought_wholesale": None,
        }

        # Calculate margin if we found a price
        if price_data.get("cheapest_price") and product["price"]:
            wholesale = price_data["cheapest_price"]
            retail = product["price"]
            if wholesale < retail:
                margin = retail - wholesale
                pct = round(margin / retail * 100, 1)
                result["margin_if_bought_wholesale"] = {
                    "margin_dollars": round(margin, 2),
                    "margin_pct": pct,
                    "buy_at": wholesale,
                    "sell_at": retail,
                }
                print(f"  → Buy: ${wholesale:.2f} @ {price_data.get('store','?')} | Sell: ${retail:.2f} | Margin: {pct}%")
            else:
                print(f"  → Sell price ${retail:.2f} ≤ found price ${wholesale:.2f} — check pricing")
        else:
            print(f"  → {price_data.get('notes', 'no data')}")

        results.append(result)

        # Save incrementally every 10 products
        if (i + 1) % 10 == 0:
            with open(RESULTS_FILE, "w") as f:
                json.dump(results, f, indent=2)
            print(f"  [saved {len(results)} results]")

        time.sleep(1.2)  # Rate limit

    # Final save
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)

    # Summary
    found = [r for r in results if r.get("cheapest_price")]
    good_margin = [r for r in found if r.get("margin_if_bought_wholesale") and
                   r["margin_if_bought_wholesale"]["margin_pct"] > 20]
    overpriced = [r for r in found if r.get("cheapest_price") and r.get("our_price") and
                  r["cheapest_price"] >= r["our_price"]]

    print(f"\n{'='*60}")
    print(f"RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Products researched: {len(results)}")
    print(f"Prices found: {len(found)}")
    print(f"Good margin (>20%): {len(good_margin)}")
    print(f"May be overpriced (wholesale ≥ sell): {len(overpriced)}")
    print(f"\nTop margins:")
    good_margin.sort(key=lambda x: x["margin_if_bought_wholesale"]["margin_pct"], reverse=True)
    for r in good_margin[:10]:
        m = r["margin_if_bought_wholesale"]
        print(f"  {r['product_name'][:50]} — buy ${m['buy_at']:.2f} @ {r.get('store','?')}, sell ${m['sell_at']:.2f} ({m['margin_pct']}% margin)")
        if r.get("url"):
            print(f"    → {r['url']}")
    print(f"\nFull results: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
