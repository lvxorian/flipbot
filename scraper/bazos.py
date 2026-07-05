import re
from playwright.sync_api import Page
from scraper.base import BaseScraper


class BazosScraper(BaseScraper):
    SOURCE_NAME = "bazos"

    def get_search_url(self, location: str) -> str:
        return f"https://reality.bazos.cz/?hledat=byt+{location}"

    def parse_listings(self, page: Page) -> list[dict]:
        results = []
        try:
            page.wait_for_selector(".inzeratyd, .list, .maincontent", timeout=15000)
        except Exception:
            print("[bazos] No listing elements found")
            return results

        self.random_delay(4, 8)
        items = page.query_selector_all(".inzeraty .inzerat, .list-item, tr")
        print(f"[bazos] Found {len(items)} items")

        for item in items:
            try:
                listing = self._parse_item(item)
                if listing:
                    results.append(listing)
            except Exception as e:
                print(f"[bazos] Error parsing item: {e}")
                continue

        return results

    def _parse_item(self, item) -> dict | None:
        try:
            link_el = item.query_selector("a")
            if not link_el:
                return None

            href = link_el.get_attribute("href") or ""
            url = href if href.startswith("http") else f"https://reality.bazos.cz{href}"

            external_id = ""
            id_match = re.search(r'/(\d+)', href)
            if id_match:
                external_id = f"baz-{id_match.group(1)}"
            else:
                external_id = f"baz-{hash(href)}"

            title_el = link_el.query_selector(".nadpis, strong, b")
            title = title_el.inner_text().strip() if title_el else link_el.inner_text().strip()

            price_el = item.query_selector(".cena, .price, b:has-text('Kč')")
            price = None
            if price_el:
                price = self.extract_price(price_el.inner_text())

            area = self.extract_area(title)

            desc_el = item.query_selector(".popis, .description, td")
            description = desc_el.inner_text().strip() if desc_el else title

            condition = self.extract_condition(description + " " + title)

            location_el = item.query_selector(".lokalita, .locality, .location")
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
            print(f"[bazos] Parse error: {e}")
            return None
