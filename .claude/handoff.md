Working on: Vender Resale — NY prison package vendor storefront + research system
Last action: Rebuilt index.html with 65 real products + prices + images; set up nightly research cron; committed and pushed all work (commit a0279cd)
Next step: 1) Open vender.nyctailblazers.com to verify site looks correct 2) Replace 888-000-0000 placeholder phone in index.html with real number 3) Consider Shopify for real cart/checkout (current uses mailto order flow)
Key files:
  - index.html — full product catalog (65 products, 7 category tabs, mailto order flow)
  - scripts/nightly_research.py — runs at 2am, scrapes competitors, monitors DOCCS compliance
  - docs/disapproved-vendor-analysis.md — full analysis of 65 banned vendors + why each was banned
  - docs/wholesale-suppliers.md — wholesale sourcing guide with specific suppliers + margin data
  - research/ — daily research output folder (auto-populated by cron at 2am)
  - research/README.md — explains the folder structure and what runs nightly
Blockers: Phone number placeholder (888-000-0000) needs to be replaced with real number before going live
