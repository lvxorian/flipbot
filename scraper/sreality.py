import json
import re
import requests
from typing import Optional

from scraper.base import BaseScraper
from utils.user_agents import USER_AGENTS


LOCALITY_MAP = {
    "cheb": {"region": "CZ041", "subregion": 3808},
    "karlovy-vary": {"region": "CZ041", "subregion": 3940},
    "sokolov": {"region": "CZ041", "subregion": 3939},
    "marianske-lazne": {"region": "CZ041", "subregion": 3808},
    "kraslice": {"region": "CZ041", "subregion": 3939},
    "as": {"region": "CZ041", "subregion": 3808},
    "frantiskovy-lazne": {"region": "CZ041", "subregion": 3808},
}


class SrealityScraper(BaseScraper):
    SOURCE_NAME = "sreality"

    def get_search_url(self, location: str) -> str:
        loc = LOCALITY_MAP.get(location, {"region": "CZ041"})
        region = loc["region"]
        params = (
            f"category_main_cb=1&category_type_cb=1&locality_region={region}"
            f"&per_page=60&tms=1"
        )
        return f"https://www.sreality.cz/api/cs/v2/estates?{params}"

    def scrape(self, location: str, headless: bool = True) -> list[dict]:
        self.random_delay()
        url = self.get_search_url(location)
        headers = {"User-Agent": self.user_agent}
        results = []

        try:
            resp = requests.get(url, headers=headers, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("_embedded", {}).get("estates", []):
                listing = self._parse_item(item, location)
                if listing:
                    results.append(listing)
        except Exception as e:
            print(f"[sreality] Error fetching {location}: {e}")

        return results

    def _parse_item(self, item: dict, location: str) -> dict | None:
        try:
            external_id = str(item.get("hash_id", ""))
            if not external_id:
                return None

            price = item.get("price_czk")
            if price is None:
                price_raw = item.get("price")
                price = self.extract_price(str(price_raw)) if price_raw else None

            area = item.get("built_area") or item.get("area")
            if area is None:
                area = self.extract_area(str(item.get("locality", "")))

            title = item.get("name", {}).get("cs-CZ", "")

            sealing = item.get("sealing", {})
            condition_text = sealing.get("text", "") if sealing else ""
            condition = self.extract_condition(condition_text)

            locality_parts = []
            for part in ["region", "district", "municipality", "city", "street"]:
                val = item.get("locality", {}).get(part)
                if val:
                    locality_parts.append(str(val))
            full_location = ", ".join(locality_parts) if locality_parts else location

            image_url = None
            images = item.get("_links", {}).get("images", [])
            if images:
                image_url = f"https://www.sreality.cz{images[0].get('href', '')}" if "href" in images[0] else None

            return {
                "external_id": external_id,
                "source": self.SOURCE_NAME,
                "url": f"https://www.sreality.cz/detail/prodej/byt/{item.get('locality', {}).get('slug', location)}/{external_id}",
                "title": title,
                "location": full_location,
                "price": price,
                "area_m2": area,
                "condition": condition,
                "description": item.get("description", {}).get("cs-CZ", ""),
                "image_url": image_url,
            }
        except Exception as e:
            print(f"[sreality] Error parsing item: {e}")
            return None

    def parse_listings(self, page) -> list[dict]:
        pass
