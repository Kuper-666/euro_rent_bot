---
name: supabase-migration
description: Use when migrating data from local JSON files to Supabase, creating new tables, or fixing Supabase connection issues
---

# Supabase Migration Skill

## Overview
Миграция данных из локальных JSON-файлов в Supabase с fallback на JSON для локальной разработки.

## When to Use
- Данные хранятся в JSON и теряются при перезапуске на Render
- Нужно создать новую таблицу в Supabase
- Supabase не подключается (DNS, credentials)
- Нужно сделать Supabase запросы идемпотентными

## Core Pattern

### 1. Создание таблицы (SQL)
```sql
CREATE TABLE IF NOT EXISTS "TableName" (
  id SERIAL PRIMARY KEY,
  field TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE "TableName" ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Service role full access on TableName' AND tablename = 'TableName') THEN
    CREATE POLICY "Service role full access on TableName" ON "TableName" FOR ALL USING (auth.role() = 'service_role');
  END IF;
END $$;
```

### 2. Python-модуль с fallback
```python
def _get_sb():
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if url and key:
            return create_client(url, key)
    except Exception:
        pass
    return None

def load_data():
    sb = _get_sb()
    if sb:
        try:
            result = sb.table("Table").select("*").execute()
            return result.data
        except Exception:
            pass
    return _load_json("local.json", default)
```

### 3. DNS fix для Windows
```python
import dns_fix  # В самом начале файла
```

## Quick Reference

| Действие | Команда |
|----------|---------|
| Проверить подключение | `sb.table("Users").select("*").limit(1).execute()` |
| Вставить запись | `sb.table("Table").insert({...}).execute()` |
| Обновить запись | `sb.table("Table").update({...}).eq("id", id).execute()` |
| Удалить запись | `sb.table("Table").delete().eq("id", id).execute()` |

## Common Mistakes
- Нет `IF NOT EXISTS` → ошибка при повторном запуске
- Нет RLS политики → анонимный доступ запрещён
- Нет fallback на JSON → крэш при отсутствии Supabase
- DNS не резолвится → нужен `dns_fix.py`
