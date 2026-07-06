CREATE TABLE IF NOT EXISTS "Favorites" (id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, listing_url TEXT NOT NULL, listing_title TEXT DEFAULT '', price TEXT DEFAULT '', created_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE IF NOT EXISTS "ApplicationTracker" (id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, listing_url TEXT NOT NULL, listing_title TEXT DEFAULT '', status TEXT DEFAULT 'saved', notes TEXT DEFAULT '', created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE IF NOT EXISTS "UserProfiles" (user_id TEXT PRIMARY KEY, full_name TEXT DEFAULT '', profession TEXT DEFAULT '', income TEXT DEFAULT '', employer TEXT DEFAULT '', move_in_date TEXT DEFAULT '', occupants TEXT DEFAULT '', pets TEXT DEFAULT '', cover_letter TEXT DEFAULT '', created_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE IF NOT EXISTS "AlertSubscriptions" (id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, city TEXT NOT NULL, max_price NUMERIC DEFAULT 0, furnished BOOLEAN DEFAULT FALSE, pets_allowed BOOLEAN DEFAULT FALSE, parking BOOLEAN DEFAULT FALSE, active BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE IF NOT EXISTS "WebListings" (id SERIAL PRIMARY KEY, portal TEXT NOT NULL, url TEXT UNIQUE NOT NULL, title TEXT DEFAULT '', price NUMERIC DEFAULT 0, city TEXT DEFAULT '', created_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE IF NOT EXISTS "UrlTokens" (id SERIAL PRIMARY KEY, token TEXT UNIQUE NOT NULL, url TEXT NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW());
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS filter_furnished BOOLEAN DEFAULT FALSE;
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS filter_pets BOOLEAN DEFAULT FALSE;
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS filter_parking BOOLEAN DEFAULT FALSE;
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS work_address TEXT DEFAULT '';
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS balance NUMERIC DEFAULT 0;
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS vip BOOLEAN DEFAULT FALSE;
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS ref_code TEXT DEFAULT '';
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS referrals TEXT DEFAULT '[]';
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS last_paid_at NUMERIC DEFAULT 0;
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS last_activity NUMERIC DEFAULT 0;
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS vip_criteria TEXT DEFAULT '';
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS pdf_state TEXT DEFAULT '';
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS pdf_started_at NUMERIC DEFAULT 0;
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS vip_state TEXT DEFAULT '';
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS profile_state TEXT DEFAULT '';
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT '';
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS last_letter TEXT DEFAULT '';
ALTER TABLE "Favorites" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "ApplicationTracker" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "UserProfiles" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "AlertSubscriptions" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "WebListings" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "UrlTokens" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access on Favorites" ON "Favorites" FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access on ApplicationTracker" ON "ApplicationTracker" FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access on UserProfiles" ON "UserProfiles" FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access on AlertSubscriptions" ON "AlertSubscriptions" FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access on WebListings" ON "WebListings" FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access on UrlTokens" ON "UrlTokens" FOR ALL USING (auth.role() = 'service_role');

-- Listing history (for trends and holy grail tracking)
CREATE TABLE IF NOT EXISTS "ListingHistory" (
  id SERIAL PRIMARY KEY,
  url TEXT DEFAULT '',
  city TEXT DEFAULT '',
  price NUMERIC DEFAULT 0,
  score INTEGER DEFAULT 0,
  timestamp NUMERIC DEFAULT 0,
  is_holy_grail BOOLEAN DEFAULT FALSE,
  grail_reason TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE "ListingHistory" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access on ListingHistory" ON "ListingHistory" FOR ALL USING (auth.role() = 'service_role');

-- Price trends per city
CREATE TABLE IF NOT EXISTS "PriceTrends" (
  id SERIAL PRIMARY KEY,
  city TEXT UNIQUE NOT NULL,
  prices JSONB DEFAULT '[]',
  avg NUMERIC DEFAULT 0,
  trend TEXT DEFAULT 'stable',
  trend_pct NUMERIC DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE "PriceTrends" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access on PriceTrends" ON "PriceTrends" FOR ALL USING (auth.role() = 'service_role');

-- User city filters
CREATE TABLE IF NOT EXISTS "UserCities" (
  id SERIAL PRIMARY KEY,
  user_id TEXT UNIQUE NOT NULL,
  city TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE "UserCities" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access on UserCities" ON "UserCities" FOR ALL USING (auth.role() = 'service_role');
