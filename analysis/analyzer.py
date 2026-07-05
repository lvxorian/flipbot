import statistics
from typing import Optional

from scraper.database import (
    get_connection,
    get_listings_for_stats,
    get_median_price_per_m2,
    save_market_stats,
    save_opportunity,
)
from scraper.config import settings


def calculate_market_stats(
    db_path: str,
    location: str | None = None,
    condition: str | None = None,
) -> dict | None:
    conn = get_connection(db_path)
    try:
        listings = get_listings_for_stats(conn, location, condition)
        if len(listings) < 3:
            return None

        prices_per_m2 = [l["price"] / l["area_m2"] for l in listings]

        avg = statistics.mean(prices_per_m2)
        median = statistics.median(prices_per_m2)
        min_val = min(prices_per_m2)
        max_val = max(prices_per_m2)

        loc_key = location or "vše"
        cond_key = condition or "vše"
        save_market_stats(conn, loc_key, cond_key, avg, median, min_val, max_val, len(listings))

        return {
            "location": loc_key,
            "condition": cond_key,
            "avg_price_m2": round(avg, 2),
            "median_price_m2": round(median, 2),
            "min_price_m2": round(min_val, 2),
            "max_price_m2": round(max_val, 2),
            "sample_count": len(listings),
        }
    finally:
        conn.close()


def detect_opportunities(
    db_path: str,
    threshold: float | None = None,
) -> list[dict]:
    conn = get_connection(db_path)
    opportunities = []
    threshold = threshold or settings.DISCOUNT_THRESHOLD

    try:
        active_listings = get_listings_for_stats(conn)
        stats_cache: dict = {}

        for listing in active_listings:
            location = listing["location"]
            condition = listing["condition"]

            cache_key = f"{location}:{condition}"
            if cache_key not in stats_cache:
                locs_to_check = [location, None]
                conds_to_check = [condition, None]

                best_median = None
                for loc in locs_to_check:
                    for cond in conds_to_check:
                        if cond is None and loc is None:
                            continue
                        median = get_median_price_per_m2(conn, loc, cond)
                        if median is not None:
                            if best_median is None or median < best_median:
                                best_median = median

                stats_cache[cache_key] = best_median

            median_m2 = stats_cache[cache_key]
            if median_m2 is None:
                continue

            price_m2 = listing["price"] / listing["area_m2"]
            discount = (median_m2 - price_m2) / median_m2

            if discount >= threshold:
                saved = save_opportunity(
                    conn,
                    listing["id"],
                    round(price_m2, 2),
                    round(median_m2, 2),
                    round(discount * 100, 1),
                    f"Cena {price_m2:.0f} Kč/m² je o {discount*100:.1f}% nižší než medián {median_m2:.0f} Kč/m²",
                )
                if saved:
                    opportunities.append({
                        "listing_id": listing["id"],
                        "url": listing["url"],
                        "title": listing["title"],
                        "price": listing["price"],
                        "area_m2": listing["area_m2"],
                        "location": listing["location"],
                        "source": listing["source"],
                        "price_m2": round(price_m2, 2),
                        "median_m2": round(median_m2, 2),
                        "discount_pct": round(discount * 100, 1),
                    })

        return opportunities
    finally:
        conn.close()


def run_full_analysis(db_path: str) -> dict:
    conn = get_connection(db_path)
    results = {
        "stats": [],
        "opportunities": [],
    }

    try:
        locations = set()
        conditions = set()
        for row in conn.execute(
            "SELECT DISTINCT location, condition FROM listings WHERE active = 1 AND location IS NOT NULL"
        ).fetchall():
            if row["location"]:
                locations.add(row["location"])
            if row["condition"]:
                conditions.add(row["condition"])

        for loc in locations:
            stat = calculate_market_stats(db_path, location=loc)
            if stat:
                results["stats"].append(stat)

            for cond in conditions:
                stat = calculate_market_stats(db_path, location=loc, condition=cond)
                if stat:
                    results["stats"].append(stat)

        conn.close()
        conn = get_connection(db_path)

    finally:
        conn.close()

    results["opportunities"] = detect_opportunities(db_path)

    return results
