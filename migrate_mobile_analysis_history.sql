-- migrate_mobile_analysis_history.sql
-- Выполни этот SQL в Supabase Dashboard → SQL Editor
-- Персональная история анализов для мобильного приложения EuroRent Lens
-- (/api/history). Отдельная от общей истории объявлений в listing_features.py
-- (_load_history/_save_history) — та глобальная, для всех пользователей
-- бота, эта — по конкретному telegram_user_id, для отображения в приложении.

CREATE TABLE IF NOT EXISTS "MobileAnalysisHistory" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_user_id TEXT NOT NULL,
    listing_text TEXT NOT NULL,
    analysis TEXT NOT NULL,
    city TEXT DEFAULT '',
    price DOUBLE PRECISION,
    score INTEGER,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mobile_analysis_history_user
    ON "MobileAnalysisHistory" (telegram_user_id, created_at DESC);
