"""
Apartments.com aggregator scraper.

NOTE ON RELIABILITY: Apartments.com actively fights scrapers and changes its
markup often. This parser targets (a) JSON-LD blocks and (b) the data-* card
attributes that have been stable for a while. If the site changes or blocks the
request, fetch() returns None and the pipeline falls back to the property-direct
scraper + last-known history, so the dashboard still renders. Treat selectors
here as the thing most likely to need maintenance.
"""
from __future__ import annotations
import json
import re
from typing import List
from bs4 import BeautifulSoup

from .base import Listing, fetch


def _search_url(area: str, bedrooms: int, max_rent: int) -> str:
    # e.g. https://www.apartments.com/addison-tx/1-bedrooms-under-1600/
    return f"https://www.apartments.com/{area}/{bedrooms}-bedrooms-under-{max_rent}/"


def _parse_cards(html: str, source_tag: str) -> List[Listing]:
    soup = BeautifulSoup(html, "lxml")
    out: List[Listing] = []

    # Strategy 1: JSON-LD (most stable when present)
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        items = data.get("about", []) if isinstance(data, dict) else []
        for it in items if isinstance(items, list) else []:
            name = it.get("name")
            url = it.get("url")
            if name and url:
                out.append(Listing(
                    unit_id=_slug(url), property_name=name, address=name,
                    zip=_zip_from(it.get("address", {})), bedrooms=1,
                    rent=0, rating=None, url=url, source=source_tag,
                ))

    # Strategy 2: placard cards (the visible listing grid)
    for card in soup.select("article.placard, li.mortar-wrapper article"):
        name_el = card.select_one(".property-title, .js-placardTitle")
        price_el = card.select_one(".property-pricing, .price-range")
        link_el = card.select_one("a.property-link, a.js-placard-link")
        rating_el = card.select_one(".reviewStarsRating, [class*='star']")
        addr_el = card.select_one(".property-address")
        if not (name_el and link_el):
            continue
        url = link_el.get("href", "")
        rent = _first_int(price_el.get_text() if price_el else "")
        out.append(Listing(
            unit_id=_slug(url),
            property_name=name_el.get_text(strip=True),
            address=(addr_el.get_text(strip=True) if addr_el else ""),
            zip=_zip_from_text(addr_el.get_text() if addr_el else ""),
            bedrooms=1,
            rent=rent or 0,
            rating=_rating_from(rating_el),
            url=url,
            source=source_tag,
        ))

    # De-dupe by unit_id, keep the row that has a price.
    best = {}
    for l in out:
        if l.unit_id not in best or (l.rent and not best[l.unit_id].rent):
            best[l.unit_id] = l
    return [l for l in best.values() if l.property_name]


def _slug(url: str) -> str:
    m = re.search(r"apartments\.com/([^/?#]+)", url or "")
    return m.group(1) if m else (url or "unknown")[-40:]


def _first_int(text: str) -> int:
    nums = re.findall(r"\$?\s*([0-9][0-9,]{2,})", text or "")
    vals = [int(n.replace(",", "")) for n in nums]
    return min(vals) if vals else 0


def _zip_from(addr: dict) -> str:
    return str(addr.get("postalCode", "")) if isinstance(addr, dict) else ""


def _zip_from_text(text: str) -> str:
    m = re.search(r"\b(7[0-9]{4})\b", text or "")
    return m.group(1) if m else ""


def _rating_from(el) -> float | None:
    if not el:
        return None
    m = re.search(r"([0-5](?:\.[0-9])?)", el.get("aria-label", "") or el.get_text() or "")
    return float(m.group(1)) if m else None


def scrape(areas: List[str], bedrooms: int, max_rent: int) -> List[Listing]:
    results: List[Listing] = []
    for area in areas:
        url = _search_url(area, bedrooms, max_rent)
        html = fetch(url)
        if not html:
            print(f"  [apartments.com] blocked/failed for {area} ({url})")
            continue
        cards = _parse_cards(html, source_tag=f"apartments.com:{area}")
        print(f"  [apartments.com] {area}: parsed {len(cards)} listings")
        results.extend(cards)
    return results
