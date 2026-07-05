import re
import requests
from bs4 import BeautifulSoup

from scraper.base import BaseScraper


class HyperRealityScraper(BaseScraper):
    SOURCE_NAME = "hyperreality"

    def get_search_url(self, location: str) -> str:
        return f"https://www.hyperreality.cz/prodej-bytu-{location}/"

    def scrape(self, location: str, headless: bool = True) -> list[dict]:
        self.random_delay()
        url = self.get_search_url(location)
        headers = {"User-Agent": self.user_agent}
        results = []

        try:
            resp = requests.get(url, headers=headers, timeout=60)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            items = soup.select(".list-offer, .offer, article, .item, .estate-card")
            print(f"[hyperreality] Found {len(items)} items for {location}")

            for item in items:
                try:
                    listing = self._parse_item(item)
                    if listing:
                        results.append(listing)
                except Exception as e:
                    print(f"[hyperreality] Error parsing: {e}")
                    continue

        except Exception as e:
            print(f"[hyperreality] Error fetching {location}: {e}")

        return results

    def _parse_item(self, item) -> dict | None:
        try:
            link_el = item.find("a")
            if not link_el:
                return None

            href = link_el.get("href", "")
            url = href if href.startswith("http") else f"https://www.hyperreality.cz{href}"

            external_id = ""
            id_match = re.search(r'/(\d+)', href)
            if id_match:
                external_id = f"hyp-{id_match.group(1)}"
            else:
                external_id = f"hyp-{hash(href)}"

            title = link_el.get("title") or link_el.get_text(strip=True)

            price_el = item.select_one(".price, .cena")
            price = self.extract_price(price_el.get_text(strip=True)) if price_el else None

            area_el = item.select_one(".area, .plocha, .size")
            area = self.extract_area(area_el.get_text(strip=True)) if area_el else None

            desc_el = item.select_one(".description, .popis, p")
            description = desc_el.get_text(strip=True) if desc_el else ""

            condition = self.extract_condition(description + " " + title)

            location_el = item.select_one(".location, .lokalita, .adresa")
            location = location_el.get_text(strip=True) if location_el else ""

            img_el = item.find("img")
            image_url = img_el.get("src") if img_el else None

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
            print(f"[hyperreality] Parse error: {e}")
            return None

    def parse_listings(self, page) -> list[dict]:
        pass
