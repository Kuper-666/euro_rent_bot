"""
Ядро анализа объявлений: process_listing, check_followups.
Вынесено из bot.py для разгрузки.
"""
import os
import re
import time
import html
import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from config import FREE_LIMIT, GROQ_API_KEY
from messages import get_msg
from storage import save_user, get_user
from utils import (
    can_use, use_check, calc_remaining, expire_unlimited_if_needed, load_data, save_data,
)
from services.keyboards import kb, get_analysis_inline_buttons, split_message
from handlers.user_features import track_last_url
from handlers.commands import log_referral_event
from listing_features import (
    detect_city, extract_price, record_price, record_listing, extract_score, POPULAR_CITIES,
)

logger = logging.getLogger(__name__)

client = None
if GROQ_API_KEY:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)


async def process_listing(update: Update, context: ContextTypes.DEFAULT_TYPE, listing_text: str, user_id: str, lang: str, source_url: str = "") -> None:
    is_admin = False
    ADMIN_ID = int(os.getenv("ADMIN_ID", "-1"))
    if update.effective_user and update.effective_user.id == ADMIN_ID:
        is_admin = True
    if not is_admin and update.effective_chat.type in ["group", "supergroup"]:
        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
            if member.status in ["administrator", "creator"]:
                is_admin = True
        except Exception:
            pass

    if not client:
        await update.message.reply_text(
            "⚠️ Анализатор временно недоступен (не настроен API-ключ).",
            reply_markup=kb(update),
        )
        return

    try:
        system_prompt = get_msg(lang, "system_prompt")
        full_prompt = f"{system_prompt}\n\nListing text:\n{listing_text}"
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": full_prompt}]
        )
        result = response.choices[0].message.content
        if not result:
            result = "No analysis generated."

        await asyncio.to_thread(track_last_url, user_id, source_url, listing_text[:2000])

        city_key = detect_city(listing_text)
        price = extract_price(listing_text)
        if city_key and price:
            await asyncio.to_thread(record_price, city_key, price)
        await asyncio.to_thread(
            record_listing,
            listing_text[:200], city_key or "", price or 0,
            extract_score(result) if result else 5, listing_text,
        )

        city_note = ""
        if city_key:
            ci = POPULAR_CITIES.get(city_key)
            if ci:
                city_note = f"\n\n🏙 Город: {ci['emoji']} {ci['name']}"
                if price and ci.get("avg_price"):
                    ratio = price / ci["avg_price"]
                    if ratio < 0.75:
                        city_note += f"\n🔥 Цена {price} EUR — ниже средней ({ratio:.0%})"
                    elif ratio < 0.9:
                        city_note += f"\n💰 Цена {price} EUR — ниже средней"

        if is_admin:
            user = await asyncio.to_thread(get_user, user_id)
        else:
            user = await asyncio.to_thread(get_user, user_id)
            expire_unlimited_if_needed(user)
            if not can_use(user):
                ref_code = user.get("ref_code", "")
                ref_link = f"https://t.me/{context.bot.username}?start={ref_code}" if ref_code else ""
                await update.message.reply_text(
                    get_msg(lang, "limit_reached").format(ref_link),
                    reply_markup=kb(update)
                )
                log_referral_event("limit_ref_shown", user_id)
                return
            use_check(user)
            await asyncio.to_thread(save_user, user_id, user)

            # Обработка реферала
            if user.get("free_used", 0) == 1 and user.get("referred_by"):
                referrer_id = user["referred_by"]
                referrer = await asyncio.to_thread(get_user, referrer_id)
                referrals = referrer.setdefault("referrals", [])
                if user_id not in referrals:
                    referrals.append(user_id)
                    reward = {1: 1, 3: 3, 5: 5, 10: -1}.get(len(referrals), 0)
                    if reward == -1:
                        referrer["balance"] = -1
                        referrer["last_paid_at"] = time.time()
                    elif reward > 0:
                        referrer["balance"] = referrer.get("balance", 0) + reward
                    await asyncio.to_thread(save_user, referrer_id, referrer)
                    try:
                        n = len(referrals)
                        progress = ""
                        if n < 3:
                            progress = f"Ещё {3 - n} друга до +3 проверок!"
                        elif n < 5:
                            progress = f"Ещё {5 - n} друзей до +5 проверок!"
                        elif n < 10:
                            progress = f"Ещё {10 - n} друзей до безлимита!"
                        else:
                            progress = "🎉 Безлимит активирован!"
                        ref_code = referrer.get("ref_code", "")
                        ref_link = f"https://t.me/{context.bot.username}?start={ref_code}" if ref_code else ""
                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text=f"🎉 Ваш друг сделал первую проверку!\n"
                                 f"Приглашено: {n} чел.\n\n"
                                 f"📊 {progress}\n\n"
                                 f"Ваша ссылка: {ref_link}"
                        )
                        log_referral_event("referral_confirmed", referrer_id, {"referred": user_id, "total": n})
                    except Exception:
                        pass
                    user.pop("referred_by", None)
                if user.get("free_used", 0) == 1:
                    ref_code = user.get("ref_code", "")
                    ref_link = f"https://t.me/{context.bot.username}?start={ref_code}" if ref_code else ""
                    aha_msg = (
                        f"🎉 Это была ваша первая проверка!\n\n"
                        f"Если пригодилось — пригласите друга, который тоже ищет квартиру, "
                        f"и получите +1 проверку бесплатно.\n\n"
                        f"Ваша ссылка: {ref_link}"
                    )
                    await update.message.reply_text(aha_msg, reply_markup=kb(update))
                    log_referral_event("aha_moment_shown", user_id)
                elif user.get("free_used", 0) % 5 == 0 and user.get("free_used", 0) > 0:
                    ref_code = user.get("ref_code", "")
                    ref_link = f"https://t.me/{context.bot.username}?start={ref_code}" if ref_code else ""
                    if user.get("balance", 0) == -1:
                        total_checks = "∞"
                    else:
                        total_checks = user.get("free_used", 0) + max(0, user.get("balance", 0))
                    gentle_msg = (
                        f"📊 Вы уже сделали {total_checks} проверок с ботом!\n\n"
                        f"Если знаете кого-то в похожей ситуации — "
                        f"пригласите и получите +1 проверку бесплатно.\n\n"
                        f"Ваша ссылка: {ref_link}"
                    )
                    await update.message.reply_text(gentle_msg, reply_markup=kb(update))
                    log_referral_event("5check_trigger_shown", user_id, {"total_checks": total_checks})

        remaining = calc_remaining(user)
        clean_result = re.sub(r'<[^>]+>', '', result)
        safe_result = html.escape(clean_result)
        safe_footer = html.escape(get_msg(lang, "affiliate_footer"))
        remaining_text = "∞" if user.get("balance", 0) == -1 else html.escape(str(remaining))
        admin_note = html.escape("\n\nАдмин: проверка бесплатная") if is_admin else ""
        safe_balance = html.escape(f"\n\nОсталось проверок: ") + remaining_text
        ref_code = user.get("ref_code", "")
        share_url = f"https://t.me/{context.bot.username}?start={ref_code}" if ref_code else ""
        safe_share = f"\n\n{html.escape(get_msg(lang, 'share_text'))}\n<a href=\"{share_url}\">Поделиться с другом</a>" if share_url else ""

        work_address = user.get("work_address", "")
        travel_note = ""
        if work_address and city_key and city_key in POPULAR_CITIES:
            from travel_time import calc_travel_time_async
            city_name = POPULAR_CITIES[city_key].get("name", city_key)
            travel = await calc_travel_time_async(work_address, city_name)
            if travel:
                travel_note = f"\n\n🚗 <b>До работы:</b> {travel['text']}"

        full_text = safe_result + city_note + travel_note + safe_footer + admin_note + safe_balance + safe_share
        parts = split_message(full_text)
        for i, part in enumerate(parts):
            markup = get_analysis_inline_buttons() if i == len(parts) - 1 else None
            await update.message.reply_text(part, reply_markup=markup, parse_mode="HTML")

    except Exception as e:
        if "insufficient_quota" in str(e) or "429" in str(e):
            await update.message.reply_text(
                "Извините, анализатор сейчас перегружен.\n\n"
                "Попробуйте отправить объявление через 5-10 минут — я обязательно отвечу!\n\n"
                "А пока можете:\n"
                "- Прочитать /help о тарифах\n"
                "- Отправить ссылку позже",
                reply_markup=kb(update)
            )
        else:
            await update.message.reply_text(get_msg(lang, "error").format(str(e)[:200]), reply_markup=kb(update))


def check_followups(user: dict, lang: str) -> str:
    now = time.time()
    last_paid = user.get("last_paid_at", 0)
    free_used = user.get("free_used", 0)
    balance = user.get("balance", 0)

    if balance == -1:
        return ""

    if balance > 0 and last_paid:
        days_since = (now - last_paid) / 86400
        if 2.5 <= days_since <= 4:
            return (
                "Вы использовали часть проверок из пакета.\n"
                "Хотите докупить? /pay\n"
            )

    if free_used >= FREE_LIMIT and balance == 0:
        return (
            "Все бесплатные проверки использованы.\n\n"
            "Пакеты и цены:\n"
            "3 проверки — 300 Stars (~3EUR) -> /pay_3\n"
            "10 проверок — 900 Stars (~9EUR) -> /pay_9\n"
            "Безлимит/мес — 1900 Stars (~19EUR) -> /pay_19\n\n"
            "Подробнее: /pay"
        )

    return ""
