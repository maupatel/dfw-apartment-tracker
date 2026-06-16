"""Common data model + HTTP helper shared by all scraper sources."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional
import time
import requests

# A realistic browser header set. Aggregators block obvious bots, so we look
# like a normal Chrome session. This is best-effort, not bulletproof.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}


@dataclass
class Listing:
    """One bookable unit (or property-level listing)."""
    unit_id: str                 # stable id used for price-history tracking
    property_name: str
    address: str
    zip: str
    bedrooms: int
    rent: int                    # base rent in dollars
    rating: Optional[float]      # review stars out of 5
    url: str
    source: str                  # which scraper produced it
    available_date: Optional[str] = None
    # filled in later by the pipeline:
    safety_score: Optional[float] = None
    price_change: Optional[int] = None       # vs yesterday
    days_tracked: Optional[int] = None
    is_lowest_ever: bool = False
    recommended: bool = False
    alerts: list = field(default_factory=list)

    def dict(self):
        return asdict(self)


def fetch(url: str, retries: int = 3, pause: float = 2.0) -> Optional[str]:
    """GET a page with retries. Returns HTML text or None on failure."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                return resp.text
            # 403/429 → blocked or rate-limited; back off.
            time.sleep(pause * (attempt + 1))
        except requests.RequestException:
            time.sleep(pause * (attempt + 1))
    return None
