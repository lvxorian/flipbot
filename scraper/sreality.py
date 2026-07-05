import re
from playwright.sync_api import Page, TimeoutError as PwTimeout
from scraper.base import BaseScraper
from scraper.config import settings


class SrealityScraper(BaseScraper):
    SOURCE_NAME = "sreality"

    def get_search_url(self, location: str) -> str:
        return f"https://www.sreality.cz/hledani/prodej/byty/{location}/"

    def parse_listings(self, page: Page) -> list[dict]:
        results = []
        try:
            page.wait_for_selector('[id^="estate-list-item"]', timeout=20000)
        except Exception:
            print("[sreality] No listing items found")
            return results

        self.random_delay(2, 4)
        cards = page.query_selector_all('[id^="estate-list-item"]')
        print(f"[sreality] Found {len(cards)} cards")

        for card in cards:
            try:
                listing = self._parse_card(card)
                if listing:
                    results.append(listing)
            except Exception as e:
                print(f"[sreality] Card parse error: {e}")
                continue

        return results

    def _safe_scrape_page(self, page: Page, location: str) -> list[dict]:
        url = self.get_search_url(location)
        print(f"[sreality] Fetching {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=settings.TIMEOUT_MS)
        self._handle_consent(page)
        self.random_delay()
        return self.parse_listings(page)

    def _handle_consent(self, page: Page) -> None:
        if "cmp.seznam" in page.url:
            try:
                btn = page.wait_for_selector(
                    "[data-testid='cw-button-agree-with-ads']", timeout=10000
                )
                if btn:
                    btn.click(force=True)
                    page.wait_for_url("**sreality.cz**", timeout=15000)
            except PwTimeout:
                raise
            except Exception as e:
                print(f"[sreality] Consent error: {e}")

    def _parse_card(self, card) -> dict | None:
        link = card.query_selector("a")
        if not link:
            return None

        href = link.get_attribute("href") or ""
        url = f"https://www.sreality.cz{href}" if href.startswith("/") else href

        id_match = re.search(r"/(\d+)$", href)
        if not id_match:
            return None
        external_id = id_match.group(1)

        price_el = card.query_selector("p:has-text('Kč')")
        price = self.extract_price(price_el.inner_text()) if price_el else None

        paras = card.query_selector_all("p")
        title = paras[0].inner_text().strip() if paras else ""
        location = paras[1].inner_text().strip() if len(paras) >= 2 else ""
        area = self.extract_area(title)
        condition = self.extract_condition(title)

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
            "description": title,
            "image_url": image_url,
        }
