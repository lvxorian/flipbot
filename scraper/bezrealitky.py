import re
from playwright.sync_api import Page
from scraper.base import BaseScraper


class BezrealitkyScraper(BaseScraper):
    SOURCE_NAME = "bezrealitky"

    def get_search_url(self, location: str) -> str:
        return (
            f"https://www.bezrealitky.cz/vyhledat?"
            f"offerType=prodej&estateType=byt&location={location}"
        )

    def parse_listings(self, page: Page) -> list[dict]:
        results = []
        try:
            page.wait_for_selector('[data-testid="estate-card"]', timeout=15000)
        except Exception:
            try:
                page.wait_for_selector(".MuiCard-root", timeout=10000)
            except Exception:
                print("[bezrealitky] No estate cards found")
                return results

        self.random_delay(2, 4)
        cards = page.query_selector_all('[data-testid="estate-card"], .MuiCard-root')
        print(f"[bezrealitky] Found {len(cards)} cards")

        for card in cards:
            try:
                listing = self._parse_card(card)
                if listing:
                    results.append(listing)
            except Exception as e:
                print(f"[bezrealitky] Error parsing card: {e}")
                continue

        return results

    def _parse_card(self, card) -> dict | None:
        try:
            link_el = card.query_selector("a")
            if not link_el:
                return None

            href = link_el.get_attribute("href") or ""
            url = f"https://www.bezrealitky.cz{href}" if href.startswith("/") else href

            external_id = ""
            id_match = re.search(r'/(\d+)(?:\?|$)', href)
            if id_match:
                external_id = id_match.group(1)
            else:
                title_el = link_el.query_selector("h2, h3, [data-testid='title']")
                title_text = title_el.inner_text() if title_el else ""
                external_id = f"brk-{hash(href)}"

            title_el = card.query_selector("h2, h3, [data-testid='title']")
            title = title_el.inner_text().strip() if title_el else ""

            price_el = card.query_selector('[data-testid="price"], [class*="price"]')
            price = None
            if price_el:
                price = self.extract_price(price_el.inner_text())

            area_el = card.query_selector('[data-testid="area"], [class*="area"]')
            area = None
            if area_el:
                area = self.extract_area(area_el.inner_text())

            desc_el = card.query_selector('[data-testid="description"], p, [class*="description"]')
            description = desc_el.inner_text().strip() if desc_el else ""
            condition = self.extract_condition(description + " " + title)

            location_el = card.query_selector('[data-testid="location"], [class*="location"]')
            location = location_el.inner_text().strip() if location_el else ""

            img_el = card.query_selector("img")
            image_url = img_el.get_attribute("src") if img_el else None

            return {
                "external_id": external_id,
                "source": self.SOURCE_NAME,
                "url": url,
                "title": title,
                "location": location,
                "price": price,
                "area_m2": area,
                "condition": condition,
                "description": description,
                "image_url": image_url,
            }
        except Exception as e:
            print(f"[bezrealitky] Card parse error: {e}")
            return None
