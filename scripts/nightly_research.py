#!/usr/bin/env python3
"""
Vender Resale — Nightly Research Script
Runs every night to:
  1. Scrape all competitor sites for current prices + new products
  2. Check DOCCS disapproved vendor list for new additions
  3. Identify new Directive 4911 compliant products competitors are selling
  4. Generate a dated daily report in research/

Designed to run via cron at 2am:
  0 2 * * * /usr/bin/python3 "/Users/markususche/Desktop/Vender Resale/scripts/nightly_research.py" >> "/Users/markususche/Desktop/Vender Resale/research/logs/cron.log" 2>&1
"""

import asyncio
import json
import os
import re
import sys
import hashlib
import urllib.request
import urllib.error
from datetime import date, datetime
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
RESEARCH_DIR = ROOT / "research"
PRICES_DIR = RESEARCH_DIR / "competitor-prices"
COMPLIANCE_DIR = RESEARCH_DIR / "compliance"
NEW_PRODUCTS_DIR = RESEARCH_DIR / "new-products"
LOGS_DIR = RESEARCH_DIR / "logs"
STATE_FILE = RESEARCH_DIR / ".state.json"

TODAY = date.today().isoformat()
NOW = datetime.now().strftime("%Y-%m-%d %H:%M")

for d in [PRICES_DIR, COMPLIANCE_DIR, NEW_PRODUCTS_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Competitor Sites ──────────────────────────────────────────────────────────
COMPETITOR_SITES = {
    "emmaspremiumservices": {
        "name": "Emma's Premium Services",
        "urls": [
            "https://emmaspremiumservices.com/collections/all",
            "https://emmaspremiumservices.com/collections/food-snacks",
            "https://emmaspremiumservices.com/collections/hygiene",
            "https://emmaspremiumservices.com/collections/clothing",
            "https://emmaspremiumservices.com/collections/electronics",
        ],
    },
    "plugforinmates": {
        "name": "Plug For Inmates",
        "urls": [
            "https://plugforinmates.com/collections/all",
            "https://plugforinmates.com/",
        ],
    },
    "nysapprovedvendor": {
        "name": "NYS Approved Vendor",
        "urls": [
            "https://nysapprovedvendor.com/",
            "https://nysapprovedvendor.com/shop/",
        ],
    },
    "cigessentials": {
        "name": "CIG Essentials",
        "urls": [
            "https://cigessentials.com/",
            "https://cigessentials.com/collections/all",
        ],
    },
    "skyesthelimit": {
        "name": "Skye's The Limit",
        "urls": [
            "https://skyesthelimitcatalog.com/",
            "https://skyesthelimitcatalog.com/shop/",
        ],
    },
}

# ── DOCCS Monitoring URLs ─────────────────────────────────────────────────────
DOCCS_DISAPPROVED_URL = "https://doccs.ny.gov/system/files/documents/2026/03/incarcerated-individual-disapproved-package-vendor-list-3-10-2026.pdf"
DOCCS_MAIL_PAGE = "https://doccs.ny.gov/mail-packages"
DIRECTIVE_4911_URL = "https://doccs.ny.gov/system/files/documents/2024/11/4911_0.pdf"

# ── Known Disapproved Vendors (from March 2026 list) ─────────────────────────
KNOWN_DISAPPROVED = {
    "Albany Sport Wear", "All Star Hip Hop Apparel", "American Discount Products",
    "Audio Officialz", "Bakery HNY", "Beauty & Glamour", "Bid Easy, LLC",
    "Bombmissary", "Bookt", "Born Greedy", "Bueno Snackz", "Bug Spray on Paper",
    "Cassette Kingz", "City Jeans", "Crazy Snackz", "Crossroads Trading Comp.",
    "EAJ Packaging", "FelonSpace.com", "Fix it Right", "Flyboy Fashion Apparel",
    "Foreign Entertainment", "Free Inside Services, LLC", "Freedom Foods & Goods",
    "GBK Products & Service", "Great Goods", "Grindz Entertainment",
    "Heartland America", "IGM General Merchandising", "Inmate Shopping Outlet",
    "Inmate Sporting Good", "Julie Camp Treasures", "Kash Kare LLC",
    "K D Services", "KRM Kollel Supermarket", "L&A Products",
    "Lavish Royalties LLC", "Liberty Shop LLC", "Life Trading Center",
    "Lifetime Liberty Group", "Madison Avenue Entertainment Group",
    "Mainline Music Distributors", "Moises Cigar Shop",
    "Music and Gear Outlet", "M&G Outlet", "Nana's Soul Kitchen Wholesale Distribution",
    "Nice & Naughty", "Nu Choice", "NY Food Feast",
    "Original Products Botannical", "Prison Art",
    "Prisoner Legal Help", "Legal Associates LLP",
    "Prisoner Promotions", "Rahle Enterprises", "RAM-NYC", "Rapido Supply",
    "Re-Nu Shoe Repair", "S. Platt Books Inc.", "SHOES4U", "Sneaker Stash",
    "Sounds Good Music LLC", "State Shops NY", "T & W Inc.",
    "TFL Administrative Services", "TNT Boutique", "Triple R",
    "Twenty One-Thirty Six District", "Ujamaa Heir",
    "Underground Kicks & Accessories", "UP NYC", "Uptown Entertainment",
    "Valencia Springer Boutique", "Within Your Reach",
}

# ── Price extraction helpers ──────────────────────────────────────────────────
PRICE_RE = re.compile(r'\$\s*(\d+(?:\.\d{2})?)')
IMG_RE = re.compile(r'!\[([^\]]*)\]\((https?://[^\)]+)\)')
HEADING_RE = re.compile(r'^#{1,4}\s+(.+)')


def extract_products(markdown: str, source_url: str) -> list[dict]:
    products = []
    lines = markdown.split('\n')
    current: dict = {}

    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            if current.get('name') and current.get('price'):
                products.append({**current})
                current = {}
            continue

        heading = HEADING_RE.match(line)
        if heading:
            if current.get('name') and current.get('price'):
                products.append({**current})
            current = {'name': heading.group(1), 'source_url': source_url}
            continue

        price_m = PRICE_RE.search(line)
        if price_m and current.get('name'):
            current['price'] = float(price_m.group(1))
            current['price_raw'] = line

        img_m = IMG_RE.search(line)
        if img_m and not current.get('image_url'):
            current['image_alt'] = img_m.group(1)
            current['image_url'] = img_m.group(2)

    if current.get('name') and current.get('price'):
        products.append(current)

    # Deduplicate
    seen: set = set()
    out = []
    for p in products:
        k = p['name'].lower().strip()
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


# ── crawl4ai scraping ─────────────────────────────────────────────────────────
async def crawl_site(slug: str, info: dict) -> dict:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

    browser_cfg = BrowserConfig(headless=True, verbose=False,
                                extra_args=["--no-sandbox", "--disable-extensions"])
    run_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_for_images=True,
        page_timeout=30000,
        scan_full_page=True,
        scroll_delay=0.5,
    )

    result = {"site": info["name"], "slug": slug, "date": TODAY,
               "products": [], "errors": [], "pages_crawled": []}

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        for url in info["urls"]:
            try:
                r = await crawler.arun(url=url, config=run_cfg)
                if r.success:
                    result["pages_crawled"].append(url)
                    products = extract_products(r.markdown or "", url)
                    result["products"].extend(products)
                    print(f"  [{slug}] {url} → {len(products)} products")
                else:
                    result["errors"].append({"url": url, "error": r.error_message})
                    print(f"  [{slug}] FAIL {url}: {r.error_message}")
            except Exception as e:
                result["errors"].append({"url": url, "error": str(e)})
                print(f"  [{slug}] ERROR {url}: {e}")

    # Deduplicate across pages
    seen: set = set()
    deduped = []
    for p in result["products"]:
        k = p.get('name', '').lower().strip()
        if k and k not in seen:
            seen.add(k)
            deduped.append(p)
    result["products"] = deduped
    return result


async def scrape_all_competitors() -> dict[str, dict]:
    print(f"\n[{NOW}] Scraping {len(COMPETITOR_SITES)} competitor sites...")
    tasks = [crawl_site(slug, info) for slug, info in COMPETITOR_SITES.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    out = {}
    for i, (slug, info) in enumerate(COMPETITOR_SITES.items()):
        r = results[i]
        if isinstance(r, Exception):
            out[slug] = {"site": info["name"], "slug": slug, "date": TODAY,
                          "products": [], "errors": [str(r)]}
        else:
            out[slug] = r
        # Save dated file
        out_path = PRICES_DIR / f"{TODAY}-{slug}.json"
        with open(out_path, "w") as f:
            json.dump(out[slug], f, indent=2)
        # Overwrite latest symlink-style file
        latest_path = PRICES_DIR / f"latest-{slug}.json"
        with open(latest_path, "w") as f:
            json.dump(out[slug], f, indent=2)
    return out


# ── Compliance check ──────────────────────────────────────────────────────────
def check_doccs_updates() -> dict:
    """Download DOCCS mail page and check for changes."""
    report = {"checked_at": NOW, "changes_detected": False, "notes": []}

    try:
        req = urllib.request.Request(DOCCS_MAIL_PAGE,
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
            h = hashlib.md5(content).hexdigest()

        state = load_state()
        prev_hash = state.get("doccs_mail_page_hash")
        if prev_hash and prev_hash != h:
            report["changes_detected"] = True
            report["notes"].append("DOCCS mail/packages page content changed — review immediately")
        elif not prev_hash:
            report["notes"].append("First run — baseline hash stored")
        else:
            report["notes"].append("No changes on DOCCS mail/packages page")

        state["doccs_mail_page_hash"] = h
        save_state(state)

    except Exception as e:
        report["notes"].append(f"Could not fetch DOCCS mail page: {e}")

    # Check disapproved list PDF for changes
    try:
        req = urllib.request.Request(DOCCS_DISAPPROVED_URL,
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            pdf_content = resp.read()
            pdf_hash = hashlib.md5(pdf_content).hexdigest()

        state = load_state()
        prev_pdf = state.get("disapproved_list_hash")
        if prev_pdf and prev_pdf != pdf_hash:
            report["changes_detected"] = True
            report["notes"].append(
                "DISAPPROVED VENDOR LIST PDF HAS CHANGED — download and review new version")
            # Save the new PDF
            pdf_path = COMPLIANCE_DIR / f"{TODAY}-disapproved-vendors.pdf"
            with open(pdf_path, "wb") as f:
                f.write(pdf_content)
            report["notes"].append(f"New PDF saved to {pdf_path}")
        elif not prev_pdf:
            report["notes"].append("Disapproved list baseline hash stored")
        else:
            report["notes"].append("Disapproved vendor list — no changes detected")

        state["disapproved_list_hash"] = pdf_hash
        save_state(state)

    except Exception as e:
        report["notes"].append(f"Could not fetch disapproved vendor PDF: {e}")

    return report


# ── New product analysis ──────────────────────────────────────────────────────
# Items that Directive 4911 explicitly allows (Attachment A summary)
ALLOWED_CATEGORIES = {
    "food": [
        "chips", "crackers", "cookies", "candy", "chocolate", "nuts", "dried fruit",
        "beef jerky", "jerky", "ramen", "instant noodles", "soup", "oatmeal",
        "protein bar", "granola", "coffee", "tea", "hot cocoa", "creamer",
        "peanut butter", "jelly", "jam", "honey", "condiments", "sauce",
        "rice", "pasta", "canned", "tuna", "sardines", "vienna sausage",
        "cereal", "trail mix", "popcorn", "pretzels", "pudding", "gelatin",
        "protein powder", "drink mix", "kool-aid", "lemonade", "instant drink",
        "seasoning", "spice", "salt", "pepper", "oil", "vinegar",
    ],
    "hygiene": [
        "soap", "shampoo", "conditioner", "deodorant", "toothpaste", "toothbrush",
        "floss", "mouthwash", "lotion", "moisturizer", "lip balm", "chapstick",
        "razors", "shaving cream", "aftershave", "cologne", "body spray",
        "feminine hygiene", "pads", "tampons", "nail clippers", "nail file",
        "comb", "brush", "hair grease", "edge control", "wave grease",
        "dandruff shampoo", "body wash", "face wash", "cotton swabs",
    ],
    "clothing": [
        "t-shirt", "sweatshirt", "hoodie", "sweatpants", "socks", "underwear",
        "boxers", "briefs", "thermal", "long underwear", "shorts", "pants",
        "belt", "hat", "beanie", "gloves", "scarf",
    ],
    "shoes": [
        "sneakers", "boots", "slippers", "sandals",
        # NOTE: must check footwear compliance rules — no hollow soles, no air chambers
    ],
    "electronics": [
        "radio", "am/fm radio", "walkman", "cd player", "mp3 player",
        "headphones", "earbuds", "batteries", "extension cord", "power strip",
        "fan", "alarm clock", "calculator", "watch",
    ],
    "stationery": [
        "pen", "pencil", "paper", "notebook", "envelope", "stamp",
        "dictionary", "bible", "book", "magazine",
    ],
    "tobacco": [
        "cigarettes", "cigars", "pipe tobacco",
        # Must have NY State Tax Stamps
    ],
}

PROHIBITED_KEYWORDS = [
    "energy drink", "hot pepper", "marshmallow", "fresh", "homemade",
    "bakery", "restaurant", "deli", "hollow", "platform sole", "air max",
    "pump", "memory foam", "metal shank", "adult", "explicit", "drug",
    "marijuana", "alcohol", "weapon", "knife", "blade",
]


def flag_new_products(competitor_data: dict[str, dict]) -> list[dict]:
    """Find products competitors sell that we don't yet offer and that appear compliant."""
    state = load_state()
    known_products = set(state.get("known_product_names", []))
    new_compliant = []

    for slug, site_data in competitor_data.items():
        for product in site_data.get("products", []):
            name = product.get("name", "").lower().strip()
            if not name or name in known_products:
                continue

            # Check if any prohibited keywords appear
            is_prohibited = any(kw in name for kw in PROHIBITED_KEYWORDS)
            if is_prohibited:
                continue

            # Check if it matches any allowed category
            matched_category = None
            for cat, keywords in ALLOWED_CATEGORIES.items():
                if any(kw in name for kw in keywords):
                    matched_category = cat
                    break

            if matched_category:
                new_compliant.append({
                    "name": product.get("name"),
                    "price": product.get("price"),
                    "image_url": product.get("image_url"),
                    "source_site": site_data["site"],
                    "source_url": product.get("source_url"),
                    "category": matched_category,
                    "date_found": TODAY,
                })
                known_products.add(name)

    state["known_product_names"] = list(known_products)
    save_state(state)
    return new_compliant


# ── State management ──────────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ── Report generation ─────────────────────────────────────────────────────────
def generate_report(competitor_data: dict, compliance: dict, new_products: list) -> str:
    total_products = sum(len(v.get("products", [])) for v in competitor_data.values())
    lines = [
        f"# Vender Resale — Daily Research Report",
        f"**Date:** {TODAY}  ",
        f"**Generated:** {NOW}",
        "",
        "---",
        "",
        "## Compliance Check",
        f"- DOCCS pages checked: {compliance['checked_at']}",
        f"- Changes detected: {'**YES — ACTION REQUIRED**' if compliance['changes_detected'] else 'No'}",
        "",
    ]
    for note in compliance["notes"]:
        lines.append(f"- {note}")

    lines += [
        "",
        "---",
        "",
        f"## Competitor Price Scrape",
        f"**Total products scraped:** {total_products}",
        "",
    ]

    for slug, data in competitor_data.items():
        products = data.get("products", [])
        errors = data.get("errors", [])
        lines.append(f"### {data.get('site', slug)}")
        lines.append(f"- Products found: {len(products)}")
        lines.append(f"- Errors: {len(errors)}")
        if products:
            priced = [p for p in products if p.get("price")]
            if priced:
                prices = [p["price"] for p in priced]
                lines.append(f"- Price range: ${min(prices):.2f} – ${max(prices):.2f}")
                lines.append(f"- Sample products:")
                for p in priced[:5]:
                    lines.append(f"  - {p['name']} — ${p['price']:.2f}")
        lines.append("")

    lines += [
        "---",
        "",
        f"## New Compliant Products Found Today",
        f"**Count:** {len(new_products)}",
        "",
    ]

    if new_products:
        by_cat: dict = {}
        for p in new_products:
            cat = p.get("category", "other")
            by_cat.setdefault(cat, []).append(p)
        for cat, items in sorted(by_cat.items()):
            lines.append(f"### {cat.title()}")
            for item in items:
                price_str = f"${item['price']:.2f}" if item.get("price") else "price unknown"
                lines.append(f"- **{item['name']}** — {price_str} (from {item['source_site']})")
                if item.get("image_url"):
                    lines.append(f"  - Image: {item['image_url']}")
            lines.append("")
    else:
        lines.append("No new compliant products identified today.")
        lines.append("")

    lines += [
        "---",
        "",
        "## Action Items",
    ]

    if compliance["changes_detected"]:
        lines.append("- [ ] **URGENT: Review DOCCS compliance changes — check what changed**")
    if new_products:
        lines.append(f"- [ ] Review {len(new_products)} new compliant products — add to catalog?")
    lines.append("- [ ] Check pricing vs competitors and adjust as needed")
    lines.append("")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    print(f"\n{'='*60}")
    print(f"Vender Resale — Nightly Research — {NOW}")
    print(f"{'='*60}\n")

    # Run compliance check and scraping in parallel
    compliance_task = asyncio.create_task(
        asyncio.to_thread(check_doccs_updates)
    )
    competitor_data = await scrape_all_competitors()
    compliance = await compliance_task

    print(f"\nCompliance check: {compliance['notes']}")

    new_products = flag_new_products(competitor_data)
    print(f"New compliant products found: {len(new_products)}")

    report = generate_report(competitor_data, compliance, new_products)

    # Save dated report
    report_path = RESEARCH_DIR / f"{TODAY}-daily-report.md"
    with open(report_path, "w") as f:
        f.write(report)

    # Overwrite latest report
    latest_path = RESEARCH_DIR / "latest-report.md"
    with open(latest_path, "w") as f:
        f.write(report)

    # Save new products JSON
    if new_products:
        new_path = NEW_PRODUCTS_DIR / f"{TODAY}-new-products.json"
        with open(new_path, "w") as f:
            json.dump(new_products, f, indent=2)

    print(f"\nReport saved to: {report_path}")
    print(f"Latest report: {latest_path}")

    if compliance["changes_detected"]:
        print("\n*** COMPLIANCE CHANGES DETECTED — CHECK IMMEDIATELY ***")
        sys.exit(2)  # Exit code 2 = compliance alert

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
