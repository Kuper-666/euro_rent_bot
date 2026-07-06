"""
Единый Supabase клиент с кешированием.
Используй вместо создания отдельных клиентов в каждом модуле.
"""
import os
import logging

logger = logging.getLogger(__name__)

_client = None


def get_supabase():
    """Возвращает кешированный Supabase client или None."""
    global _client
    if _client is not None:
        return _client

    try:
        import dns_fix  # noqa: F401
    except ImportError:
        pass

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        logger.debug("SUPABASE_URL/SUPABASE_KEY not set")
        return None

    try:
        from supabase import create_client
        _client = create_client(url, key)
        logger.info("Supabase client connected")
        return _client
    except Exception as e:
        logger.warning("Supabase connection failed: %s", e)
        return None
