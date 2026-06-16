"""
Price-history tracking.

This is the core of the "listing-day low" experiment. Every run we append today's
base rent for each unit to data/history.json. From that history we compute:
  - price_change   : today's rent minus yesterday's (negative = it dropped)
  - days_tracked   : how many days we've seen this unit
  - is_lowest_ever : today's rent is the lowest we've ever recorded for it

A brand-new unit (days_tracked == 1) is, by the theory, most likely to be at its
floor price — so those get highlighted on the dashboard as "just listed".
"""
from __future__ import annotations
import json
import os
from datetime import date
from typing import List, Dict
from .sources.base import Listing

HISTORY_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "history.json")


def _load() -> Dict:
    try:
        with open(HISTORY_PATH) as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(hist: Dict) -> None:
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w") as fh:
        json.dump(hist, fh, indent=2, sort_keys=True)


def update(listings: List[Listing]) -> List[Listing]:
    today = date.today().isoformat()
    hist = _load()

    for l in listings:
        if not l.rent:
            continue
        rec = hist.setdefault(l.unit_id, {
            "property_name": l.property_name, "url": l.url, "prices": {},
        })
        prices: Dict[str, int] = rec["prices"]

        # Previous observation (most recent date before today)
        prior_dates = sorted(d for d in prices if d < today)
        prev = prices[prior_dates[-1]] if prior_dates else None

        prices[today] = l.rent
        rec["property_name"] = l.property_name
        rec["url"] = l.url

        all_prices = list(prices.values())
        l.price_change = (l.rent - prev) if prev is not None else None
        l.days_tracked = len(prices)
        l.is_lowest_ever = l.rent <= min(all_prices)
        if l.days_tracked == 1:
            l.alerts = (l.alerts or []) + ["JUST LISTED — likely floor price, act today"]

    _save(hist)
    return listings


def series(unit_id: str) -> Dict[str, int]:
    """Return {date: rent} history for one unit (used for the trend sparkline)."""
    return _load().get(unit_id, {}).get("prices", {})
