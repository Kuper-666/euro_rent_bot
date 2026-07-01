"""
Email-рассылка недельного дайджеста объявлений.
Запуск: python email_newsletter.py
Cron: 0 10 * * 1 cd /path/to/rent_bot && python email_newsletter.py
"""

import os
import json
import asyncio
import logging
import smtplib
import feedparser
import re
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from groq import Groq
from telegram import Bot

from config import GROQ_API_KEY
from utils import clean_text
from storage import load_data, save_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
NEWSLETTER_FROM = os.environ.get("NEWSLETTER_FROM", "EuroRent AI <noreply@eurorent.ai>")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")

RSS_FEEDS = [
    "https://www.google.com/alerts/feeds/15276190721492704538/14744967623754419043",
]

DIGEST_PROMPT = (
    "Ты — эксперт по аренде жилья в Европе. "
    "Составь краткую сводку (2-3 предложения) по объявлению. "
    "Выдели: цену, район, главные плюсы/минусы. "
    "Отвечай на русском."
)

bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def get_email_subscribers() -> list[dict]:
    subscribers_file = "email_subscribers.json"
    if os.path.exists(subscribers_file):
        with open(subscribers_file, "r") as f:
            return json.load(f)
    return []


def save_email_subscribers(subscribers: list[dict]):
    with open("email_subscribers.json", "w") as f:
        json.dump(subscribers, f, ensure_ascii=False, indent=2)


def add_email_subscriber(email: str, user_id: str) -> bool:
    if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email):
        logger.warning(f"Invalid email rejected: {email}")
        return False
    subscribers = get_email_subscribers()
    for s in subscribers:
        if s["email"] == email:
            return False
    subscribers.append({
        "email": email,
        "user_id": user_id,
        "subscribed_at": datetime.now(timezone.utc).isoformat(),
        "active": True,
    })
    save_email_subscribers(subscribers)
    return True


def remove_email_subscriber(email: str) -> bool:
    subscribers = get_email_subscribers()
    for s in subscribers:
        if s["email"] == email:
            s["active"] = False
            save_email_subscribers(subscribers)
            return True
    return False


def get_active_subscribers() -> list[dict]:
    return [s for s in get_email_subscribers() if s.get("active", True)]


def strip_html(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text).strip()


def fetch_week_entries():
    entries = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                url = entry.get("link", "")
                if not url:
                    continue
                title = strip_html(entry.get("title", ""))
                summary = strip_html(entry.get("summary", ""))[:500]
                entries.append({"url": url, "title": title, "summary": summary})
        except Exception as e:
            logger.error(f"RSS error: {e}")
    return entries


def analyze_for_digest(title: str, summary: str) -> str | None:
    if not groq_client:
        return None
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": DIGEST_PROMPT},
                {"role": "user", "content": f"{title}\n\n{summary}"},
            ],
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"GROQ error: {e}")
        return None


def build_digest_html(entries: list[dict], analyses: list[str], bot_username: str) -> str:
    listings_html = ""
    for entry, analysis in zip(entries, analyses):
        analyze_url = f"https://t.me/{bot_username}?start=analyze_{entry['url']}"
        listings_html += f"""
        <div style="background:#f8f9fa;border-radius:8px;padding:16px;margin-bottom:12px;border-left:4px solid #4CAF50;">
            <h3 style="margin:0 0 8px 0;color:#333;">{entry['title']}</h3>
            <p style="margin:0 0 8px 0;color:#555;">{analysis}</p>
            <a href="{entry['url']}" style="color:#1976D2;text-decoration:none;">Объявление</a>
            &nbsp;|&nbsp;
            <a href="{analyze_url}" style="color:#4CAF50;text-decoration:none;">Полный анализ в боте</a>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
        <div style="background:linear-gradient(135deg,#1976D2,#4CAF50);padding:24px;border-radius:12px 12px 0 0;">
            <h1 style="color:white;margin:0;font-size:24px;">🏠 EuroRent AI — Дайджест недели</h1>
            <p style="color:rgba(255,255,255,0.9);margin:8px 0 0 0;">Лучшие объявления об аренде в Европе</p>
        </div>
        <div style="padding:24px;background:white;border:1px solid #e0e0e0;">
            <p style="color:#555;font-size:16px;">Доброе утро! Вот лучшие объявления за неделю:</p>
            {listings_html}
            <hr style="border:none;border-top:1px solid #e0e0e0;margin:20px 0;">
            <p style="color:#888;font-size:13px;text-align:center;">
                <a href="https://t.me/{bot_username}" style="color:#1976D2;">Открыть бота в Telegram</a>
                &nbsp;|&nbsp;
                <a href="https://t.me/{bot_username}?start=unsubscribe_email" style="color:#888;">Отписаться</a>
            </p>
        </div>
    </body>
    </html>
    """


def build_digest_plain(entries: list[dict], analyses: list[str], bot_username: str) -> str:
    text = "🏠 EuroRent AI — Дайджест недели\n\n"
    text += "Лучшие объявления об аренде:\n\n"
    for i, (entry, analysis) in enumerate(zip(entries, analyses), 1):
        text += f"{i}. {entry['title']}\n"
        text += f"   {analysis}\n"
        text += f"   Объявление: {entry['url']}\n"
        text += f"   Анализ: https://t.me/{bot_username}?start=analyze_{entry['url']}\n\n"
    text += f"\n---\nБот: https://t.me/{bot_username}\nОтписаться: https://t.me/{bot_username}?start=unsubscribe_email\n"
    return text


def send_email(to_email: str, subject: str, html: str, plain: str) -> bool:
    if not SMTP_USER or not SMTP_PASS:
        logger.error("SMTP credentials not configured")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = NEWSLETTER_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(NEWSLETTER_FROM, to_email, msg.as_string())
        return True
    except Exception as e:
        logger.error(f"Email send error to {to_email}: {e}")
        return False


async def run_weekly_digest():
    subscribers = get_active_subscribers()
    if not subscribers:
        logger.info("No active email subscribers")
        return

    entries = fetch_week_entries()
    if not entries:
        logger.info("No entries found")
        return

    random.shuffle(entries)
    top_entries = entries[:5]

    analyses = []
    for entry in top_entries:
        analysis = analyze_for_digest(entry["title"], entry["summary"])
        analyses.append(analysis or entry["summary"][:200])

    me = await bot.get_me() if bot else None
    bot_username = me.username if me else "expat_rent_bot"

    html = build_digest_html(top_entries, analyses, bot_username)
    plain = build_digest_plain(top_entries, analyses, bot_username)
    subject = f"🏠 EuroRent AI — Дайджест за {datetime.now().strftime('%d.%m.%Y')}"

    sent = 0
    failed = 0
    for sub in subscribers:
        success = send_email(sub["email"], subject, html, plain)
        if success:
            sent += 1
            logger.info(f"Sent to {sub['email']}")
        else:
            failed += 1
        await asyncio.sleep(0.5)

    logger.info(f"Newsletter done. Sent: {sent}, Failed: {failed}")


if __name__ == "__main__":
    asyncio.run(run_weekly_digest())
