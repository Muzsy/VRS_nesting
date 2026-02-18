from __future__ import annotations

from functools import lru_cache

from api.config import Settings, load_settings
from api.supabase_client import SupabaseClient


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


@lru_cache(maxsize=1)
def get_supabase_client() -> SupabaseClient:
    settings = get_settings()
    return SupabaseClient(base_url=settings.supabase_url, anon_key=settings.supabase_anon_key)
