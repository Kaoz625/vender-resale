Working on: Vender Resale — major session complete
Last action: Final UPC/nutrition batch pushed (commit 90632a7) — 1,597 products with full nutrition facts

## What Was Built This Session
- directive.html: plain-English Directive 4911 guide (allowed/prohibited/package rules)
- Directive 4911 nav link on all pages + official PDF links in footers
- Cart compliance: weight scale (30lb shipment / 40lb food monthly), blocked facilities hard stop, tobacco age-21 checkbox, electronics permit checkbox, receipt notice for items >$30
- UPC enrichment: 1,625 products have verified UPCs, 1,597 have nutrition facts (USDA + Open Food Facts)
- Categorization fixed: word-boundary matching, 0 mislabeled items
- 492 products have weight_oz field for cart weight tracker
- Perplexity price research script — finds cheapest buy links per product
- 100+ Directive 4911 rules documented (see research output)

## Next Directive 4911 Features (prioritized)
1. Clothing color filter — block blue/black/gray/orange from cart
2. Price caps — clothing $90, watch $50, audio $150, headphones $50
3. Quantity caps — blanket max 1, sheets max 2, cigarettes max 2 cartons
4. Deodorant stick-only warning
5. Shoe size tolerance warning (within 1 size)

## CRITICAL MISSING — Revenue Blockers
- PAYMENT PROCESSING — orders go via email only, no checkout
  → Fastest: PayPal button in cart.html
  → Better: Stripe Payment Links
  → Best: Shopify migration
- Phone number in nav
- Policy pages: Refund, Substitution, Shipping Schedule, Privacy, Terms

## Key Credentials
- USDA_API_KEY — value lives ONLY in ~/.credentials/api-keys.env.
  Load it with: set -a; . ~/.credentials/api-keys.env; set +a
  NEVER write the value into this file. This repo is PUBLIC.
- Cloudflare Pages: vender-resale project (account id: see ~/.credentials/api-keys.env)
- Formspree: https://formspree.io/f/mvzynowp

## Live URLs
- https://vender-resale.pages.dev
- https://vender.nyctailblazers.com

## Key Files
- index.html / shop.html / product.html / cart.html / directive.html
- js/store.js, data/catalog.json (3,019 products), data/upc-cache.json
- scripts/enrich_upcs.py, scripts/price_research.py, scripts/nightly_research.py
- .github/workflows/deploy.yml (auto-deploy on push)
