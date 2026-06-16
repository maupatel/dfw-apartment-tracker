# 🏠 DFW Apartment Tracker (Addison / Plano)

Finds cheap, well-rated **1-bedroom** apartments near **Addison & Plano**, tracks
each unit's base rent **day by day**, flags units that **just got listed** (most
likely at their floor price), and **emails you** when something qualifying drops
under your budget. Results publish to a **GitHub Pages dashboard**.

## Why the "sign on listing day" idea works (mostly)

Most large DFW complexes price units with **revenue-management software**
(RealPage *YieldStar*, Rainmaker *LRO*). Like airline/hotel pricing, the base
rent for a given unit + move-in date **changes daily** based on occupancy,
lease-expiration balancing, and demand. A freshly available unit is frequently
posted at its **lowest base rent**, and the quote can creep up day over day. So:

- **Tracking daily is the real edge.** This tool records every unit's price each
  morning, so you can *see* the floor instead of guessing.
- A unit flagged **🆕 JUST LISTED** (first day we've seen it) is your best
  same-day-signing candidate.
- It's a tendency, **not a guarantee** — sometimes prices drop later (slow lease-up,
  end-of-month specials). The dashboard's per-unit trend line shows which is happening.

Sources on the mechanism: ProPublica on YieldStar/RealPage, Apartments.com "why
prices change," RentHop seasonality research.

## What it does

1. Scrapes Apartments.com for 1BR units in the configured areas **plus** any
   specific complexes you list (Neo at Midtown is the built-in proof-of-concept).
2. Records today's base rent into `data/history.json` and computes the daily
   change, days-tracked, and lowest-ever flag.
3. Filters by **price**, **review rating**, and **neighborhood safety score**.
4. Renders `docs/index.html` (the GitHub Pages dashboard).
5. Emails you (via Resend) any recommended unit **under your alert cap** (default $1000).

## Setup

```bash
pip install -r requirements.txt

# Test with no network / no scraping — just sample data:
SCRAPER_MOCK=1 python -m scraper.main
# open docs/index.html in a browser
```

### 1. Configure
Edit `config.yaml`: areas, bedrooms, `alert_max_rent`, `min_rating`,
`min_safety_score`, your target properties, and the `safety_map`.

### 2. Email alerts (Resend)
1. Sign up at https://resend.com (free tier) and create an API key.
2. Verify a sender domain/address and set it as `email.from_address` in `config.yaml`.
3. Locally: `cp .env.example .env` and fill in `RESEND_API_KEY`, then
   `export $(cat .env | xargs)` before running.
4. On GitHub: repo **Settings → Secrets and variables → Actions → New secret**,
   name it `RESEND_API_KEY`.

### 3. GitHub Pages + daily automation
1. Push this folder to a new GitHub repo.
2. **Settings → Pages** → Source: *Deploy from a branch* → branch `main`, folder `/docs`.
3. The workflow in `.github/workflows/daily.yml` runs every morning (~8:15 AM CT),
   commits the updated history + dashboard, and Pages redeploys automatically.
   You can also trigger it manually from the **Actions** tab.

Your dashboard lives at: `https://<your-username>.github.io/<repo>/`

## Plugging in real crime data

The `safety_map` in `config.yaml` is a hand-tuned starter for the Addison/Plano
zips. To make it data-driven, replace the static scores using a free source:

- **FBI Crime Data Explorer API** (agency-level): https://cde.ucr.cjis.gov
- **City of Plano / Dallas open-data crime portals** (incident-level by area)
- Map incidents → zip → a 0–10 score and write it back into `safety_map`.

## ⚠️ Honest caveats

- **Apartments.com/Zillow actively block scrapers and forbid it in their ToS.**
  The aggregator parser is best-effort and **will need maintenance** when their
  markup changes. The property-direct path (single page) is more stable. If
  everything is blocked, the run falls back to sample data so the dashboard still
  builds — check the Actions log to see whether real data came through.
- For a rock-solid feed, consider a licensed API (e.g. RentCast, Realtor/Zillow
  partner APIs) and drop it in as a new file under `scraper/sources/`.
- Always confirm price/availability on the actual listing before applying.

## Project layout

```
config.yaml                 # everything you tune
scraper/
  main.py                   # pipeline orchestrator
  sources/
    base.py                 # Listing model + HTTP helper
    apartments_com.py       # aggregator scraper
    property_direct.py      # per-property scraper (Neo at Midtown PoC)
    mock.py                 # sample data for testing
  filters.py                # price / rating / safety → recommended
  storage.py                # daily price history + listing-day-low logic
  notify.py                 # Resend email alerts
  report.py                 # builds docs/index.html
data/history.json           # committed price history (the dataset)
docs/index.html             # the GitHub Pages dashboard (generated)
.github/workflows/daily.yml # daily cron
```
