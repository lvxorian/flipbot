# FlipBot — Realitní monitorovací systém

Automated real estate monitoring for Czech republic. Scrapes 7 portals, tracks prices, detects undervalued properties, sends Telegram alerts, and provides a professional web dashboard.

## Architecture

```
┌──────────────────┐     ┌──────────────┐     ┌──────────────┐
│  GitHub Actions  │ ──→ │  SQLite DB   │ ──→ │  FastAPI Web │
│  (every 6 hours) │     │ + data.json  │     │  Dashboard   │
│  7 scrapers      │     │  export      │     │  (Vercel)    │
│  → analysis      │     └──────────────┘     └──────────────┘
│  → Telegram      │
└──────────────────┘
```

## Sources (7)

| Portal | Method | Type |
|--------|--------|------|
| Sreality | REST API | Byty, prodej |
| Bezrealitky | Playwright | Byty, prodej |
| Annonce | Playwright | Classifieds |
| Bazos | Playwright | Classifieds |
| Reality iDNES | Playwright | Byty, prodej |
| HyperReality | requests+BS4 | Aggregator |
| Realcity | Playwright | Byty, prodej |

## Setup

### 1. Clone & install

```bash
git clone https://github.com/lvxorian/flipbot.git
cd flipbot
pip install -r requirements.txt
playwright install chromium
```

### 2. Create Telegram bot

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Choose name (e.g. `FlipBot Realitni Monitor`)
4. Choose username ending in `bot` (e.g. `flipbot_monitor_bot`)
5. BotFather replies with your **token** — save it
6. Start a chat with your bot (send any message)
7. Get your **chat ID**:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
   Your chat ID is the `chat.id` value in the response.

### 3. Environment variables

Copy this to `.env` in project root:

```env
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
LOCATIONS=["cheb","karlovy-vary","sokolov","marianske-lazne"]
DISCOUNT_THRESHOLD=0.15
```

### 4. Run locally

```bash
python main.py
```

### 5. Run web dashboard locally

```bash
python -m uvicorn web.app:app --reload --port 8000
```

Open http://localhost:8000

## GitHub Actions (free, every 6h)

### 1. Push to GitHub

```bash
git remote add origin https://github.com/lvxorian/flipbot.git
git push -u origin main
```

### 2. Add secrets

Go to **Settings → Secrets and variables → Actions** in your repo and add:

| Secret | Value |
|--------|-------|
| `TELEGRAM_TOKEN` | Your bot token from BotFather |
| `TELEGRAM_CHAT_ID` | Your chat ID |

### 3. Enable GitHub Pages (optional, for Vercel-free alternative)

Go to **Settings → Pages** → set source to **GitHub Actions**

## Deploy web dashboard on Vercel (free)

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/lvxorian/flipbot)

1. Click the button above or go to [vercel.com](https://vercel.com)
2. Import your `flipbot` repo
3. Set **Root Directory** to `./` (default)
4. Set **Framework Preset** to `Other`
5. Add env variable: `DATA_EXPORT_PATH=data/data.json`
6. Deploy

The dashboard reads `data/data.json` which is auto-committed by the scraper every 6 hours.

## How it works

1. **Scrape** — each portal is scraped with random delays (3-8s) and rotating User-Agents
2. **Store** — listings are upserted in SQLite with full price history
3. **Analyze** — median price/m² is calculated per location and condition
4. **Detect** — if a listing is >15% below median, it's flagged as an opportunity
5. **Notify** — new opportunities and price drops are sent via Telegram
6. **Export** — `data/data.json` is committed for the Vercel dashboard

## Project structure

```
flipbot/
├── scraper/           # Scrapers + database + config
│   ├── config.py
│   ├── database.py
│   ├── base.py
│   ├── sreality.py
│   ├── bezrealitky.py
│   ├── annonce.py
│   ├── bazos.py
│   ├── realityidnes.py
│   ├── hyperreality.py
│   └── realcity.py
├── analysis/          # Market analysis + opportunity detection
├── notifications/     # Telegram alerts
├── web/               # FastAPI dashboard
│   ├── app.py
│   ├── templates/
│   └── static/
├── api/               # Vercel entry point
├── utils/             # User-Agent pool
├── main.py            # Scrape orchestrator
└── .github/workflows/ # CI/CD
```

## Customization

Edit `scraper/config.py` or set env vars:

- `LOCATIONS` — JSON array of cities to scan
- `DISCOUNT_THRESHOLD` — trigger at % below median (default 0.15 = 15%)
- `MIN_DELAY_SECONDS` / `MAX_DELAY_SECONDS` — pause between pages
- `PORTAL_DELAY_SECONDS` — pause between portals
