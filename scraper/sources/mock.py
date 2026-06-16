"""
Mock source — deterministic sample data.

Used when SCRAPER_MOCK=1 (or as a safety net when every live source is blocked
and there is no history yet) so the dashboard, email, and history logic can be
demoed and tested without hitting any real site.
"""
from __future__ import annotations
import random
from typing import List
from .base import Listing

_SAMPLE = [
    ("Neo at Midtown", "Addison", "75001", 985, 4.2, "https://www.apartments.com/neo-at-midtown-addison-tx/"),
    ("The Mansions at Spring Creek", "Plano", "75093", 1140, 4.5, "https://www.apartments.com/"),
    ("Addison Keller Springs", "Addison", "75001", 970, 3.6, "https://www.apartments.com/"),
    ("Legacy West Residences", "Plano", "75024", 1320, 4.7, "https://www.apartments.com/"),
    ("Prairie Creek Villas", "Plano", "75074", 940, 3.4, "https://www.apartments.com/"),
    ("Vista North Dallas", "Dallas", "75254", 999, 4.1, "https://www.apartments.com/"),
]


def scrape(seed: int = 0) -> List[Listing]:
    rng = random.Random(seed)
    out = []
    for i, (name, city, zip_, base, rating, url) in enumerate(_SAMPLE):
        jitter = rng.choice([-15, -5, 0, 0, 10, 25])  # simulate daily price drift
        out.append(Listing(
            unit_id=f"mock-{i}", property_name=name,
            address=f"{name}, {city} {zip_}", zip=zip_, bedrooms=1,
            rent=base + jitter, rating=rating, url=url, source="mock",
            available_date="Available Now",
        ))
    return out
