import datetime
import sys
import traceback

from scraper.config import settings
from scraper.database import (
    init_db,
    get_connection,
    upsert_listing,
    start_scrape_log,
    finish_scrape_log,
    get_unnotified_opportunities,
    mark_notified,
    export_to_json,
)
from scraper.sreality import SrealityScraper
from scraper.bezrealitky import BezrealitkyScraper
from scraper.annonce import AnnonceScraper
from scraper.bazos import BazosScraper
from scraper.realityidnes import RealityIdnesScraper
from scraper.hyperreality import HyperRealityScraper
from scraper.realcity import RealcityScraper
from analysis.analyzer import detect_opportunities, calculate_market_stats
from notifications.telegram import notify_opportunity


def get_scrapers() -> list:
    return [
        SrealityScraper(),
        BezrealitkyScraper(),
        AnnonceScraper(),
        BazosScraper(),
        RealityIdnesScraper(),
        HyperRealityScraper(),
        RealcityScraper(),
    ]


def run_scrape_session():
    start_time = datetime.datetime.now()
    print(f"=" * 60)
    print(f"FlipBot Scrape Session — {start_time.isoformat()}")
    print(f"=" * 60)

    init_db()
    conn = get_connection()
    log_id = start_scrape_log(conn)
    conn.close()

    total_found = 0
    total_new = 0
    total_price_changes = 0
    scrapers = get_scrapers()

    for scraper in scrapers:
        try:
            for location in settings.LOCATIONS:
                conn = get_connection()
                try:
                    print(f"\n[{scraper.SOURCE_NAME}] Scraping {location}...")
                    listings = scraper.scrape(location, headless=True)
                    print(f"[{scraper.SOURCE_NAME}] Found {len(listings)} listings in {location}")

                    for item in listings:
                        result = upsert_listing(
                            conn,
                            external_id=item["external_id"],
                            source=item["source"],
                            url=item["url"],
                            title=item.get("title"),
                            location=item.get("location"),
                            price=item.get("price"),
                            area_m2=item.get("area_m2"),
                            condition=item.get("condition"),
                            description=item.get("description"),
                            image_url=item.get("image_url"),
                        )
                        total_found += 1
                        if result["is_new"]:
                            total_new += 1
                        if result["price_changed"]:
                            total_price_changes += 1

                    conn.commit()
                except Exception as e:
                    print(f"[{scraper.SOURCE_NAME}] Error scraping {location}: {e}")
                    traceback.print_exc()
                finally:
                    conn.close()

        except Exception as e:
            print(f"[{scraper.SOURCE_NAME}] Fatal error: {e}")
            traceback.print_exc()

    print(f"\n--- Scraping complete ---")
    print(f"Total listings found: {total_found}")
    print(f"New listings: {total_new}")
    print(f"Price changes detected: {total_price_changes}")

    print(f"\n--- Running market analysis ---")
    try:
        opportunities = detect_opportunities(settings.DB_PATH)
        print(f"New opportunities detected: {len(opportunities)}")
    except Exception as e:
        print(f"Analysis error: {e}")
        traceback.print_exc()
        opportunities = []

    print(f"\n--- Sending notifications ---")
    conn = get_connection()
    try:
        unnotified = get_unnotified_opportunities(conn)
        sent_count = 0
        for opp in unnotified:
            success = notify_opportunity(opp)
            if success:
                mark_notified(conn, opp["id"])
                sent_count += 1
        conn.commit()
        print(f"Notifications sent: {sent_count}")
    except Exception as e:
        print(f"Notification error: {e}")
        traceback.print_exc()
    finally:
        conn.close()

    print(f"\n--- Finalizing scrape log ---")
    conn = get_connection()
    finish_scrape_log(
        conn, log_id, total_found, total_new,
        total_price_changes, len(opportunities),
        status="success",
    )
    conn.close()

    print(f"\n--- Exporting data ---")
    try:
        conn = get_connection()
        export_to_json(conn, settings.DATA_EXPORT_PATH)
        conn.close()
        print(f"Data exported to {settings.DATA_EXPORT_PATH}")
    except Exception as e:
        print(f"Export error: {e}")

    elapsed = (datetime.datetime.now() - start_time).total_seconds()
    print(f"\n=== Session finished in {elapsed:.0f}s ===")


if __name__ == "__main__":
    try:
        run_scrape_session()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)
