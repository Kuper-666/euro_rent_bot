-- Включаем RLS обратно
ALTER TABLE "Users" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "UrlTokens" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "PendingListings" ENABLE ROW LEVEL SECURITY;

-- Политики для Users: service_role имеет полный доступ, anon только чтение
CREATE POLICY "Service role full access on Users"
ON "Users" FOR ALL
USING (auth.role() = 'service_role');

CREATE POLICY "Anon read access on Users"
ON "Users" FOR SELECT
USING (true);

-- Политики для UrlTokens
CREATE POLICY "Service role full access on UrlTokens"
ON "UrlTokens" FOR ALL
USING (auth.role() = 'service_role');

CREATE POLICY "Anon read access on UrlTokens"
ON "UrlTokens" FOR SELECT
USING (true);

-- Политики для PendingListings
CREATE POLICY "Service role full access on PendingListings"
ON "PendingListings" FOR ALL
USING (auth.role() = 'service_role');

CREATE POLICY "Anon read access on PendingListings"
ON "PendingListings" FOR SELECT
USING (true);
