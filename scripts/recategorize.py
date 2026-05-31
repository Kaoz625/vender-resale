#!/usr/bin/env python3
"""
Two-level categorization:
  top_category  — 8 broad groups (for homepage grid + sidebar top-level)
  category      — specific subcategory (for sidebar drill-down + filtering)

Nuts, seeds, protein powder, jerky → Proteins (not Snacks).
"""
import json, re, os
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

# ── Taxonomy ──────────────────────────────────────────────────────────────────
# top_category → list of subcategories (order = display order in sidebar)
TAXONOMY = {
    "Proteins & Meat": [
        "Beef",
        "Poultry",
        "Pork",
        "Seafood & Fish",
        "Nuts & Seeds",
        "Protein Powder",
        "Jerky & Meat Snacks",
    ],
    "Snacks": [
        "Chips & Crisps",
        "Cookies & Cakes",
        "Candy & Sweets",
        "Crackers",
        "Popcorn",
        "Other Snacks",
    ],
    "Grocery": [
        "Bread & Bakery",
        "Dairy & Cheese",
        "Rice & Grains",
        "Breakfast & Cereal",
        "Beverages",
        "Condiments & Sauces",
        "Canned & Packaged Food",
        "Soup",
    ],
    "Produce": [
        "Fresh Vegetables",
        "Fresh Fruit",
    ],
    "Hygiene & Personal Care": [
        "Soap & Body Wash",
        "Oral Care",
        "Deodorant",
        "Hair Care",
        "Skin Care & Lotion",
        "Feminine Care",
        "Shaving",
    ],
    "Clothing": [
        "Sweatsuits & Sets",
        "Shirts & Tops",
        "Pants & Bottoms",
        "Winter Gear",
        "Socks & Underwear",
        "Footwear",
    ],
    "Bedding & Home": [
        "Blankets & Bedding",
        "Towels",
        "Kitchen & Supplies",
    ],
    "Electronics": [
        "Headphones & Earbuds",
        "Radios",
        "Electronics Accessories",
    ],
    "Other": [
        "Tobacco",
        "Bundles",
        "Books & Cards",
        "Gift Cards",
    ],
}

# Flat list of all subcategories for validation
ALL_SUBCATS = [sub for subs in TAXONOMY.values() for sub in subs]

# subcategory → top_category reverse map
SUBCAT_TO_TOP = {sub: top for top, subs in TAXONOMY.items() for sub in subs}

# ── Raw category → subcategory ────────────────────────────────────────────────
RAW_MAP = {
    "Meat": "Beef", "BEEF": "Beef",
    "PORK": "Pork",
    "TURKEY": "Poultry", "CHICKEN": "Poultry",
    "Fish": "Seafood & Fish", "SEAFOOD": "Seafood & Fish", "seafood": "Seafood & Fish",
    "canned food": "Canned & Packaged Food",
    "Snacks": "Other Snacks", "SNACKS": "Other Snacks", "snacks": "Other Snacks",
    "Potato Chips": "Chips & Crisps",
    "Candy": "Candy & Sweets", "CANDY": "Candy & Sweets", "candy": "Candy & Sweets",
    "Cereal Bars": "Other Snacks",
    "Cookies": "Cookies & Cakes", "Cooies": "Cookies & Cakes",
    "Cake": "Cookies & Cakes", "Cakes": "Cookies & Cakes",
    "Bread": "Bread & Bakery", "BREAD": "Bread & Bakery",
    "Sandwich": "Bread & Bakery",
    "Dairy": "Dairy & Cheese", "CHEESE": "Dairy & Cheese", "cheese": "Dairy & Cheese",
    "Shredded Cheese": "Dairy & Cheese",
    "Rice": "Rice & Grains", "RICE": "Rice & Grains",
    "Instant Oatmeal": "Breakfast & Cereal", "Instant Grits": "Breakfast & Cereal",
    "Hot Cereal": "Breakfast & Cereal", "Cereal": "Breakfast & Cereal",
    "DRINKS": "Beverages", "Drinks": "Beverages", "drinks": "Beverages",
    "Drink Mix": "Beverages", "Juice": "Beverages", "Coffee": "Beverages",
    "Hot Cocoa": "Beverages",
    "CONDIMENTS": "Condiments & Sauces", "SALAD DRESSING": "Condiments & Sauces",
    "Soup": "Soup",
    "Vegetable": "Fresh Vegetables", "VEGETABLES": "Fresh Vegetables",
    "Vegetables": "Fresh Vegetables",
    "Fruit": "Fresh Fruit", "FRUIT": "Fresh Fruit",
    "Apples": "Fresh Fruit", "Grapes": "Fresh Fruit", "Oranges": "Fresh Fruit",
    "Green Pepper": "Fresh Vegetables", "Red Pepper": "Fresh Vegetables",
    "Yellow Pepper": "Fresh Vegetables", "Jalapeño Pepper": "Fresh Vegetables",
    "Yellow Onion": "Fresh Vegetables",
    "PACKAGED FOOD": "Canned & Packaged Food",
    "Food Storage": "Kitchen & Supplies", "Storage": "Kitchen & Supplies",
    "Bar Soap": "Soap & Body Wash", "Baby Oil": "Skin Care & Lotion",
    "Lip Balm": "Skin Care & Lotion",
    "PERSONAL CARE": "Soap & Body Wash", "Personal Care": "Soap & Body Wash",
    "Deodorant": "Deodorant", "Body Lotion": "Skin Care & Lotion",
    "Feminine Wash": "Feminine Care", "Shaving Cream": "Shaving",
    "makeup": "Skin Care & Lotion",
    "Hair Care": "Hair Care", "Shampoo": "Hair Care",
    "CLOTHING": "Sweatsuits & Sets", "clothing": "Sweatsuits & Sets",
    "Sweatsuit": "Sweatsuits & Sets",
    "Sweatsuit w/Hat, Scarf & Gloves Set": "Sweatsuits & Sets",
    "Gentlemen Thermal Set": "Sweatsuits & Sets",
    "Ladies Thermal Set": "Sweatsuits & Sets",
    "Shorts & Polo Shirt Set": "Sweatsuits & Sets",
    "Shorts & Crewneck Tee Set": "Sweatsuits & Sets",
    "Short Sleeve Polo Shirt": "Shirts & Tops",
    "Sweatshirt": "Shirts & Tops",
    "Shorts": "Pants & Bottoms", "Sweatpants": "Pants & Bottoms",
    "Winter Gear": "Winter Gear", "Watch Cap": "Winter Gear",
    "HATS": "Winter Gear", "Wool Gloves": "Winter Gear",
    "Wool Scarf": "Winter Gear", "rain coat": "Winter Gear",
    "LEATHER BELT": "Pants & Bottoms",
    "Ankle Socks": "Socks & Underwear", "Tube Socks": "Socks & Underwear",
    "Wool Socks": "Socks & Underwear", "SOCKS": "Socks & Underwear",
    "Men's Boxer Briefs": "Socks & Underwear",
    "SHOES": "Footwear", "BOOTS": "Footwear", "SLIPPERS": "Footwear",
    "Headphones": "Headphones & Earbuds", "Radio": "Radios",
    "ELECTRONICS": "Headphones & Earbuds",
    "reading glasses": "Electronics Accessories",
    "GLASSES": "Electronics Accessories",
    "Bedding": "Blankets & Bedding", "BEDDING": "Blankets & Bedding",
    "Sheet Set": "Blankets & Bedding",
    "Towels": "Towels", "towels": "Towels", "towels/bedding": "Towels",
    "KITCHEN TOOLS & UTENSILS": "Kitchen & Supplies",
    "TOBACCO": "Tobacco", "BUNDLES": "Bundles",
    "GREETING CARDS": "Books & Cards", "Gift Card": "Gift Cards",
    "f": None,
}

# ── Name keyword rules — checked top to bottom, first match wins ──────────────
NAME_RULES = [
    # Protein powder FIRST (before nuts/snacks)
    (["protein powder", "whey", "casein", "creatine", "mass gainer",
      "pre-workout", "pre workout", "bcaa", "amino acid"], "Protein Powder"),
    # Jerky BEFORE chips/snacks
    (["jerky", "beef stick", "meat stick", "slim jim", "jack link",
      "oberto", "old wisconsin", "pork stick"], "Jerky & Meat Snacks"),
    # Nuts & Seeds BEFORE chips/snacks
    (["almond", "cashew", "pistachio", "pecan", "walnut", "hazelnut",
      "macadamia", "peanut", "mixed nuts", "sunflower seed", "pumpkin seed",
      "nut mix", "trail mix", "mixed seed", "sesame", "chia seed",
      "flaxseed", "hemp seed"], "Nuts & Seeds"),
    # Seafood
    (["tuna", "salmon", "sardine", "shrimp", "crab", "lobster", "clam",
      "oyster", "tilapia", "cod", "catfish", "anchovy", "mackerel",
      "herring", "trout", "halibut", "snapper"], "Seafood & Fish"),
    # Poultry
    (["chicken", "turkey", "poultry", "wing", "rotisserie", "fajita",
      "nugget", "breast", "thigh", "drumstick", "hen"], "Poultry"),
    # Beef
    (["beef", "steak", "brisket", "roast beef", "ground beef",
      "burger", "braised", "meatball", "taco filling", "corned beef",
      "bourguignon", "hereford beef", "shredded beef"], "Beef"),
    # Pork
    (["pork", "bacon", "ham", "sausage", "pepperoni", "chorizo",
      "pulled pork", "ribs", "hot dog", "salami", "luncheon", "spam",
      "pork belly", "pork rind", "chicharron"], "Pork"),
    # Candy
    (["candy", "gummy", "gummi", "lollipop", "m&m", "skittles",
      "starburst", "twizzler", "jolly rancher", "reese", "snicker",
      "twix", "kit kat", "milky way", "butterfinger", "lifesaver",
      "airhead", "swedish fish", "sour patch", "haribo", "trolli",
      "laffy taffy", "nerds", "starbursts"], "Candy & Sweets"),
    # Cookies & Cakes
    (["cookie", "brownie", "muffin", "cake", "wafer", "waffle cookie",
      "danish", "pastry", "croissant", "donut", "twinkie", "little debbie",
      "oreo", "chips ahoy", "nutter butter", "fig newton", "dutch maid",
      "galette", "mousse cake", "butter ring", "biscuit", "shortbread",
      "snickerdoodle", "macaroon"], "Cookies & Cakes"),
    # Chips
    (["chip", "crisp", "corn chip", "tortilla chip", "potato chip",
      "funyun", "cheeto", "dorito", "pringle", "lays", "ruffles",
      "frito", "tostito", "combos"], "Chips & Crisps"),
    # Crackers
    (["cracker", "rice cake", "pretzel", "wheat thin", "cheez-it",
      "goldfish", "ritz", "triscuit", "graham cracker", "matzo"], "Crackers"),
    # Popcorn
    (["popcorn", "act ii", "orville", "smartfood", "boom chicka"], "Popcorn"),
    # Granola/protein bars → Other Snacks
    (["granola bar", "protein bar", "clif bar", "kind bar", "nature valley",
      "lara bar", "rx bar", "quest bar", "fiber one",
      "fruit snack", "fruit roll", "fruit leather",
      "rice krispie treat", "cereal bar", "snack bar"], "Other Snacks"),
    # Bread
    (["bread", "roll", "bun", "wrap", "tortilla", "pita", "bagel",
      "english muffin", "brioche", "sourdough", "rye bread",
      "white bread", "wheat bread", "hoagie"], "Bread & Bakery"),
    # Breakfast
    (["oatmeal", "grits", "cream of wheat", "cereal", "granola",
      "muesli", "pancake", "waffle mix", "instant oat", "maple brown sugar",
      "frosted flakes", "honey bunches", "cheerio", "raisin bran",
      "corn flake", "lucky charm"], "Breakfast & Cereal"),
    # Dairy
    (["cheese", "cheddar", "mozzarella", "parmesan", "swiss", "provolone",
      "american cheese", "cream cheese", "milk", "butter", "yogurt",
      "colby", "pepper jack", "velveeta", "queso", "brie",
      "gouda", "ricotta"], "Dairy & Cheese"),
    # Rice & Grains
    (["rice", "ramen", "noodle", "pasta", "spaghetti", "macaroni",
      "instant rice", "uncle ben", "knorr", "minute rice", "jasmine",
      "basmati", "brown rice", "quinoa", "couscous",
      "bean", "lentil", "chickpea", "black bean"], "Rice & Grains"),
    # Beverages
    (["drink", "juice", "lemonade", "punch", "kool-aid", "gatorade",
      "powerade", "coffee", "tea", "cocoa", "hot chocolate",
      "cappuccino", "instant coffee", "creamer", "water", "soda",
      "crystal light", "tang", "hawaiian punch", "nestea", "lipton",
      "mio", "liquid iv", "propel", "snapple", "arizona"], "Beverages"),
    # Condiments
    (["sauce", "ketchup", "mustard", "mayo", "mayonnaise", "ranch",
      "bbq", "hot sauce", "sriracha", "soy sauce", "vinegar", "relish",
      "salsa", "guacamole", "dressing", "seasoning", "spice",
      "garlic powder", "onion powder", "paprika", "cumin",
      "condiment", "syrup", "honey", "jam", "jelly",
      "peanut butter", "nutella", "hazelnut spread"], "Condiments & Sauces"),
    # Soup
    (["soup", "ramen soup", "chicken noodle soup", "tomato soup",
      "broth", "stock", "chowder", "bisque", "stew broth"], "Soup"),
    # Canned
    (["canned", "can of", "vienna sausage", "potted meat",
      "deviled ham", "ravioli", "spaghettio", "chef boyardee",
      "chili", "stew", "hormel compleats", "ready to eat"], "Canned & Packaged Food"),
    # Produce — Vegetables
    (["potato", "sweet potato", "onion", "pepper", "broccoli",
      "carrot", "celery", "lettuce", "spinach", "kale", "squash",
      "cucumber", "zucchini", "garlic", "vegetable", "tomato",
      "corn", "pea", "green bean", "asparagus", "beet",
      "artichoke", "cauliflower", "cabbage"], "Fresh Vegetables"),
    # Produce — Fruit
    (["apple", "orange", "banana", "grape", "strawberry", "blueberry",
      "mango", "pineapple", "peach", "plum", "melon", "watermelon",
      "avocado", "fruit", "lemon", "lime", "cherry", "raspberry",
      "blackberry", "cantaloupe", "kiwi", "pear"], "Fresh Fruit"),
    # Soap & Hygiene
    (["soap", "body wash", "hand wash", "antibacterial", "sanitizer",
      "freshmint", "freshscent", "dove soap", "irish spring",
      "dial", "ivory soap"], "Soap & Body Wash"),
    # Oral Care
    (["toothpaste", "toothbrush", "mouthwash", "floss", "dental",
      "colgate", "crest", "oral-b", "listerine", "whitening"], "Oral Care"),
    # Deodorant
    (["deodorant", "antiperspirant", "body spray", "cologne", "perfume",
      "speed stick", "old spice", "degree", "secret", "axe",
      "arm & hammer", "ban", "mitchum", "dove deodorant"], "Deodorant"),
    # Hair Care
    (["shampoo", "conditioner", "hair", "wave", "edge", "grease",
      "pomade", "du-rag", "wave cap", "hair spray", "relaxer",
      "curl", "afro", "brush", "comb", "dandruff",
      "head & shoulders", "pantene", "suave", "tresemme",
      "vo5", "garnier", "aussie"], "Hair Care"),
    # Skin Care
    (["lotion", "moisturizer", "cream", "lip balm", "chapstick",
      "petroleum", "vaseline", "cocoa butter", "shea butter",
      "baby oil", "skin care", "sunscreen", "spf", "face wash",
      "cleanser", "aveeno", "lubriderm", "cetaphil",
      "jergens", "nivea", "olay"], "Skin Care & Lotion"),
    # Feminine
    (["feminine", "tampon", "pad", "menstrual", "always", "tampax",
      "stayfree", "carefree"], "Feminine Care"),
    # Shaving
    (["razor", "shave", "shaving cream", "aftershave",
      "gillette", "schick", "barbasol", "edge shave"], "Shaving"),
    # Sweatsuits
    (["sweatsuit", "tracksuit", "jogging suit", "short set",
      "short sleeve set", "polo set", "crewneck set", "thermal set",
      "matching set", "2 piece", "two piece", "pajama"], "Sweatsuits & Sets"),
    # Shirts
    (["shirt", "tee", "t-shirt", "polo", "sweatshirt", "hoodie",
      "crewneck", "long sleeve", "thermal top", "tank top",
      "undershirt", "jersey", "baseball tee"], "Shirts & Tops"),
    # Bottoms
    (["pant", "sweatpant", "jogger", "jean", "short", "gym short",
      "basketball short", "legging", "thermal bottom", "belt",
      "trouser"], "Pants & Bottoms"),
    # Winter gear
    (["beanie", "hat", "cap", "glove", "scarf", "winter", "wool hat",
      "knit hat", "fleece hat", "watch cap", "toboggan",
      "rain jacket", "rain coat", "windbreaker", "earmuff"], "Winter Gear"),
    # Socks & Underwear
    (["sock", "underwear", "boxer", "brief", "trunk", "thong",
      "boyshort", "bra", "sports bra", "panty", "lingerie",
      "thermal underwear"], "Socks & Underwear"),
    # Footwear
    (["shoe", "boot", "sneaker", "slipper", "sandal", "loafer",
      "canvas shoe", "athletic shoe", "tennis shoe", "moccasin",
      "slip-on"], "Footwear"),
    # Electronics
    (["headphone", "earphone", "earbud", "earpiece", "in-ear",
      "wired headset", "wireless earphone", "memory wire",
      "hi-fi", "hifi", "bass earphone"], "Headphones & Earbuds"),
    (["radio", "am/fm", "am fm", "walkman", "cd player",
      "mp3 player", "sangean"], "Radios"),
    (["battery", "charger", "cable", "extension cord",
      "calculator", "watch", "clock", "fan", "alarm",
      "reading glass", "glasses", "magnifier", "flashlight",
      "power strip"], "Electronics Accessories"),
    # Bedding
    (["blanket", "sheet", "pillow", "pillowcase", "comforter",
      "quilt", "bedspread", "fire retardant blanket",
      "fleece blanket", "throw blanket"], "Blankets & Bedding"),
    # Towels
    (["towel", "washcloth", "bath cloth", "hand towel",
      "face cloth"], "Towels"),
    # Kitchen
    (["bowl", "cup", "mug", "spoon", "fork", "knife", "utensil",
      "container", "storage bag", "zip lock", "plastic wrap",
      "aluminum foil", "can opener", "bottle opener",
      "kitchen", "cooking", "microwave safe",
      "cutting board", "colander"], "Kitchen & Supplies"),
    # Tobacco
    (["cigarette", "cigar", "tobacco", "pipe tobacco", "chew",
      "snuff", "newport", "marlboro", "camel", "kool",
      "winston", "pall mall"], "Tobacco"),
    # Bundles
    (["bundle", "combo", "kit", "package deal", "value pack",
      "variety pack", "assortment", "gift set",
      "collection set", "care package"], "Bundles"),
    # Books
    (["book", "bible", "dictionary", "magazine", "novel",
      "workbook", "study guide", "textbook", "dummies",
      "puzzle", "crossword", "coloring book",
      "greeting card", "birthday card", "christmas card"], "Books & Cards"),
]


def categorize(raw_cat, name):
    # 1. Direct raw map
    mapped = RAW_MAP.get(raw_cat.strip())
    if mapped:
        return mapped

    # 2. Name keywords
    name_lower = name.lower()
    for keywords, subcat in NAME_RULES:
        if any(kw in name_lower for kw in keywords):
            return subcat

    # 3. Fallback by raw category hint
    raw_lower = raw_cat.lower()
    if "food" in raw_lower or "snack" in raw_lower:
        for keywords, subcat in NAME_RULES:
            if any(kw in name_lower for kw in keywords):
                return subcat
        return "Canned & Packaged Food"
    if "care" in raw_lower or "hygiene" in raw_lower:
        return "Soap & Body Wash"
    if "cloth" in raw_lower or "wear" in raw_lower:
        return "Sweatsuits & Sets"

    return "Canned & Packaged Food"


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
            subcat = categorize(raw_cat, p.get("name", ""))
            top_cat = SUBCAT_TO_TOP.get(subcat, "Other")

            desc = re.sub(r"\s+", " ", (p.get("description") or "").strip())

            all_products.append({
                "id": uid,
                "handle": p.get("handle", ""),
                "name": p["name"],
                "price": p["price"],
                "price_max": p.get("price_max", p["price"]),
                "image_url": p["image_url"],
                "images": p.get("images", [p["image_url"]])[:3],
                "top_category": top_cat,
                "category": subcat,
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
    top_counts = Counter(p["top_category"] for p in all_products)
    sub_counts = Counter(p["category"] for p in all_products)

    print(f"\nTotal: {len(all_products)} products\n")
    for top, subs in TAXONOMY.items():
        tc = top_counts.get(top, 0)
        if not tc:
            continue
        print(f"  {top} ({tc})")
        for sub in subs:
            sc = sub_counts.get(sub, 0)
            if sc:
                print(f"    └─ {sub}: {sc}")

    # Save catalog
    out = DATA / "catalog.json"
    with open(out, "w") as f:
        json.dump(all_products, f, separators=(",", ":"))
    print(f"\ncatalog.json: {os.path.getsize(out)//1024} KB")

    # Save taxonomy for frontend
    taxonomy_out = []
    for top, subs in TAXONOMY.items():
        tc = top_counts.get(top, 0)
        if not tc:
            continue
        sub_list = [{"name": s, "count": sub_counts.get(s, 0)}
                    for s in subs if sub_counts.get(s, 0)]
        taxonomy_out.append({"name": top, "count": tc, "subcategories": sub_list})

    with open(DATA / "categories.json", "w") as f:
        json.dump(taxonomy_out, f, separators=(",", ":"))
    print(f"categories.json: {len(taxonomy_out)} top-level groups")


if __name__ == "__main__":
    main()
