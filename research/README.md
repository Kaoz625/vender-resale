# Research Folder — Vender Resale

This folder is auto-updated nightly by `scripts/nightly_research.py`.

## Structure

```
research/
├── README.md                     ← this file
├── latest-report.md              ← most recent daily report (overwritten each night)
├── YYYY-MM-DD-daily-report.md    ← dated reports, one per day
├── competitor-prices/
│   ├── latest-{site}.json        ← most recent scrape per site
│   └── YYYY-MM-DD-{site}.json    ← dated snapshots
├── compliance/
│   └── YYYY-MM-DD-disapproved-vendors.pdf  ← saved if DOCCS list changes
├── new-products/
│   └── YYYY-MM-DD-new-products.json        ← newly found compliant products
├── logs/
│   └── cron.log                  ← nightly run log
└── .state.json                   ← internal state (hashes, known products)
```

## What Runs Every Night (2am)

1. **Competitor price scrape** — pulls current products + prices from:
   - Emma's Premium Services
   - NYS Approved Vendor
   - Plug For Inmates
   - CIG Essentials
   - Skye's The Limit

2. **DOCCS compliance check** — detects changes to:
   - Disapproved vendor list PDF (new vendors added?)
   - DOCCS mail/packages page (new rules?)

3. **New product detection** — flags products competitors are selling that:
   - We don't already carry
   - Appear to match Directive 4911 allowed categories
   - Are not in any prohibited category

4. **Daily report** — saved to `research/YYYY-MM-DD-daily-report.md` and `latest-report.md`

## Setup (run once)

```bash
bash scripts/setup_cron.sh
```

## Manual Run

```bash
python3 scripts/nightly_research.py
```

## Compliance Alerts

If the nightly script exits with code 2, the DOCCS disapproved list or rules page has changed.
Check `latest-report.md` immediately and review what changed before sending any more packages.

## Key Docs

- [docs/disapproved-vendor-analysis.md](../docs/disapproved-vendor-analysis.md) — full analysis of why vendors get banned
- [docs/wholesale-suppliers.md](../docs/wholesale-suppliers.md) — wholesale sourcing guide with specific suppliers + pricing
- [docs/directive-4911-compliance.md](../docs/directive-4911-compliance.md) — compliance rules reference
