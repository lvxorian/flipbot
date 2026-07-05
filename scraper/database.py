import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from scraper.config import settings


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or settings.DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str | None = None) -> None:
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS listings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id     TEXT NOT NULL,
            source          TEXT NOT NULL,
            url             TEXT NOT NULL,
            title           TEXT,
            location        TEXT,
            price           INTEGER NOT NULL,
            area_m2         REAL,
            condition       TEXT,
            description     TEXT,
            image_url       TEXT,
            first_seen      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active          INTEGER DEFAULT 1,
            UNIQUE(external_id, source)
        );

        CREATE TABLE IF NOT EXISTS price_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id      INTEGER NOT NULL,
            price           INTEGER NOT NULL,
            recorded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (listing_id) REFERENCES listings(id)
        );

        CREATE TABLE IF NOT EXISTS market_stats (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            location        TEXT NOT NULL,
            condition       TEXT,
            avg_price_m2    REAL,
            median_price_m2 REAL,
            min_price_m2    REAL,
            max_price_m2    REAL,
            sample_count    INTEGER,
            calculated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS opportunities (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id      INTEGER NOT NULL,
            price_m2        REAL,
            median_price_m2 REAL,
            discount_pct    REAL,
            reason          TEXT,
            notified        INTEGER DEFAULT 0,
            notified_at     TIMESTAMP,
            detected_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (listing_id) REFERENCES listings(id)
        );

        CREATE TABLE IF NOT EXISTS scrape_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at      TIMESTAMP,
            finished_at     TIMESTAMP,
            listings_found  INTEGER DEFAULT 0,
            listings_new    INTEGER DEFAULT 0,
            price_changes   INTEGER DEFAULT 0,
            opportunities_found INTEGER DEFAULT 0,
            status          TEXT DEFAULT 'running',
            error_message   TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_listings_source ON listings(source);
        CREATE INDEX IF NOT EXISTS idx_listings_location ON listings(location);
        CREATE INDEX IF NOT EXISTS idx_listings_condition ON listings(condition);
        CREATE INDEX IF NOT EXISTS idx_listings_active ON listings(active);
        CREATE INDEX IF NOT EXISTS idx_opportunities_notified ON opportunities(notified);
    """)

    conn.commit()
    conn.close()


def upsert_listing(
    conn: sqlite3.Connection,
    external_id: str,
    source: str,
    url: str,
    title: str | None,
    location: str | None,
    price: int | None,
    area_m2: float | None,
    condition: str | None,
    description: str | None = None,
    image_url: str | None = None,
) -> dict:
    now = datetime.utcnow().isoformat()
    existing = conn.execute(
        "SELECT id, price FROM listings WHERE external_id = ? AND source = ?",
        (external_id, source),
    ).fetchone()

    price_changed = False

    if existing:
        old_price = existing["price"]
        conn.execute(
            """UPDATE listings
               SET url = ?, title = ?, location = ?, price = ?, area_m2 = ?,
                   condition = ?, description = ?, image_url = ?, last_seen = ?,
                   active = 1
               WHERE id = ?""",
            (url, title, location, price, area_m2, condition, description, image_url, now, existing["id"]),
        )
        listing_id = existing["id"]

        if old_price is not None and price is not None and old_price != price:
            price_changed = True
            conn.execute(
                "INSERT INTO price_history (listing_id, price, recorded_at) VALUES (?, ?, ?)",
                (listing_id, price, now),
            )
    else:
        cursor = conn.execute(
            """INSERT INTO listings
               (external_id, source, url, title, location, price, area_m2,
                condition, description, image_url, first_seen, last_seen)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (external_id, source, url, title, location, price, area_m2, condition, description, image_url, now, now),
        )
        listing_id = cursor.lastrowid

        if price is not None:
            conn.execute(
                "INSERT INTO price_history (listing_id, price, recorded_at) VALUES (?, ?, ?)",
                (listing_id, price, now),
            )

    return {"listing_id": listing_id, "is_new": existing is None, "price_changed": price_changed}


def get_listings_for_stats(
    conn: sqlite3.Connection,
    location: str | None = None,
    condition: str | None = None,
    min_price: int = 0,
    max_price: int = 50_000_000,
) -> list[dict]:
    query = """SELECT * FROM listings
               WHERE active = 1
                 AND price IS NOT NULL
                 AND area_m2 IS NOT NULL
                 AND price > ?
                 AND price < ?
                 AND area_m2 > 10"""
    params: list = [min_price, max_price]

    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    if condition:
        query += " AND condition = ?"
        params.append(condition)

    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_median_price_per_m2(conn: sqlite3.Connection, location: str | None = None, condition: str | None = None) -> float | None:
    listings = get_listings_for_stats(conn, location, condition)
    if not listings:
        return None

    prices_per_m2 = sorted([l["price"] / l["area_m2"] for l in listings])
    n = len(prices_per_m2)

    if n % 2 == 0:
        return (prices_per_m2[n // 2 - 1] + prices_per_m2[n // 2]) / 2
    return prices_per_m2[n // 2]


def save_market_stats(conn: sqlite3.Connection, location: str, condition: str | None,
                       avg: float, median: float, min_val: float, max_val: float, count: int) -> None:
    conn.execute(
        """INSERT INTO market_stats
           (location, condition, avg_price_m2, median_price_m2, min_price_m2, max_price_m2, sample_count)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (location, condition, avg, median, min_val, max_val, count),
    )


def save_opportunity(conn: sqlite3.Connection, listing_id: int, price_m2: float,
                     median_m2: float, discount_pct: float, reason: str) -> bool:
    existing = conn.execute(
        "SELECT id FROM opportunities WHERE listing_id = ?", (listing_id,)
    ).fetchone()
    if existing:
        return False
    conn.execute(
        """INSERT INTO opportunities (listing_id, price_m2, median_price_m2, discount_pct, reason)
           VALUES (?, ?, ?, ?, ?)""",
        (listing_id, price_m2, median_m2, discount_pct, reason),
    )
    return True


def get_unnotified_opportunities(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """SELECT o.*, l.url, l.title, l.price, l.area_m2, l.location, l.source, l.image_url
           FROM opportunities o
           JOIN listings l ON o.listing_id = l.id
           WHERE o.notified = 0
           ORDER BY o.detected_at DESC"""
    ).fetchall()
    return [dict(r) for r in rows]


def mark_notified(conn: sqlite3.Connection, opportunity_id: int) -> None:
    now = datetime.utcnow().isoformat()
    conn.execute(
        "UPDATE opportunities SET notified = 1, notified_at = ? WHERE id = ?",
        (now, opportunity_id),
    )


def start_scrape_log(conn: sqlite3.Connection) -> int:
    now = datetime.utcnow().isoformat()
    cursor = conn.execute(
        "INSERT INTO scrape_logs (started_at, status) VALUES (?, 'running')", (now,)
    )
    return cursor.lastrowid


def finish_scrape_log(conn: sqlite3.Connection, log_id: int, found: int, new: int,
                       price_changes: int, opportunities: int, status: str = "success",
                       error: str | None = None) -> None:
    now = datetime.utcnow().isoformat()
    conn.execute(
        """UPDATE scrape_logs
           SET finished_at = ?, listings_found = ?, listings_new = ?,
               price_changes = ?, opportunities_found = ?, status = ?, error_message = ?
           WHERE id = ?""",
        (now, found, new, price_changes, opportunities, status, error, log_id),
    )


def export_to_json(conn: sqlite3.Connection, output_path: str) -> None:
    listings = [dict(r) for r in conn.execute(
        """SELECT id, external_id, source, url, title, location, price, area_m2,
                  condition, image_url, first_seen, last_seen
           FROM listings WHERE active = 1 ORDER BY last_seen DESC"""
    ).fetchall()]

    opportunities = [dict(r) for r in conn.execute(
        """SELECT o.id, o.listing_id, o.price_m2, o.median_price_m2, o.discount_pct,
                  o.reason, o.detected_at, l.url, l.title, l.price, l.area_m2,
                  l.location, l.source
           FROM opportunities o
           JOIN listings l ON o.listing_id = l.id
           WHERE o.notified = 1
           ORDER BY o.detected_at DESC"""
    ).fetchall()]

    stats = [dict(r) for r in conn.execute(
        "SELECT * FROM market_stats ORDER BY calculated_at DESC LIMIT 50"
    ).fetchall()]

    log = conn.execute(
        "SELECT * FROM scrape_logs ORDER BY id DESC LIMIT 30"
    ).fetchone()
    last_scan = dict(log) if log else None

    data = {
        "exported_at": datetime.utcnow().isoformat(),
        "total_listings": len(listings),
        "total_opportunities": len(opportunities),
        "listings": listings,
        "opportunities": opportunities,
        "market_stats": stats,
        "last_scan": last_scan,
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
