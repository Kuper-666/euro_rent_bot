-- Выполни в Supabase SQL Editor

-- 1. Favorites
CREATE TABLE IF NOT EXISTS "Favorites" (
  id SERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  listing_url TEXT NOT NULL,
  listing_title TEXT DEFAULT '',
  price TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. ApplicationTracker
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

-- 3. UserProfiles
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

-- 4. AlertSubscriptions
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

-- 5. WebListings
CREATE TABLE IF NOT EXISTS "WebListings" (
  id SERIAL PRIMARY KEY,
  portal TEXT NOT NULL,
  url TEXT UNIQUE NOT NULL,
  title TEXT DEFAULT '',
  price NUMERIC DEFAULT 0,
  city TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Новые колонки в Users
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS filter_furnished BOOLEAN DEFAULT FALSE;
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS filter_pets BOOLEAN DEFAULT FALSE;
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS filter_parking BOOLEAN DEFAULT FALSE;
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS work_address TEXT DEFAULT '';

-- 7. RLS policies
ALTER TABLE "Favorites" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "ApplicationTracker" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "UserProfiles" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "AlertSubscriptions" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "WebListings" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on Favorites" ON "Favorites" FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access on ApplicationTracker" ON "ApplicationTracker" FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access on UserProfiles" ON "UserProfiles" FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access on AlertSubscriptions" ON "AlertSubscriptions" FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access on WebListings" ON "WebListings" FOR ALL USING (auth.role() = 'service_role');
