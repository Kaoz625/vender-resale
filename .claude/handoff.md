Working on: Vender Resale — competitive analysis complete, Phase 1 improvements queued
Last action: Full competitive analysis of 4 competitor sites (2026-05-31). Report delivered to Markus.

Next step — PRIORITY ORDER:
  1) PAYMENT PROCESSING — site cannot take money (biggest blocker, kills all other work)
     Fastest: Add PayPal checkout button to cart.html
     Better:  Stripe Payment Links — generate per-order, email to customer post-form-submit
     Full:    Migrate to Shopify (all 4 competitors run on Shopify)
  2) Add phone number to nav header (Google Voice takes 5 min — every competitor has one)
  3) Add policy pages: Refund, Substitution, Shipping Schedule, Privacy, Terms of Service
  4) Add DOCCS Inmate Lookup link to cart checkout → doccs.ny.gov
  5) Add "Guaranteed Facility Acceptance or Full Refund" badge to hero + cart

Still-open previous blocker (GitHub Actions auto-deploy):
  → https://github.com/Kaoz625/vender-resale/settings/secrets/actions
  → CLOUDFLARE_API_TOKEN = (from ~/.credentials/api-keys.env → CLOUDFLARE_WRANGLER_OAUTH)
  → CLOUDFLARE_ACCOUNT_ID = 4589ead053bd6785d78f5096068625ba

Live URLs:
  - https://vender-resale.pages.dev (always works)
  - https://vender.nyctailblazers.com (custom domain)

Key files:
  - index.html / shop.html / product.html / cart.html
  - js/store.js — cart + catalog logic
  - data/catalog.json — 3,016 products
  - .github/workflows/deploy.yml — auto-deploy on push
  - scripts/nightly_research.py — 2am cron, price refresh + compliance check

Formspree: https://formspree.io/f/mvzynowp (orders → vender@nyctailblazers.com)
Cloudflare Pages project: vender-resale (account 4589ead053bd6785d78f5096068625ba)

Competitive summary (2026-05-31):
  STRENGTHS: best design, largest catalog (3,016), best product detail pages, nutrition facts
  GAPS: no real payments, no BNPL, no order tracking, no phone, no reviews, no guarantee badge,
        no bundles, no policy pages, no sort/filter, no Rikers section, no blog/SEO content
  Biggest single gap: payment processing — without it nothing converts
  Full prioritized roadmap: ask claude to re-run analysis or see docs/competitors.md
