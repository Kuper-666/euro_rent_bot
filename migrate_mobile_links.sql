-- migrate_mobile_links.sql
-- Выполни этот SQL в Supabase Dashboard → SQL Editor
-- Привязка Google-аккаунта мобильного приложения к Telegram user_id.
-- Позволяет баланс/лимиты проверок быть общими между ботом и приложением.

CREATE TABLE IF NOT EXISTS "MobileLinks" (
    google_user_id TEXT PRIMARY KEY,
    telegram_user_id TEXT NOT NULL,
    email TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mobile_links_telegram
    ON "MobileLinks" (telegram_user_id);
