"""
Reddit мониторинг для EuroRent AI.
Только чтение — сбор постов по ключевым словам.
Запуск: python reddit_monitor.py
"""

import os
import re
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path

import praw
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("reddit_monitor")

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
SEEN_FILE = DATA_DIR / "reddit_seen.json"
REPORT_FILE = DATA_DIR / "reddit_report.txt"

SUBREDDITS = [
    "berlin", "germany", "askberliners",
    "Munich", "Hamburg", "frankfurt", "cologne",
    "expats", "AskAGerman", "Finanzen",
    "rentbusters", "Renters", "wohnen",
]

KEYWORDS = [
    "rent", "apartment", "scam", "landlord", "rental",
    "Nebenkosten", "Miete", "Wohnung", "Mietvertrag",
    "hidden fees", "deposit", "Kaution", "Vermieter",
    "besichtigung", "viewing", "contract", "betrug",
    "fake listing", "mieter", "anmeldung", "wohnungsbesichtigung",
    "provision", "makler", "immobilien", "mietpreis",
]

SEEN_POSTS = {}

# Записи о просмотренных постах старше этого срока удаляются при каждом
# save_seen() — без этого reddit_seen.json растёт неограниченно на
# протяжении всего времени жизни бота (13 subreddit'ов × 25 постов каждые
# 6 часов), раздувая файл и память на каждый load_seen(). 30 дней с запасом
# покрывает любой реалистичный интервал, за который пост мог бы повторно
# попасться (Reddit API отдаёт .new() — самые свежие посты, не архив).
SEEN_POST_TTL_SECONDS = 30 * 86400


def load_seen():
    global SEEN_POSTS
    if SEEN_FILE.exists():
        try:
            with open(SEEN_FILE) as f:
                SEEN_POSTS = json.load(f)
        except (json.JSONDecodeError, OSError):
            SEEN_POSTS = {}


def save_seen():
    now = time.time()
    global SEEN_POSTS
    SEEN_POSTS = {
        post_id: entry
        for post_id, entry in SEEN_POSTS.items()
        if now - entry.get("seen_at", now) < SEEN_POST_TTL_SECONDS
    }
    with open(SEEN_FILE, "w") as f:
        json.dump(SEEN_POSTS, f, indent=2)


def keyword_score(title: str, text: str) -> int:
    combined = f"{title} {text}".lower()
    score = 0
    for kw in KEYWORDS:
        if re.search(re.escape(kw.lower()), combined):
            score += 1
    return score


def monitor():
    load_seen()

    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "EuroRentAI/v1.0 (by /u/eurorent_ai)")

    if not client_id or not client_secret:
        logger.warning("REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET not set — skipping")
        return

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )

    logger.info(f"Logged in as: {reddit.user.me()}")
    matches = []
    now_ts = int(time.time())

    for sub_name in SUBREDDITS:
        try:
            sub = reddit.subreddit(sub_name)
            for post in sub.new(limit=25):
                post_id = post.id
                if post_id in SEEN_POSTS:
                    continue

                score = keyword_score(post.title, post.selftext or "")
                if score < 2:
                    continue

                url = f"https://reddit.com{post.permalink}"
                SEEN_POSTS[post_id] = {
                    "title": post.title,
                    "subreddit": sub_name,
                    "url": url,
                    "score": score,
                    "created": post.created_utc,
                    "seen_at": now_ts,
                }
                matches.append({
                    "subreddit": sub_name,
                    "title": post.title,
                    "url": url,
                    "score": score,
                    "created": datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
                })
                logger.info(f"[{sub_name}] score={score} — {post.title[:80]}")
        except Exception as e:
            logger.warning(f"Error reading r/{sub_name}: {e}")

    save_seen()

    if not matches:
        logger.info("No new matches found")
        return

    matches.sort(key=lambda m: m["score"], reverse=True)

    lines = [
        f"=== Reddit Report — {datetime.now().strftime('%d.%m.%Y %H:%M')} ===",
        f"Найдено: {len(matches)} постов\n",
    ]
    for m in matches:
        lines.append(f"[r/{m['subreddit']}] (score={m['score']}) {m['title']}")
        lines.append(f"  {m['url']}")
        lines.append(f"  {m['created'].strftime('%d.%m.%Y %H:%M')}")
        lines.append("")

    report = "\n".join(lines)
    print(report)

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info(f"Report saved to {REPORT_FILE}")

    try:
        from alerting import alert_admin
        top = matches[:5]
        alert_lines = [f"🔍 Reddit: найдено {len(matches)} релевантных постов\n"]
        for m in top:
            alert_lines.append(f"[r/{m['subreddit']}] (score={m['score']}) {m['title'][:80]}\n{m['url']}")
        alert_admin("reddit_matches", "\n\n".join(alert_lines))
    except Exception as e:
        logger.warning(f"Failed to alert admin about Reddit matches: {e}")


if __name__ == "__main__":
    monitor()
