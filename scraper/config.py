import os
import json
from dotenv import load_dotenv

load_dotenv()


class Settings:
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    DB_PATH: str = os.getenv("DB_PATH", "data/flipbot.db")
    DATA_EXPORT_PATH: str = os.getenv("DATA_EXPORT_PATH", "data/data.json")

    DISCOUNT_THRESHOLD: float = float(os.getenv("DISCOUNT_THRESHOLD", "0.15"))

    MIN_DELAY_SECONDS: int = int(os.getenv("MIN_DELAY_SECONDS", "3"))
    MAX_DELAY_SECONDS: int = int(os.getenv("MAX_DELAY_SECONDS", "8"))
    PORTAL_DELAY_SECONDS: int = int(os.getenv("PORTAL_DELAY_SECONDS", "30"))

    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "2"))
    TIMEOUT_MS: int = int(os.getenv("TIMEOUT_MS", "60000"))

    LOCATIONS: list[str] = json.loads(
        os.getenv("LOCATIONS", '["cheb", "karlovy-vary", "sokolov", "marianske-lazne"]')
    )

    @property
    def is_telegram_configured(self) -> bool:
        return bool(self.TELEGRAM_TOKEN) and bool(self.TELEGRAM_CHAT_ID)


settings = Settings()
