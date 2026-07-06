-- Выполни этот SQL в Supabase Dashboard → SQL Editor
-- Это создаст 3 недостающие таблицы

-- 1. EmailSubscribers (подписчики email)
CREATE TABLE IF NOT EXISTS "EmailSubscribers" (
  id SERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  user_id TEXT DEFAULT '',
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE "EmailSubscribers" ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Service role full access on EmailSubscribers' AND tablename = 'EmailSubscribers') THEN
    CREATE POLICY "Service role full access on EmailSubscribers" ON "EmailSubscribers" FOR ALL USING (auth.role() = 'service_role');
  END IF;
END $$;

-- 2. PostedListings (дедупликация постов)
CREATE TABLE IF NOT EXISTS "PostedListings" (
  id SERIAL PRIMARY KEY,
  url TEXT UNIQUE NOT NULL,
  title TEXT DEFAULT '',
  city TEXT DEFAULT '',
  posted_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE "PostedListings" ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Service role full access on PostedListings' AND tablename = 'PostedListings') THEN
    CREATE POLICY "Service role full access on PostedListings" ON "PostedListings" FOR ALL USING (auth.role() = 'service_role');
  END IF;
END $$;

-- 3. ReferralEvents (лог рефералов)
CREATE TABLE IF NOT EXISTS "ReferralEvents" (
  id SERIAL PRIMARY KEY,
  event_type TEXT NOT NULL,
  user_id TEXT NOT NULL,
  extra JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE "ReferralEvents" ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Service role full access on ReferralEvents' AND tablename = 'ReferralEvents') THEN
    CREATE POLICY "Service role full access on ReferralEvents" ON "ReferralEvents" FOR ALL USING (auth.role() = 'service_role');
  END IF;
END $$;
