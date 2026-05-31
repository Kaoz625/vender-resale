Working on: Vender Resale — full multi-page storefront with 3,016 products
Last action: Built and pushed complete site rebuild (commit 149788a) — 4 pages + shared JS + 3016-product catalog
Next step: 1) Open vender.nyctailblazers.com and verify all 4 pages load correctly 2) Replace phone placeholder 888-000-0000 in cart.html 3) Sign up for Formspree (formspree.io) if you want form submissions going to a dashboard instead of mailto 4) Test "Add to Cart" → product.html → cart.html → submit order flow end-to-end

Key files:
  - index.html — landing page (category grid, featured products, hero)
  - shop.html — full catalog (3016 products, filter/search/sort/pagination)
  - product.html — product detail (gallery, variants, Add to Cart) — loaded via ?id=N
  - cart.html — cart + order form (mailto-based order submission)
  - js/store.js — shared cart logic, catalog loader, toast, product card renderer
  - data/catalog.json — 3,016 products (2.3MB minified, Shopify CDN images)
  - scripts/scrape_shopify.py — re-run to refresh product catalog from competitor sites
  - scripts/nightly_research.py — cron at 2am, monitors prices + DOCCS compliance

Architecture notes:
  - Static site (Cloudflare Pages) — no backend, no npm
  - Cart lives in localStorage, order goes via mailto
  - catalog.json loads once, cached in sessionStorage between page navigations
  - All product images are Shopify CDN URLs from competitor sites (always present)

Blockers: none — phone number placeholder (888-000-0000) needs real number before going live
