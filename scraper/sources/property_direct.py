"""
Property-direct scraper for specific complexes listed in config.target_properties.

Scraping a single property's own page is more reliable than the big search
aggregators, so this is both the proof-of-concept path (Neo at Midtown) and the
fallback when the aggregator gets blocked. It reads the property's
Apartments.com page and pulls the per-unit pricing table when available.
"""
from __future__ import annotations
import json
import re
from typing import List, Dict
from bs4 import BeautifulSoup

from .base import Listing, fetch


def scrape(targets: List[Dict]) -> List[Listing]:
    out: List[Listing] = []
    for t in targets:
        url = t.get("apartments_url")
        if not url:
            continue
        html = fetch(url)
        if not html:
            print(f"  [property] blocked/failed for {t['name']}")
            continue
        out.extend(_parse_property(html, t))
        print(f"  [property] {t['name']}: parsed {len([l for l in out if l.property_name==t['name']])} unit(s)")
    return out


def _parse_property(html: str, t: Dict) -> List[Listing]:
    soup = BeautifulSoup(html, "lxml")
    name = t["name"]
    zip_ = str(t.get("zip", ""))
    rating = _property_rating(soup)
    units: List[Listing] = []

    # Per-unit pricing rows (1-bed only). Markup: .pricingGridItem / .unitContainer
    for row in soup.select(".pricingGridItem, .unitContainer, [data-beds]"):
        beds = row.get("data-beds")
        text = row.get_text(" ", strip=True)
        if beds is not None:
            try:
                if int(float(beds)) != 1:
                    continue
            except ValueError:
                pass
        elif "1 bed" not in text.lower() and "1 bd" not in text.lower():
            continue
        rent = _first_int(text)
        if not rent:
            continue
        unit_no = (row.get("data-unit") or _unit_no(text) or "u")
        avail = _avail(text)
        units.append(Listing(
            unit_id=f"{_slug(t['apartments_url'])}#{unit_no}",
            property_name=name,
            address=f"{name}, {t.get('city','')} {zip_}",
            zip=zip_, bedrooms=1, rent=rent, rating=rating,
            url=t["apartments_url"], source="property-direct",
            available_date=avail,
        ))

    # Fallback: property-level min 1BR price from the rent summary.
    if not units:
        rent = _summary_1bed_price(soup)
        if rent:
            units.append(Listing(
                unit_id=_slug(t["apartments_url"]),
                property_name=name,
                address=f"{name}, {t.get('city','')} {zip_}",
                zip=zip_, bedrooms=1, rent=rent, rating=rating,
                url=t["apartments_url"], source="property-direct",
            ))
    return units


def _property_rating(soup) -> float | None:
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        agg = data.get("aggregateRating") if isinstance(data, dict) else None
        if isinstance(agg, dict) and agg.get("ratingValue"):
            try:
                return float(agg["ratingValue"])
            except (ValueError, TypeError):
                pass
    el = soup.select_one(".reviewRating, .averageRating")
    if el:
        m = re.search(r"([0-5](?:\.[0-9])?)", el.get_text())
        if m:
            return float(m.group(1))
    return None


def _summary_1bed_price(soup) -> int:
    for blk in soup.select(".rentInfoDetail, .priceBedRangeInfo, .rentRollup"):
        text = blk.get_text(" ", strip=True).lower()
        if "1 bed" in text or "1 bd" in text:
            return _first_int(text)
    return 0


def _first_int(text: str) -> int:
    nums = re.findall(r"\$\s*([0-9][0-9,]{2,})", text or "")
    vals = [int(n.replace(",", "")) for n in nums]
    return min(vals) if vals else 0


def _unit_no(text: str):
    m = re.search(r"(?:Unit|#)\s*([A-Za-z0-9\-]+)", text)
    return m.group(1) if m else None


def _avail(text: str):
    m = re.search(r"(Avail(?:able)?[^.,]*)", text, re.I)
    return m.group(1).strip()[:40] if m else None


def _slug(url: str) -> str:
    m = re.search(r"apartments\.com/([^/?#]+)", url or "")
    return m.group(1) if m else url[-40:]
