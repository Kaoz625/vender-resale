#!/usr/bin/env python3
"""
Re-categorize all 3,016 products into specific subcategories.
Uses raw category first, falls back to product name keyword matching.
Outputs a new data/catalog.json.
"""
import json, re, os
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

# ── Proper category taxonomy ──────────────────────────────────────────────────
# These are the final displayed categories (order matters for UI display)
CATEGORIES = [
    "Meat & Proteins",
    "Seafood & Fish",
    "Poultry",
    "Snacks & Chips",
    "Cookies & Cakes",
    "Candy & Sweets",
    "Bread & Bakery",
    "Dairy & Cheese",
    "Rice & Grains",
    "Breakfast & Cereal",
    "Beverages",
    "Condiments & Sauces",
    "Produce & Vegetables",
    "Canned & Packaged Food",
    "Hygiene & Soap",
    "Hair Care",
    "Skin Care & Lotion",
    "Deodorant",
    "Sweatsuits & Sets",
    "Shirts & Tops",
    "Pants & Bottoms",
    "Winter Gear",
    "Socks & Underwear",
    "Footwear",
    "Electronics & Headphones",
    "Bedding & Linens",
    "Towels",
    "Tobacco",
    "Kitchen & Supplies",
    "Bundles",
    "Books & Cards",
    "Gift Cards",
]

# ── Raw category → our category ───────────────────────────────────────────────
RAW_MAP = {
    # Proteins
    "Meat": "Meat & Proteins",
    "BEEF": "Meat & Proteins",
    "PORK": "Meat & Proteins",
    "TURKEY": "Meat & Proteins",
    "CHICKEN": "Poultry",
    "Fish": "Seafood & Fish",
    "SEAFOOD": "Seafood & Fish",
    "seafood": "Seafood & Fish",
    "canned food": "Canned & Packaged Food",
    # Snacks
    "Snacks": "Snacks & Chips",
    "SNACKS": "Snacks & Chips",
    "snacks": "Snacks & Chips",
    "Potato Chips": "Snacks & Chips",
    "Candy": "Candy & Sweets",
    "CANDY": "Candy & Sweets",
    "candy": "Candy & Sweets",
    "Cereal Bars": "Snacks & Chips",
    "Cookies": "Cookies & Cakes",
    "Cooies": "Cookies & Cakes",
    "Cake": "Cookies & Cakes",
    "Cakes": "Cookies & Cakes",
    # Bread
    "Bread": "Bread & Bakery",
    "BREAD": "Bread & Bakery",
    "Sandwich": "Bread & Bakery",
    # Dairy
    "Dairy": "Dairy & Cheese",
    "CHEESE": "Dairy & Cheese",
    "cheese": "Dairy & Cheese",
    "Shredded Cheese": "Dairy & Cheese",
    # Grains
    "Rice": "Rice & Grains",
    "RICE": "Rice & Grains",
    "Instant Oatmeal": "Breakfast & Cereal",
    "Instant Grits": "Breakfast & Cereal",
    "Hot Cereal": "Breakfast & Cereal",
    "Cereal": "Breakfast & Cereal",
    # Beverages
    "DRINKS": "Beverages",
    "Drinks": "Beverages",
    "drinks": "Beverages",
    "Drink Mix": "Beverages",
    "Juice": "Beverages",
    "Coffee": "Beverages",
    "Hot Cocoa": "Beverages",
    # Condiments
    "CONDIMENTS": "Condiments & Sauces",
    "SALAD DRESSING": "Condiments & Sauces",
    "Soup": "Canned & Packaged Food",
    # Produce
    "Vegetable": "Produce & Vegetables",
    "VEGETABLES": "Produce & Vegetables",
    "Vegetables": "Produce & Vegetables",
    "Fruit": "Produce & Vegetables",
    "FRUIT": "Produce & Vegetables",
    "Apples": "Produce & Vegetables",
    "Grapes": "Produce & Vegetables",
    "Oranges": "Produce & Vegetables",
    "Green Pepper": "Produce & Vegetables",
    "Red Pepper": "Produce & Vegetables",
    "Yellow Pepper": "Produce & Vegetables",
    "Jalapeño Pepper": "Produce & Vegetables",
    "Yellow Onion": "Produce & Vegetables",
    # Packaged food
    "PACKAGED FOOD": "Canned & Packaged Food",
    "Food Storage": "Kitchen & Supplies",
    "Storage": "Kitchen & Supplies",
    # Hygiene
    "Bar Soap": "Hygiene & Soap",
    "Baby Oil": "Skin Care & Lotion",
    "Lip Balm": "Skin Care & Lotion",
    "PERSONAL CARE": "Hygiene & Soap",
    "Personal Care": "Hygiene & Soap",
    "Deodorant": "Deodorant",
    "Body Lotion": "Skin Care & Lotion",
    "Feminine Wash": "Hygiene & Soap",
    "Shaving Cream": "Hygiene & Soap",
    "makeup": "Skin Care & Lotion",
    # Hair
    "Hair Care": "Hair Care",
    "Shampoo": "Hair Care",
    # Clothing
    "CLOTHING": "Sweatsuits & Sets",
    "clothing": "Sweatsuits & Sets",
    "Sweatsuit": "Sweatsuits & Sets",
    "Sweatsuit w/Hat, Scarf & Gloves Set": "Sweatsuits & Sets",
    "Gentlemen Thermal Set": "Sweatsuits & Sets",
    "Ladies Thermal Set": "Sweatsuits & Sets",
    "Shorts & Polo Shirt Set": "Sweatsuits & Sets",
    "Shorts & Crewneck Tee Set": "Sweatsuits & Sets",
    "Short Sleeve Polo Shirt": "Shirts & Tops",
    "Sweatshirt": "Shirts & Tops",
    "Shorts": "Pants & Bottoms",
    "Sweatpants": "Pants & Bottoms",
    "Winter Gear": "Winter Gear",
    "Watch Cap": "Winter Gear",
    "HATS": "Winter Gear",
    "Wool Gloves": "Winter Gear",
    "Wool Scarf": "Winter Gear",
    "rain coat": "Winter Gear",
    "LEATHER BELT": "Pants & Bottoms",
    # Socks & Underwear
    "Ankle Socks": "Socks & Underwear",
    "Tube Socks": "Socks & Underwear",
    "Wool Socks": "Socks & Underwear",
    "SOCKS": "Socks & Underwear",
    "Men's Boxer Briefs": "Socks & Underwear",
    # Footwear
    "SHOES": "Footwear",
    "BOOTS": "Footwear",
    "SLIPPERS": "Footwear",
    # Electronics
    "Headphones": "Electronics & Headphones",
    "Radio": "Electronics & Headphones",
    "ELECTRONICS": "Electronics & Headphones",
    "reading glasses": "Electronics & Headphones",
    "GLASSES": "Electronics & Headphones",
    # Bedding
    "Bedding": "Bedding & Linens",
    "BEDDING": "Bedding & Linens",
    "Sheet Set": "Bedding & Linens",
    "Towels": "Towels",
    "towels": "Towels",
    "towels/bedding": "Towels",
    # Misc
    "KITCHEN TOOLS & UTENSILS": "Kitchen & Supplies",
    "TOBACCO": "Tobacco",
    "BUNDLES": "Bundles",
    "GREETING CARDS": "Books & Cards",
    "Gift Card": "Gift Cards",
    "f": None,  # junk
}

# ── Keyword rules for name-based categorization ───────────────────────────────
# Checked in order — first match wins
NAME_RULES = [
    # Seafood
    (["tuna", "salmon", "sardine", "shrimp", "crab", "lobster", "clam", "oyster",
      "tilapia", "cod", "catfish", "anchovy", "mackerel", "herring"], "Seafood & Fish"),
    # Poultry
    (["chicken", "turkey", "poultry", "wing", "rotisserie", "fajita", "nugget",
      "breast", "thigh", "drumstick"], "Poultry"),
    # Meat & Proteins
    (["beef", "steak", "pork", "ribs", "rib", "bacon", "ham", "sausage", "pepperoni",
      "brisket", "pulled pork", "chorizo", "hot dog", "salami", "jerky", "meat",
      "burger", "meatball", "ground beef", "roast", "luncheon", "spam",
      "taco filling", "braised", "sous vide", "hereford", "bourguignon"], "Meat & Proteins"),
    # Seafood
    (["fish", "seafood", "shrimp", "crab", "lobster"], "Seafood & Fish"),
    # Candy
    (["candy", "gummy", "gummi", "lollipop", "chocolate bar", "m&m", "skittles",
      "starburst", "nerves", "twizzler", "jolly rancher", "reese", "snicker",
      "twix", "kit kat", "milky way", "butterfinger", "lifesaver", "airhead",
      "swedish fish", "sour patch", "haribo", "trolli"], "Candy & Sweets"),
    # Cookies & Cakes
    (["cookie", "biscuit", "brownie", "muffin", "cake", "wafer", "waffle cookie",
      "danish", "pastry", "croissant", "donut", "twinkie", "little debbie",
      "oreo", "chips ahoy", "nutter butter", "fig newton", "dutch maid",
      "galette", "mousse cake", "butter ring"], "Cookies & Cakes"),
    # Snacks & Chips
    (["chip", "crisp", "pretzel", "popcorn", "cracker", "rice cake", "pork rind",
      "trail mix", "mixed nuts", "sunflower seed", "pumpkin seed", "pistachios",
      "cashew", "almond", "peanut", "snack", "granola bar", "protein bar",
      "fruit snack", "fruit roll", "slim jim", "beef stick", "meat stick",
      "pork skin", "chicharron", "funyun", "combos", "chex mix",
      "lance", "goldfish", "cheez-it", "wheat thin"], "Snacks & Chips"),
    # Bread & Bakery
    (["bread", "roll", "bun", "wrap", "tortilla", "pita", "bagel", "english muffin",
      "croissant", "hoagie", "sub roll", "brioche", "sourdough", "rye", "wheat bread",
      "white bread"], "Bread & Bakery"),
    # Breakfast & Cereal
    (["oatmeal", "grits", "cream of wheat", "cereal", "granola", "muesli",
      "pancake", "waffle mix", "breakfast", "frosted flakes", "honey bunches",
      "cheerio", "raisin bran", "corn flake", "instant oat", "maple brown sugar"], "Breakfast & Cereal"),
    # Dairy & Cheese
    (["cheese", "cheddar", "mozzarella", "parmesan", "swiss", "provolone",
      "american cheese", "cream cheese", "milk", "butter", "yogurt", "dairy",
      "colby", "pepper jack", "velveeta", "queso"], "Dairy & Cheese"),
    # Rice & Grains
    (["rice", "ramen", "noodle", "pasta", "spaghetti", "macaroni", "instant rice",
      "uncle ben", "knorr", "minute rice", "jasmine", "basmati", "brown rice",
      "quinoa", "couscous", "bean", "lentil"], "Rice & Grains"),
    # Beverages
    (["drink", "juice", "lemonade", "punch", "kool-aid", "gatorade", "powerade",
      "coffee", "tea", "cocoa", "hot chocolate", "cappuccino", "instant coffee",
      "creamer", "water", "beverage", "soda", "energy", "crystal light",
      "tang", "hawaiian punch", "nestea", "lipton", "mio", "liquid iv"], "Beverages"),
    # Condiments & Sauces
    (["sauce", "ketchup", "mustard", "mayo", "mayonnaise", "ranch", "bbq",
      "hot sauce", "sriracha", "soy sauce", "vinegar", "relish", "pickle",
      "salsa", "guacamole", "dressing", "seasoning", "spice", "salt",
      "pepper", "garlic powder", "onion powder", "paprika", "cumin",
      "condiment", "oil", "honey", "syrup", "jam", "jelly", "peanut butter"], "Condiments & Sauces"),
    # Canned & Packaged
    (["soup", "chili", "stew", "broth", "stock", "canned", "can of", "vienna sausage",
      "corned beef", "potted meat", "deviled ham", "ravioli", "spaghettio",
      "chef boyardee"], "Canned & Packaged Food"),
    # Produce
    (["apple", "orange", "banana", "grape", "strawberry", "blueberry", "mango",
      "pineapple", "peach", "plum", "melon", "watermelon", "avocado",
      "tomato", "potato", "sweet potato", "onion", "pepper", "broccoli",
      "carrot", "celery", "lettuce", "spinach", "kale", "squash",
      "cucumber", "zucchini", "garlic", "vegetable", "produce", "fruit"], "Produce & Vegetables"),
    # Hygiene
    (["soap", "body wash", "hand wash", "antibacterial", "sanitizer",
      "toothpaste", "toothbrush", "mouthwash", "floss", "dental",
      "feminine", "tampon", "pad", "razor", "shave", "shaving",
      "nail clip", "nail file", "cotton swab", "q-tip", "hygiene",
      "freshmint", "freshscent", "colgate", "crest", "oral-b"], "Hygiene & Soap"),
    # Hair
    (["shampoo", "conditioner", "hair", "wave", "edge", "grease", "pomade",
      "du-rag", "wave cap", "hair spray", "relaxer", "curl", "afro",
      "brush", "comb", "dandruff", "head & shoulders", "pantene",
      "suave", "dove shampoo"], "Hair Care"),
    # Skin Care
    (["lotion", "moisturizer", "cream", "lip balm", "chapstick", "petroleum",
      "vaseline", "cocoa butter", "shea butter", "baby oil", "skin care",
      "sunscreen", "spf", "face wash", "cleanser", "toner", "serum",
      "aveeno", "lubriderm", "cetaphil", "jergens"], "Skin Care & Lotion"),
    # Deodorant
    (["deodorant", "antiperspirant", "body spray", "cologne", "perfume",
      "speed stick", "old spice", "degree", "secret", "axe", "arm & hammer",
      "ban", "sure", "mitchum", "dove deodorant"], "Deodorant"),
    # Sweatsuits & Sets
    (["sweatsuit", "tracksuit", "jogging suit", "short set", "short sleeve set",
      "polo set", "crewneck set", "thermal set", "pajama", "sleep set",
      "matching set", "2 piece", "two piece"], "Sweatsuits & Sets"),
    # Shirts & Tops
    (["shirt", "tee", "t-shirt", "polo", "sweatshirt", "hoodie", "crewneck",
      "long sleeve", "thermal top", "tank top", "undershirt",
      "jersey", "baseball tee"], "Shirts & Tops"),
    # Pants & Bottoms
    (["pant", "sweatpant", "jogger", "jean", "short", "gym short",
      "basketball short", "brief", "boxer", "underwear bottom",
      "legging", "thermal bottom", "belt"], "Pants & Bottoms"),
    # Winter Gear
    (["beanie", "hat", "cap", "glove", "scarf", "winter", "wool",
      "knit", "fleece hat", "watch cap", "toboggan", "thermal",
      "rain jacket", "rain coat", "windbreaker"], "Winter Gear"),
    # Socks & Underwear
    (["sock", "underwear", "boxer", "brief", "trunk", "thong",
      "boyshort", "bra", "sports bra", "panty", "lingerie"], "Socks & Underwear"),
    # Footwear
    (["shoe", "boot", "sneaker", "slipper", "sandal", "loafer",
      "canvas shoe", "athletic shoe", "tennis shoe", "moccasin"], "Footwear"),
    # Electronics
    (["headphone", "earphone", "earbud", "earpiece", "radio", "mp3",
      "speaker", "battery", "charger", "cable", "extension cord",
      "calculator", "watch", "clock", "fan", "reading glass",
      "glasses", "magnifier", "clear", "in-ear", "wired"], "Electronics & Headphones"),
    # Bedding
    (["blanket", "sheet", "pillow", "pillowcase", "comforter", "quilt",
      "bedspread", "mattress", "fire retardant blanket", "fleece blanket"], "Bedding & Linens"),
    # Towels
    (["towel", "washcloth", "bath cloth", "hand towel"], "Towels"),
    # Tobacco
    (["cigarette", "cigar", "tobacco", "pipe", "chew", "snuff",
      "newport", "marlboro", "camel", "kool", "winston"], "Tobacco"),
    # Kitchen
    (["bowl", "cup", "mug", "spoon", "fork", "knife", "utensil",
      "container", "storage", "bag", "zip", "plastic wrap",
      "aluminum foil", "can opener", "bottle opener",
      "kitchen", "cooking", "microwave safe"], "Kitchen & Supplies"),
    # Bundles
    (["bundle", "combo", "kit", "package deal", "value pack",
      "variety pack", "assortment", "gift set", "collection set"], "Bundles"),
    # Books
    (["book", "bible", "dictionary", "magazine", "novel", "workbook",
      "study guide", "textbook", "dummies", "puzzle", "crossword",
      "greeting card", "birthday card"], "Books & Cards"),
]


def categorize(raw_cat: str, name: str) -> str:
    # 1. Try direct raw category map
    mapped = RAW_MAP.get(raw_cat.strip())
    if mapped:
        return mapped

    # 2. For generic/empty cats — use product name keywords
    name_lower = name.lower()
    for keywords, category in NAME_RULES:
        if any(kw in name_lower for kw in keywords):
            return category

    # 3. Still generic categories — try raw cat partial match
    raw_lower = raw_cat.lower()
    if "food" in raw_lower or "snack" in raw_lower:
        # Try name keywords more aggressively
        for keywords, category in NAME_RULES:
            if any(kw in name_lower for kw in keywords):
                return category
        return "Canned & Packaged Food"
    if "care" in raw_lower or "hygiene" in raw_lower:
        return "Hygiene & Soap"
    if "cloth" in raw_lower or "wear" in raw_lower:
        return "Sweatsuits & Sets"

    return "Canned & Packaged Food"  # sensible default for unidentified food items


def main():
    SOURCES = ["nysapprovedvendor", "emmaspremiumservices", "cigessentials"]
    all_products = []
    uid = 0
    seen_keys = set()

    for slug in SOURCES:
        fpath = ROOT / "research/competitor-prices" / f"shopify-{slug}.json"
        if not fpath.exists():
            continue
        with open(fpath) as f:
            products = json.load(f)

        for p in products:
            if not p.get("image_url") or not p.get("price"):
                continue
            key = (p["name"].lower().strip(), slug)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            raw_cat = (p.get("category") or "").strip()
            category = categorize(raw_cat, p.get("name", ""))

            desc = (p.get("description") or "").strip()
            desc = re.sub(r"\s+", " ", desc)

            all_products.append({
                "id": uid,
                "handle": p.get("handle", ""),
                "name": p["name"],
                "price": p["price"],
                "price_max": p.get("price_max", p["price"]),
                "image_url": p["image_url"],
                "images": p.get("images", [p["image_url"]])[:3],
                "category": category,
                "source": slug,
                "description": desc[:250],
                "variants": [
                    {"title": v["title"], "price": v["price"]}
                    for v in p.get("variants", [])
                    if v.get("title") and v["title"] != "Default Title"
                ][:6],
            })
            uid += 1

    # Stats
    cat_counts = Counter(p["category"] for p in all_products)
    print(f"\nTotal products: {len(all_products)}")
    print("\nCategory breakdown:")
    for cat in CATEGORIES:
        count = cat_counts.get(cat, 0)
        if count:
            print(f"  {count:4d}  {cat}")
    uncategorized = [c for c in cat_counts if c not in CATEGORIES]
    for c in uncategorized:
        print(f"  {cat_counts[c]:4d}  *** UNMAPPED: {c}")

    # Save
    out = DATA / "catalog.json"
    with open(out, "w") as f:
        json.dump(all_products, f, separators=(",", ":"))
    print(f"\nSaved {len(all_products)} products → {out}")
    print(f"File size: {os.path.getsize(out)/1024:.0f} KB")

    # Save category list for the frontend
    cat_list = [
        {"name": cat, "count": cat_counts.get(cat, 0)}
        for cat in CATEGORIES
        if cat_counts.get(cat, 0) > 0
    ]
    with open(DATA / "categories.json", "w") as f:
        json.dump(cat_list, f, separators=(",", ":"))
    print(f"Categories with products: {len(cat_list)}")


if __name__ == "__main__":
    main()
