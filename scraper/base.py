import random
import re
import time
from abc import ABC, abstractmethod
from typing import Optional

from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PwTimeout

from scraper.config import settings
from utils.user_agents import USER_AGENTS


class BaseScraper(ABC):
    SOURCE_NAME: str = "base"

    def __init__(self):
        self.user_agent = random.choice(USER_AGENTS)
        self.viewport = {
            "width": random.randint(1280, 1920),
            "height": random.randint(720, 1080),
        }

    def random_delay(self, min_s: int | None = None, max_s: int | None = None) -> None:
        delay = random.uniform(
            min_s or settings.MIN_DELAY_SECONDS,
            max_s or settings.MAX_DELAY_SECONDS,
        )
        time.sleep(delay)

    def _stealth_page(self, page: Page) -> None:
        page.evaluate("""() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['cs-CZ', 'cs', 'en-US', 'en'] });
        }""")

    def _create_context(self, playwright, headless: bool = True):
        browser = playwright.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(
            user_agent=self.user_agent,
            viewport=self.viewport,
            locale="cs-CZ",
            timezone_id="Europe/Prague",
            geolocation={"latitude": 50.0755, "longitude": 14.4378},
            permissions=["geolocation"],
        )
        return browser, context

    def scrape(self, location: str, headless: bool = True) -> list[dict]:
        self.random_delay()
        with sync_playwright() as playwright:
            browser, context = self._create_context(playwright, headless)
            try:
                page = context.new_page()
                self._stealth_page(page)
                results = self._scrape_page(page, location)
            except Exception as e:
                print(f"[{self.SOURCE_NAME}] Error scraping {location}: {e}")
                results = []
            finally:
                context.close()
                browser.close()
        return results

    def _safe_scrape_page(self, page: Page, location: str) -> list[dict]:
        url = self.get_search_url(location)
        print(f"[{self.SOURCE_NAME}] Fetching {url}")
        page.goto(url, wait_until="networkidle", timeout=settings.TIMEOUT_MS)
        self.random_delay()
        return self.parse_listings(page)

    def _scrape_page(self, page: Page, location: str) -> list[dict]:
        for attempt in range(settings.MAX_RETRIES + 1):
            try:
                return self._safe_scrape_page(page, location)
            except PwTimeout:
                print(f"[{self.SOURCE_NAME}] Timeout on {location}, attempt {attempt + 1}")
                if attempt < settings.MAX_RETRIES:
                    self.random_delay(10, 20)
                else:
                    print(f"[{self.SOURCE_NAME}] Failed after {settings.MAX_RETRIES + 1} attempts")
                    return []
            except Exception as e:
                print(f"[{self.SOURCE_NAME}] Error: {e}")
                if attempt < settings.MAX_RETRIES:
                    self.random_delay(10, 20)
                else:
                    return []

    @abstractmethod
    def get_search_url(self, location: str) -> str:
        ...

    @abstractmethod
    def parse_listings(self, page: Page) -> list[dict]:
        ...

    def extract_price(self, text: str | None) -> int | None:
        if not text:
            return None
        cleaned = re.sub(r'[^\d]', '', text)
        try:
            return int(cleaned)
        except (ValueError, TypeError):
            return None

    def extract_area(self, text: str | None) -> float | None:
        if not text:
            return None
        match = re.search(r'(\d+[.,]?\d*)\s*m[²2]', text)
        if match:
            try:
                return float(match.group(1).replace(',', '.'))
            except (ValueError, TypeError):
                return None
        match = re.search(r'(\d+[.,]?\d*)', text)
        if match:
            try:
                return float(match.group(1).replace(',', '.'))
            except (ValueError, TypeError):
                return None
        return None

    def extract_condition(self, text: str) -> str | None:
        if not text:
            return None
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["novostavba", "nový", "nově postaven"]):
            return "novostavba"
        if any(kw in text_lower for kw in ["po rekonstrukci", "zrekonstruovan", "rekonstruovaný"]):
            return "po rekonstrukci"
        if any(kw in text_lower for kw in ["před rekonstrukcí", "k rekonstrukci", "k renovaci"]):
            return "před rekonstrukcí"
        if any(kw in text_lower for kw in ["velmi dobrý", "dobrý", "udržovaný"]):
            return "dobrý"
        if any(kw in text_lower for kw in ["k demolici", "špatný", "zanedbaný"]):
            return "špatný"
        return None
