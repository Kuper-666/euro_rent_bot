-- Phase 1 SQL: Favorites, ApplicationTracker, UserProfiles, AlertSubscriptions, Filters
-- Выполни в Supabase SQL Editor

-- Избранное
CREATE TABLE IF NOT EXISTS "Favorites" (
  id SERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  listing_url TEXT NOT NULL,
  listing_title TEXT DEFAULT '',
  price TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Трекер заявок
CREATE TABLE IF NOT EXISTS "ApplicationTracker" (
  id SERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  listing_url TEXT NOT NULL,
  listing_title TEXT DEFAULT '',
  status TEXT DEFAULT 'saved',
  notes TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Профиль пользователя (для писем)
CREATE TABLE IF NOT EXISTS "UserProfiles" (
  user_id TEXT PRIMARY KEY,
  full_name TEXT DEFAULT '',
  profession TEXT DEFAULT '',
  income TEXT DEFAULT '',
  employer TEXT DEFAULT '',
  move_in_date TEXT DEFAULT '',
  occupants TEXT DEFAULT '',
  pets TEXT DEFAULT '',
  cover_letter TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Подписки на алерты
CREATE TABLE IF NOT EXISTS "AlertSubscriptions" (
  id SERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  city TEXT NOT NULL,
  max_price NUMERIC DEFAULT 0,
  furnished BOOLEAN DEFAULT FALSE,
  pets_allowed BOOLEAN DEFAULT FALSE,
  parking BOOLEAN DEFAULT FALSE,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Веб-листинги (для скана сайтов)
CREATE TABLE IF NOT EXISTS "WebListings" (
  id SERIAL PRIMARY KEY,
  portal TEXT NOT NULL,
  url TEXT UNIQUE NOT NULL,
  title TEXT DEFAULT '',
  price NUMERIC DEFAULT 0,
  city TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Колонки фильтров в Users
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS filter_furnished BOOLEAN DEFAULT FALSE;
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS filter_pets BOOLEAN DEFAULT FALSE;
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS filter_parking BOOLEAN DEFAULT FALSE;
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS work_address TEXT DEFAULT '';

-- RLS policies для новых таблиц
ALTER TABLE "Favorites" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "ApplicationTracker" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "UserProfiles" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "AlertSubscriptions" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "WebListings" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on Favorites" ON "Favorites" FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Anon read on Favorites" ON "Favorites" FOR SELECT USING (true);

CREATE POLICY "Service role full access on ApplicationTracker" ON "ApplicationTracker" FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Anon read on ApplicationTracker" ON "ApplicationTracker" FOR SELECT USING (true);

CREATE POLICY "Service role full access on UserProfiles" ON "UserProfiles" FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Anon read on UserProfiles" ON "UserProfiles" FOR SELECT USING (true);

CREATE POLICY "Service role full access on AlertSubscriptions" ON "AlertSubscriptions" FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Anon read on AlertSubscriptions" ON "AlertSubscriptions" FOR SELECT USING (true);

CREATE POLICY "Service role full access on WebListings" ON "WebListings" FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Anon read on WebListings" ON "WebListings" FOR SELECT USING (true);
