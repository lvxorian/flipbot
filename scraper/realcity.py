import re
from playwright.sync_api import Page
from scraper.base import BaseScraper


class RealcityScraper(BaseScraper):
    SOURCE_NAME = "realcity"

    def get_search_url(self, location: str) -> str:
        return f"https://www.realcity.cz/prodej/byty/{location}/"

    def parse_listings(self, page: Page) -> list[dict]:
        results = []
        try:
            page.wait_for_selector("article, .offer-card, .estate-item, .property-card", timeout=15000)
        except Exception:
            print("[realcity] No listing elements found")
            return results

        self.random_delay(2, 5)
        items = page.query_selector_all("article, .offer-card, .estate-item, .property-card, [class*='offer']")
        print(f"[realcity] Found {len(items)} items")

        for item in items:
            try:
                listing = self._parse_item(item)
                if listing:
                    results.append(listing)
            except Exception as e:
                print(f"[realcity] Error parsing item: {e}")
                continue

        return results

    def _parse_item(self, item) -> dict | None:
        try:
            link_el = item.query_selector("a")
            if not link_el:
                return None

            href = link_el.get_attribute("href") or ""
            url = href if href.startswith("http") else f"https://www.realcity.cz{href}"

            external_id = ""
            id_match = re.search(r'/(\d+)', href)
            if id_match:
                external_id = f"rc-{id_match.group(1)}"
            else:
                external_id = f"rc-{hash(href)}"

            title_el = link_el.query_selector("h2, h3, .title")
            title = title_el.inner_text().strip() if title_el else link_el.inner_text().strip()

            price_el = item.query_selector(".price, .cena, [class*='price']")
            price = None
            if price_el:
                price = self.extract_price(price_el.inner_text())

            area_el = item.query_selector(".area, .plocha, .size, [class*='area']")
            area = None
            if area_el:
                area = self.extract_area(area_el.inner_text())

            desc_el = item.query_selector(".description, .popis, .text")
            description = desc_el.inner_text().strip() if desc_el else ""

            condition = self.extract_condition(description + " " + title)

            location_el = item.query_selector(".location, .lokalita, .address, .place")
            location = location_el.inner_text().strip() if location_el else ""

            img_el = item.query_selector("img")
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
            print(f"[realcity] Parse error: {e}")
            return None
