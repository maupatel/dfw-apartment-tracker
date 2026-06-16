"""Apply price / rating / safety filters and decide what's recommended."""
from __future__ import annotations
from typing import List, Dict
from .sources.base import Listing


def apply(listings: List[Listing], cfg: Dict) -> List[Listing]:
    f = cfg["filters"]
    safety_map = cfg.get("safety_map", {})
    default_safe = float(safety_map.get("default", 5.0))

    for l in listings:
        l.safety_score = float(safety_map.get(l.zip, default_safe))
        reasons = []

        if l.rent and l.rent > f["alert_max_rent"]:
            reasons.append(f"rent ${l.rent} > ${f['alert_max_rent']}")
        if l.rating is not None and l.rating < f["min_rating"]:
            reasons.append(f"rating {l.rating} < {f['min_rating']}")
        if l.safety_score < f["min_safety_score"]:
            reasons.append(f"safety {l.safety_score} < {f['min_safety_score']}")
        if not l.rent:
            reasons.append("no price found")

        l.recommended = len(reasons) == 0
        l.alerts = reasons

    # Sort: recommended first, then cheapest, then safest.
    listings.sort(key=lambda x: (not x.recommended, x.rent or 9_999, -(x.safety_score or 0)))
    return listings


def alert_worthy(listings: List[Listing], cfg: Dict) -> List[Listing]:
    """Units that should trigger an email: recommended AND at/below alert price."""
    cap = cfg["filters"]["alert_max_rent"]
    return [l for l in listings if l.recommended and l.rent and l.rent <= cap]
