-- Выполни этот SQL в Supabase Dashboard → SQL Editor
-- Добавляет персистентное хранение последнего проанализированного объявления
-- (раньше хранилось только в памяти процесса в _last_analyzed_url — терялось
-- при каждом рестарте/деплое/спин-дауне на Render).

ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS last_listing_url TEXT DEFAULT '';
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS last_listing_text TEXT DEFAULT '';
