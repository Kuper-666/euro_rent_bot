-- Выполни этот SQL в Supabase Dashboard → SQL Editor
-- Добавляет персистентное хранение времени последнего анти-спам
-- напоминания (раньше эти поля читались/писались в коде, но отсутствовали
-- в схеме Supabase — при каждом save_data()/load_data() значение тихо
-- терялось, из-за чего анти-спам защита от повторной отправки одного и
-- того же напоминания никогда не переживала следующий запуск планировщика
-- в продакшене).
--
-- DOUBLE PRECISION, не TIMESTAMPTZ — код пишет сюда time.time() (float,
-- секунды с эпохи Unix), не ISO-дату/Postgres timestamp; TIMESTAMPTZ
-- отклонил бы такую запись.

ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS last_reminder DOUBLE PRECISION DEFAULT 0;
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS last_limit_reminder DOUBLE PRECISION DEFAULT 0;
