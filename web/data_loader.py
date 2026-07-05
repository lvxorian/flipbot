import json
import os
from pathlib import Path
from typing import Optional


DATA_FILE = os.getenv("DATA_EXPORT_PATH", "data/data.json")


def load_data() -> dict:
    path = Path(DATA_FILE)
    if not path.exists():
        return {
            "exported_at": None,
            "total_listings": 0,
            "total_opportunities": 0,
            "listings": [],
            "opportunities": [],
            "market_stats": [],
            "last_scan": None,
        }

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_dashboard_stats(data: dict) -> dict:
    listings = data.get("listings", [])
    opportunities = data.get("opportunities", [])
    stats = data.get("market_stats", [])

    prices = [l["price"] for l in listings if l.get("price")]
    areas = [l["area_m2"] for l in listings if l.get("area_m2")]
    price_per_m2_list = []
    for l in listings:
        if l.get("price") and l.get("area_m2"):
            price_per_m2_list.append(l["price"] / l["area_m2"])

    total_value = sum(prices)
    active_listings = len([l for l in listings if l.get("price")])
    avg_price = round(sum(prices) / len(prices)) if prices else 0
    avg_price_m2 = round(sum(price_per_m2_list) / len(price_per_m2_list)) if price_per_m2_list else 0
    avg_area = round(sum(areas) / len(areas), 1) if areas else 0

    last_scan = data.get("last_scan")
    last_scan_time = last_scan.get("finished_at") if last_scan else None

    return {
        "total_listings": len(listings),
        "active_listings": active_listings,
        "total_opportunities": len(opportunities),
        "avg_price": avg_price,
        "avg_price_m2": avg_price_m2,
        "avg_area": avg_area,
        "total_value": total_value,
        "last_scan": last_scan_time,
    }
