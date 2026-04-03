import streamlit as st
from supabase import create_client, Client

_client: Client | None = None


def _get_credentials() -> tuple[str, str]:
    return st.secrets["supabase"]["url"], st.secrets["supabase"]["key"]


def get_client() -> Client:
    global _client
    if _client is None:
        url, key = _get_credentials()
        _client = create_client(url, key)
    return _client


def is_scraping_enabled() -> bool:
    return st.secrets.get("supabase", {}).get("scraping_enabled", False)
