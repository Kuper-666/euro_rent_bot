# EuroRent AI Bot

Telegram bot for analyzing rental listings across Europe using AI.

## Features

- AI-powered rental listing analysis (Groq LLaMA 3.3)
- Multi-language: RU, UK, EN, DE, PL
- Hidden fees & scam detection
- PDF application generator (Mieterprofil)
- VIP subscription with daily city digests
- City filter with price trends
- Referral program
- Email newsletter
- Rent scanner: monitors 22 Telegram channels across 9 countries
- Smart poster: auto-posts in rental groups + replies to comments

## Setup

### 1. Clone & install

```bash
git clone https://github.com/Kuper-666/euro_rent_bot.git
cd euro_rent_bot
pip install -r requirements.txt
```

### 2. Configure .env

```bash
cp .env.example .env
```

Required:
```
TELEGRAM_TOKEN=your_bot_token
GROQ_API_KEY=your_groq_key
```

Optional (for rent scanner):
```
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+your_phone
```

### 3. Run

```bash
# Main bot
python bot.py

# Rent scanner (separate terminal)
python -m rent_scanner

# Smart poster (separate terminal)
python smart_poster.py
```

## GitHub Actions (Free)

Set these secrets in GitHub → Settings → Secrets → Actions:

| Secret | Description |
|--------|-------------|
| `TELEGRAM_TOKEN` | Bot token |
| `GROUP_ID` | Your Telegram group ID |
| `CHANNEL_ID` | Your channel ID |
| `GROQ_API_KEY` | Groq API key |
| `CITY_CHANNELS` | JSON `{"berlin": "-100xxx"}` |

Workflows:
- **Tests** — runs on every push/PR
- **Daily Post** — Mon-Fri 10:00 UTC
- **Channel Poster** — Tue/Thu/Sat 09:00 UTC

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/help` | Usage instructions |
| `/balance` | Check remaining checks |
| `/pay` | Buy checks |
| `/pdf` | Generate PDF application |
| `/vip` | VIP subscription |
| `/ref` | Referral link |
| `/lang` | Change language |
| `/set_city` | Filter by city |
| `/trend` | City price trends |
| `/holygrail` | Best deals |

## Architecture

```
bot.py                 — Main Telegram bot (1379 lines)
rent_scanner/
  app.py               — Channel monitor + lead delivery
  storage.py           — SQLite + metrics
  filters.py           — Keyword matching (22 languages)
  formatting.py        — Rich listing cards
  sources.py           — 22 verified channels
smart_poster.py        — Auto-poster + reply listener
channel_poster.py      — AI-generated channel posts
daily_poster.py        — Daily digest
pdf_generator.py       — Mieterprofil PDF
```

## Tests

```bash
python -m pytest test_bot.py test_smart_poster.py test_bot_handlers.py -v
```

103 tests covering:
- Message handlers & payment flow
- Smart poster filtering
- PDF validation
- Price/area/rooms extraction
