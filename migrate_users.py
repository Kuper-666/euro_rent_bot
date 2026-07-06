"""Миграция: добавление колонок lang, created_at, total_checks, email в таблицу Users."""
import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Set SUPABASE_URL and SUPABASE_KEY environment variables")
    exit(1)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# Проверяем текущие колонки
result = sb.table("Users").select("*").limit(1).execute()
if result.data:
    existing = list(result.data[0].keys())
    print(f"Текущие колонки: {existing}")
else:
    # Вставляем тестовую запись чтобы узнать колонки
    test = sb.table("Users").insert({"user_id": "0"}).execute()
    result = sb.table("Users").select("*").eq("user_id", "0").execute()
    existing = list(result.data[0].keys()) if result.data else []
    print(f"Текущие колонки: {existing}")
    # Удаляем тестовую запись
    sb.table("Users").delete().eq("user_id", "0").execute()

# Новые колонки которые нужно добавить
new_columns = {
    "lang": "",
    "created_at": "2026-01-01T00:00:00Z",
    "total_checks": 0,
    "email": "",
}

# Supabase Python клиент не поддерживает DDL.
# Обновим существующие записи чтобы добавить новые поля.
# Это автоматически создаст колонки при первом insert.

missing = [col for col in new_columns if col not in existing]
print(f"Отсутствующие колонки: {missing}")

if missing:
    print("\nSupabase Python клиент не поддерживает ALTER TABLE.")
    print("Выполни эти запросы в Supabase SQL Editor:")
    print()
    for col in missing:
        val = new_columns[col]
        if isinstance(val, str) and val.endswith("Z"):
            print(f'ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS {col} TIMESTAMPTZ DEFAULT NOW();')
        elif isinstance(val, int):
            print(f'ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS {col} INTEGER DEFAULT 0;')
        else:
            print(f'ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS {col} TEXT DEFAULT \'\';')
    print()
else:
    print("Все колонки уже есть!")
