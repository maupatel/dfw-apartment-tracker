"""
DFW Apartment Tracker — pipeline orchestrator.

Run:  python -m scraper.main
Env:  SCRAPER_MOCK=1   -> use sample data, no network (for testing)
      RESEND_API_KEY   -> enables email alerts
      DASHBOARD_URL    -> link included in the alert email
"""
from __future__ import annotations
import os
import sys
import yaml

from .sources import apartments_com, property_direct, mock
from . import filters, storage, notify, report

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")


def load_config() -> dict:
    with open(CONFIG_PATH) as fh:
        return yaml.safe_load(fh)


def collect(cfg: dict):
    """Gather listings from every source; fall back to mock if all live ones fail."""
    if os.environ.get("SCRAPER_MOCK") == "1":
        print("MOCK MODE — using sample data.")
        return mock.scrape(seed=int(os.environ.get("MOCK_SEED", "0")))

    s = cfg["search"]
    listings = []
    print("Scraping aggregator (apartments.com)…")
    listings += apartments_com.scrape(s["areas"], s["bedrooms"], s["max_rent"])
    print("Scraping target properties directly…")
    listings += property_direct.scrape(cfg.get("target_properties", []))

    if not listings:
        print("All live sources returned nothing (blocked?). Falling back to mock so the dashboard still renders.")
        listings = mock.scrape(seed=0)
    return listings


def main():
    cfg = load_config()
    listings = collect(cfg)

    # De-dupe across sources by unit_id (keep the one with a price).
    seen = {}
    for l in listings:
        if l.unit_id not in seen or (l.rent and not seen[l.unit_id].rent):
            seen[l.unit_id] = l
    listings = list(seen.values())

    listings = storage.update(listings)     # record history, compute deltas
    listings = filters.apply(listings, cfg) # safety/rating/price → recommended

    alerts = filters.alert_worthy(listings, cfg)
    print(f"\n{len(listings)} listings, {sum(l.recommended for l in listings)} recommended, "
          f"{len(alerts)} under ${cfg['filters']['alert_max_rent']}.")

    out = report.render(listings, cfg)
    print(f"Dashboard written: {out}")

    if alerts:
        notify.send_alert(alerts, cfg, dashboard_url=os.environ.get("DASHBOARD_URL", ""))

    return 0


if __name__ == "__main__":
    sys.exit(main())
