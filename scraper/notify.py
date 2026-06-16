"""
Email alerts via Resend (https://resend.com).

Set RESEND_API_KEY in your environment (locally) or as a GitHub Actions secret.
Free tier is plenty for a daily personal alert. The send is best-effort: if the
key is missing or the API errors, we log and continue rather than crash the run.
"""
from __future__ import annotations
import os
from typing import List, Dict
import requests
from .sources.base import Listing


def send_alert(units: List[Listing], cfg: Dict, dashboard_url: str = "") -> bool:
    email_cfg = cfg.get("email", {})
    if not email_cfg.get("enabled") or not units:
        return False

    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print("  [email] RESEND_API_KEY not set — skipping send.")
        return False

    html = _build_html(units, dashboard_url)
    payload = {
        "from": email_cfg.get("from_address", "alerts@example.com"),
        "to": [email_cfg.get("to_address")],
        "subject": f"🏠 {len(units)} apartment(s) under ${cfg['filters']['alert_max_rent']} near Addison/Plano",
        "html": html,
    }
    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload, timeout=20,
        )
        if r.status_code in (200, 201):
            print(f"  [email] sent alert for {len(units)} unit(s).")
            return True
        print(f"  [email] Resend error {r.status_code}: {r.text[:200]}")
    except requests.RequestException as e:
        print(f"  [email] send failed: {e}")
    return False


def _build_html(units: List[Listing], dashboard_url: str) -> str:
    rows = ""
    for u in units:
        chg = ""
        if u.price_change is not None:
            arrow = "▼" if u.price_change < 0 else ("▲" if u.price_change > 0 else "—")
            chg = f"{arrow} ${abs(u.price_change)}"
        flag = " 🆕 JUST LISTED" if u.days_tracked == 1 else (" ⭐ lowest ever" if u.is_lowest_ever else "")
        rows += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #eee"><b>{u.property_name}</b>{flag}<br>
              <span style="color:#666;font-size:12px">{u.address}</span></td>
          <td style="padding:8px;border-bottom:1px solid #eee;font-size:18px"><b>${u.rent}</b><br>
              <span style="color:#888;font-size:12px">{chg}</span></td>
          <td style="padding:8px;border-bottom:1px solid #eee">⭐ {u.rating or '–'}<br>
              <span style="font-size:12px">🛡 {u.safety_score}/10</span></td>
          <td style="padding:8px;border-bottom:1px solid #eee">
              <a href="{u.url}" style="color:#2563eb">View →</a></td>
        </tr>"""
    dash = f'<p><a href="{dashboard_url}">Open full dashboard →</a></p>' if dashboard_url else ""
    return f"""
    <div style="font-family:system-ui,Arial,sans-serif;max-width:640px">
      <h2>Apartments under budget near Addison / Plano</h2>
      <p style="color:#555">A new unit that <b>just got listed</b> is usually at its
      floor price. If one is flagged 🆕, signing same-day is your best shot at the lowest base rent.</p>
      <table style="border-collapse:collapse;width:100%">
        <tr style="text-align:left;background:#f8fafc">
          <th style="padding:8px">Property</th><th style="padding:8px">Rent</th>
          <th style="padding:8px">Rating / Safety</th><th style="padding:8px"></th>
        </tr>{rows}
      </table>
      {dash}
      <p style="color:#999;font-size:12px">Sent by your DFW Apartment Tracker.</p>
    </div>"""
