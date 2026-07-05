import requests
from scraper.config import settings


TELEGRAM_API = "https://api.telegram.org/bot"


def send_message(text: str, parse_mode: str = "MarkdownV2") -> bool:
    if not settings.is_telegram_configured:
        print("[telegram] Skipping notification — TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set")
        return False

    url = f"{TELEGRAM_API}{settings.TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False,
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[telegram] Failed to send message: {e}")
        return False


def escape_markdown(text: str) -> str:
    special_chars = r"_*[]()~`>#+-=|{}!"
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text




def format_opportunity_alert(opp: dict) -> str:
    title = escape_markdown(opp.get("title", "Bez názvu")[:80])
    location = escape_markdown(opp.get("location", "Neznámá")[:40])
    url = opp.get("url", "")
    price = opp.get("price", 0)
    area = opp.get("area_m2", 0)
    price_m2 = opp.get("price_m2", 0)
    median_m2 = opp.get("median_m2", 0)
    discount = opp.get("discount_pct", 0)
    source = opp.get("source", "neznámý")

    return (
        f"🏠 *Potenciální flip / investice\\!*\n"
        f"📡 *Zdroj:* {escape_markdown(source)}\n"
        f"🏷 *{title}*\n"
        f"📍 {location}\n\n"
        f"💰 *Cena:* {price:,}\\. Kč\n"
        f"📐 *Plocha:* {area} m²\n"
        f"📊 *Cena za m²:* {price_m2:,.0f} Kč\n"
        f"📈 *Medián v lokalitě:* {median_m2:,.0f} Kč/m²\n"
        f"🔻 *Sleva oproti trhu:* {discount}\\%\n\n"
        f"[🔗 Otevřít inzerát]({url})"
    )


def format_price_drop_alert(listing: dict, old_price: int, new_price: int) -> str:
    title = escape_markdown(listing.get("title", "Bez názvu")[:80])
    location = escape_markdown(listing.get("location", "Neznámá")[:40])
    url = listing.get("url", "")
    source = listing.get("source", "neznámý")
    drop_pct = ((old_price - new_price) / old_price) * 100

    return (
        f"📉 *Zlevněno\\!*\n"
        f"📡 *Zdroj:* {escape_markdown(source)}\n"
        f"🏷 *{title}*\n"
        f"📍 {location}\n\n"
        f"~~{old_price:,}\\. Kč~~ → *{new_price:,}\\. Kč*\n"
        f"🔻 *Sleva:* {drop_pct:.1f}\\%\n\n"
        f"[🔗 Otevřít inzerát]({url})"
    )


def notify_opportunity(opp: dict) -> bool:
    msg = format_opportunity_alert(opp)
    return send_message(msg)


def notify_price_drop(listing: dict, old_price: int, new_price: int) -> bool:
    msg = format_price_drop_alert(listing, old_price, new_price)
    return send_message(msg)
