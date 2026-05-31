#!/usr/bin/env python3
"""
UPC enrichment script for Vender Resale.

For each product in catalog.json:
  1. Searches Open Food Facts by product name
  2. Gets the UPC/barcode code
  3. Verifies it's a reasonable match
  4. Saves UPC back to catalog.json

With UPCs, product.html can do exact nutrition lookups:
  https://world.openfoodfacts.org/api/v0/product/{upc}.json

Run: python3 scripts/enrich_upcs.py [--limit 500] [--resume]
Expects ~20-40% hit rate (not all products are in OFF database).
"""

import json, time, re, urllib.request, urllib.error
from pathlib import Path
from difflib import SequenceMatcher

ROOT = Path(__file__).parent.parent
CATALOG_PATH = ROOT / "data/catalog.json"
UPC_CACHE_PATH = ROOT / "data/upc-cache.json"

FOOD_TOP_CATS = {
    "Proteins & Meat", "Snacks", "Grocery", "Produce"
}

def clean_name(name: str) -> str:
    """Strip size/weight from product name for better search."""
    name = re.sub(r',?\s*\d+(\.\d+)?\s*(oz|lb|lbs|g|kg|ml|fl oz|count|ct|pk|pack|pieces?)\b.*',
                  '', name, flags=re.IGNORECASE)
    name = re.sub(r'\(.*?\)', '', name)
    name = re.sub(r'\[.*?\]', '', name)
    name = ' '.join(name.split())
    return name.strip()


def name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def search_off(product_name: str) -> dict | None:
    """Query Open Food Facts and return best match with UPC."""
    query = clean_name(product_name)
    encoded = urllib.parse.quote(query)
    url = (f"https://world.openfoodfacts.org/cgi/search.pl"
           f"?search_terms={encoded}&json=1&page_size=5&search_simple=1"
           f"&fields=code,product_name,nutriments,serving_size,quantity,brands")

    req = urllib.request.Request(url, headers={"User-Agent": "VenderResale/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        return None

    products = data.get("products", [])
    if not products:
        return None

    # Find best name match
    best = None
    best_score = 0.0
    for p in products:
        off_name = p.get("product_name") or p.get("abbreviated_product_name") or ""
        score = name_similarity(query, off_name)
        if score > best_score:
            best_score = score
            best = p

    # Require reasonable similarity
    if best_score < 0.35:
        return None

    return best


def extract_nutrition(p: dict) -> dict | None:
    """Extract nutrition facts from an OFF product."""
    n = p.get("nutriments", {})
    if not n:
        return None

    def get(key_serving, key_100g):
        v = n.get(key_serving) or n.get(key_100g)
        return round(float(v), 1) if v is not None else None

    sodium_raw = n.get("sodium_serving") or n.get("sodium_100g")
    sodium_mg = round(float(sodium_raw) * 1000, 0) if sodium_raw else None

    calcium_raw = n.get("calcium_serving") or n.get("calcium_100g")
    calcium_mg = round(float(calcium_raw) * 1000, 0) if calcium_raw else None

    iron_raw = n.get("iron_serving") or n.get("iron_100g")
    iron_mg = round(float(iron_raw) * 1000, 1) if iron_raw else None

    potassium_raw = n.get("potassium_serving") or n.get("potassium_100g")
    potassium_mg = round(float(potassium_raw) * 1000, 0) if potassium_raw else None

    calories = n.get("energy-kcal_serving") or n.get("energy-kcal_100g")

    result = {
        "serving_size": p.get("serving_size") or p.get("quantity") or "See package",
        "calories": round(float(calories), 0) if calories else None,
        "total_fat_g": get("fat_serving", "fat_100g"),
        "saturated_fat_g": get("saturated-fat_serving", "saturated-fat_100g"),
        "trans_fat_g": get("trans-fat_serving", "trans-fat_100g"),
        "cholesterol_mg": get("cholesterol_serving", "cholesterol_100g"),
        "sodium_mg": sodium_mg,
        "total_carbs_g": get("carbohydrates_serving", "carbohydrates_100g"),
        "fiber_g": get("fiber_serving", "fiber_100g"),
        "sugars_g": get("sugars_serving", "sugars_100g"),
        "added_sugars_g": get("added-sugars_serving", "added-sugars_100g"),
        "protein_g": get("proteins_serving", "proteins_100g"),
        "calcium_mg": calcium_mg,
        "iron_mg": iron_mg,
        "potassium_mg": potassium_mg,
        "ingredients": (p.get("ingredients_text") or "")[:300] or None,
        "allergens": p.get("allergens_from_ingredients") or None,
    }

    # Only return if we have at least calories or protein
    if result["calories"] or result["protein_g"]:
        return result
    return None


def main():
    import argparse, urllib.parse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--food-only", action="store_true", default=True,
                        help="Only process food categories (default True)")
    args = parser.parse_args()

    with open(CATALOG_PATH) as f:
        catalog = json.load(f)

    # Load existing UPC cache
    upc_cache = {}
    if UPC_CACHE_PATH.exists() and args.resume:
        with open(UPC_CACHE_PATH) as f:
            upc_cache = json.load(f)
        print(f"Loaded {len(upc_cache)} cached UPCs")

    # Filter to food items only
    if args.food_only:
        targets = [p for p in catalog if p.get("top_category") in FOOD_TOP_CATS]
        print(f"Food products: {len(targets)} of {len(catalog)} total")
    else:
        targets = catalog

    # Skip already processed
    to_process = [p for p in targets if str(p["id"]) not in upc_cache][:args.limit]
    print(f"To process: {len(to_process)} products\n")

    found = 0
    not_found = 0

    for i, product in enumerate(to_process):
        pid = str(product["id"])
        name = product["name"]
        print(f"[{i+1}/{len(to_process)}] {name[:60]}...")

        off_product = search_off(name)

        if off_product:
            upc = off_product.get("code")
            nutrition = extract_nutrition(off_product)
            off_name = off_product.get("product_name", "")
            similarity = name_similarity(clean_name(name), off_name)

            upc_cache[pid] = {
                "product_id": product["id"],
                "product_name": name,
                "upc": upc,
                "off_name": off_name,
                "similarity": round(similarity, 2),
                "nutrition": nutrition,
            }

            if nutrition:
                cal_str = f"{nutrition['calories']} cal" if nutrition.get('calories') else "?"
                print(f"  ✓ UPC: {upc} | {off_name[:40]} (sim={similarity:.2f}) | {cal_str}")
                found += 1
            else:
                print(f"  ~ UPC: {upc} | {off_name[:40]} (no nutrition data)")
        else:
            upc_cache[pid] = {"product_id": product["id"], "product_name": name,
                               "upc": None, "nutrition": None}
            print(f"  ✗ Not found in Open Food Facts")
            not_found += 1

        # Save every 25 products
        if (i + 1) % 25 == 0:
            with open(UPC_CACHE_PATH, "w") as f:
                json.dump(upc_cache, f, indent=2)
            pct = round(found / max(found + not_found, 1) * 100)
            print(f"\n  [saved — {found} found, {not_found} not found so far ({pct}% hit rate)]\n")

        time.sleep(0.4)  # Rate limit OFF API

    # Final save of cache
    with open(UPC_CACHE_PATH, "w") as f:
        json.dump(upc_cache, f, indent=2)

    # Merge UPCs + nutrition back into catalog
    nutrition_count = 0
    upc_count = 0
    cache_by_id = {v["product_id"]: v for v in upc_cache.values()}

    for product in catalog:
        cached = cache_by_id.get(product["id"])
        if cached:
            if cached.get("upc"):
                product["upc"] = cached["upc"]
                upc_count += 1
            if cached.get("nutrition"):
                product["nutrition"] = cached["nutrition"]
                nutrition_count += 1

    with open(CATALOG_PATH, "w") as f:
        json.dump(catalog, f, separators=(",", ":"))

    total_cached = sum(1 for v in upc_cache.values() if v.get("upc"))
    print(f"\n{'='*60}")
    print(f"UPCs found: {upc_count} products now have UPCs")
    print(f"Nutrition facts: {nutrition_count} products now have full nutrition")
    print(f"Total in cache: {total_cached}")
    print(f"Cache saved: {UPC_CACHE_PATH}")
    print(f"Catalog updated: {CATALOG_PATH}")
    print(f"\nRun again with --resume to continue processing remaining products")


if __name__ == "__main__":
    main()
