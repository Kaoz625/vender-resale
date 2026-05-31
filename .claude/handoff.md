Working on: Vender Resale — live on Cloudflare Pages, auto-deploy via GitHub Actions
Last action: Fixed blur (removed grain overlay), wired Formspree, created Pages project, deployed live (commit a0f796d)
Next step:
  1) Add 2 GitHub secrets so auto-deploy works on every push:
     → Go to https://github.com/Kaoz625/vender-resale/settings/secrets/actions
     → Add secret: CLOUDFLARE_API_TOKEN = (value of CLOUDFLARE_WRANGLER_OAUTH from ~/.credentials/api-keys.env)
     → Add secret: CLOUDFLARE_ACCOUNT_ID = 4589ead053bd6785d78f5096068625ba
     → After that, every git push to main auto-deploys within ~30 seconds
  2) Verify vender.nyctailblazers.com loads correctly (DNS may take a few minutes to propagate)
  3) Test order flow: add item → cart.html → submit form → should hit Formspree + send email

Live URLs:
  - https://vender-resale.pages.dev (always works)
  - https://vender.nyctailblazers.com (custom domain, connected)

Key files:
  - index.html / shop.html / product.html / cart.html — the 4 pages
  - js/store.js — shared cart + catalog logic
  - data/catalog.json — 3,016 products with Shopify CDN images
  - .github/workflows/deploy.yml — auto-deploy to Cloudflare Pages on push
  - scripts/nightly_research.py — cron 2am, refreshes prices + DOCCS compliance check

Formspree endpoint: https://formspree.io/f/mvzynowp (orders go here + to vender@nyctailblazers.com)
Cloudflare Pages project: vender-resale (account 4589ead053bd6785d78f5096068625ba)
Blockers: GitHub Actions secrets need to be added manually (30 seconds — see step 1 above)
