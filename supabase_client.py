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
    # Injecter le token JWT de l'utilisateur connecté pour respecter le RLS
    token = st.session_state.get("auth_token")
    if token:
        _client.postgrest.auth(token)
    return _client


def refresh_auth() -> None:
    """Rafraîchit le token JWT si la session est sur le point d'expirer."""
    global _client
    if _client is None:
        return
    try:
        resp = _client.auth.refresh_session()
        if resp and resp.session:
            st.session_state["auth_token"] = resp.session.access_token
            _client.postgrest.auth(resp.session.access_token)
    except Exception:
        pass


def is_scraping_enabled() -> bool:
    return st.secrets.get("supabase", {}).get("scraping_enabled", False)
