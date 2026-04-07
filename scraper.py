"""
Scraper pour l'annuaire des Vignerons Indépendants de France.

Architecture :
- Listing  : API REST GET /api/pager/winemaker_list_page  (JSON, pas de JS nécessaire)
- Détails  : HTML server-side /annuaire-.../{slug}        (pas de JS nécessaire)

Aucun navigateur headless requis — requests suffit.
"""

import re
import time
import math
import threading
import multiprocessing
import concurrent.futures
from urllib.parse import urljoin

import requests
import httpx

# Session thread-locale : chaque thread worker a la sienne (requests.Session n'est pas thread-safe)
_thread_local = threading.local()

BASE_URL = "https://www.vignerons-independants.com"
LISTING_API = f"{BASE_URL}/api/pager/winemaker_list_page"
DETAIL_BASE = f"{BASE_URL}/annuaire-des-vignerons-independants-de-france"
DIRECTORY_URL = DETAIL_BASE

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Referer": DIRECTORY_URL,
}

# ──────────────────────────────────────────────
# Sessions HTTP
# ──────────────────────────────────────────────

def _make_session() -> requests.Session:
    """Session pour le listing API (thread principal uniquement)."""
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS)
    try:
        s.get(DIRECTORY_URL, timeout=30)
    except Exception:
        pass
    return s


def _get_thread_session() -> requests.Session:
    """
    Session propre au thread courant pour scraper les fiches détail.
    requests.Session n'est pas thread-safe — chaque worker a la sienne.
    """
    if not hasattr(_thread_local, "session"):
        s = requests.Session()
        s.headers.update(DEFAULT_HEADERS)
        _thread_local.session = s
    return _thread_local.session


# ──────────────────────────────────────────────
# Listing des producteurs via l'API
# ──────────────────────────────────────────────

def fetch_all_producers(
    progress_callback=None,
    max_pages: int = None,
    filters: dict = None,
) -> list[dict]:
    """
    Récupère la liste de tous les producteurs via l'API de pagination.

    Args:
        progress_callback : fonction(page_num, total_pages, n_producers)
        max_pages         : limiter le nombre de pages (None = tout)
        filters           : dict ex: {"wine_region": "alsace"}

    Returns:
        list[dict] — un dict normalisé par producteur
    """
    session = _make_session()
    producers: list[dict] = []

    # Première page pour connaître le total
    first = _fetch_page(session, 1, filters)
    if first is None:
        return producers

    total_pages = first.get("totalPages", 1)
    if max_pages:
        total_pages = min(total_pages, max_pages)

    for item in first.get("items", []):
        producers.append(_normalize(item))

    if progress_callback:
        progress_callback(1, total_pages, len(producers))

    # Pages suivantes
    for page_num in range(2, total_pages + 1):
        time.sleep(0.3)  # politesse
        data = _fetch_page(session, page_num, filters)
        if data is None:
            break
        for item in data.get("items", []):
            producers.append(_normalize(item))
        if progress_callback:
            progress_callback(page_num, total_pages, len(producers))

    return producers


def _fetch_page(session: requests.Session, page: int, filters: dict = None) -> dict | None:
    """Appelle l'API et retourne le JSON brut."""
    params = {
        "winemaker_list_page[page]": page,
        "winemaker_list_page[limit]": 24,
    }
    if filters:
        for k, v in filters.items():
            params[f"winemaker_list_page[filters][{k}][]"] = v

    try:
        r = session.get(
            LISTING_API,
            params=params,
            headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[API] Erreur page {page}: {e}")
        return None


def _normalize(raw: dict) -> dict:
    """Transforme un item brut de l'API en dict propre."""
    fields = raw.get("fields", {})

    # Reconstruire l'URL de la fiche à partir du slug dans url_s
    url_s = fields.get("url_s", "")
    slug = url_s.split("/")[-1] if url_s else ""
    url_fiche = f"{DETAIL_BASE}/{slug}" if slug else ""

    # Région : nettoyer "sud_ouest_armagnac" → "Sud-Ouest Armagnac"
    region_raw = fields.get("wine_region_s", "")
    region = region_raw.replace("_", " ").title() if region_raw else ""

    # Appellations (liste)
    appellations = fields.get("appellations_ms", [])
    appellation_str = ", ".join(appellations) if isinstance(appellations, list) else ""

    # Couleurs de vins
    colors_raw = fields.get("colors_ms", [])
    colors = [c.replace("color_", "").title() for c in colors_raw]
    colors_str = ", ".join(colors)

    # Adresse
    address = fields.get("address_s", "")
    # Extraire commune (avant le code pays)
    commune, departement, code_postal = "", "", ""
    m = re.search(r"(\d{5})\s+([A-ZÀÂÉÊÈÙÔÎ\s\-]+?)(?:\s+France)?$", address)
    if m:
        code_postal = m.group(1)
        commune = m.group(2).strip().title()
        departement = code_postal[:2]

    return {
        "nom": fields.get("name_s", ""),
        "region": region,
        "appellation": appellation_str,
        "commune": commune,
        "code_postal": code_postal,
        "departement": departement,
        "adresse_complete": address,
        "couleurs": colors_str,
        "nb_vins": fields.get("wines_count_i", ""),
        "a_email": fields.get("has_email_b", False),
        "latitude": fields.get("location_gl", {}).get("latitude", ""),
        "longitude": fields.get("location_gl", {}).get("longitude", ""),
        "url_fiche": url_fiche,
        "slug": slug,
    }


# ──────────────────────────────────────────────
# Détails d'une fiche producteur
# ──────────────────────────────────────────────

def scrape_producer_details(url: str) -> dict:
    """
    Scrape la page de détail d'un producteur et retourne ses coordonnées.
    Utilise uniquement requests (HTML server-side).
    """
    session = _make_session()
    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
        return _parse_detail_html(r.text, url)
    except Exception as e:
        return {"erreur": str(e), "url": url}


ITEM_TIMEOUT = 20  # secondes max par fiche avant kill du process


def _worker_process(url: str, queue: multiprocessing.Queue) -> None:
    """
    Tourne dans un process séparé. Résultat mis dans queue.
    Peut être tué proprement avec process.kill() si blocage.
    """
    try:
        s = requests.Session()
        s.headers.update(DEFAULT_HEADERS)
        r = s.get(url, timeout=(5, 15))
        r.raise_for_status()
        queue.put(_parse_detail_html(r.text, url))
    except Exception as e:
        queue.put({"erreur": str(e)[:80], "url": url})


def _fetch_one_process(url: str) -> dict:
    """
    Lance _worker_process dans un process séparé.
    Attend ITEM_TIMEOUT s, tue le process si toujours bloqué.
    Garantit un retour en moins de ITEM_TIMEOUT s sur Windows.
    """
    ctx = multiprocessing.get_context("spawn")
    q   = ctx.Queue()
    p   = ctx.Process(target=_worker_process, args=(url, q), daemon=True)
    p.start()
    p.join(timeout=ITEM_TIMEOUT)
    if p.is_alive():
        p.kill()
        p.join()
        return {"erreur": f"timeout >{ITEM_TIMEOUT}s — process tué", "url": url}
    try:
        return q.get_nowait()
    except Exception:
        return {"erreur": "pas de résultat", "url": url}


def scrape_producer_details_batch(
    urls: list[str],
    progress_callback=None,
    item_callback=None,
    start_callback=None,
    max_workers: int = 4,
) -> dict:
    """
    Scrape les fiches par mini-lots. Chaque fiche tourne dans un process
    séparé qui peut être tué si bloqué — timeout garanti sur Windows.
    """
    results = {}
    total   = len(urls)
    done    = 0

    for i in range(0, total, max_workers):
        mini   = urls[i : i + max_workers]
        bucket : dict[str, dict] = {}

        # Lancer un thread par URL (chaque thread lance son propre process)
        threads = []
        for url in mini:
            if start_callback:
                start_callback(url)

            def _run(u=url):
                bucket[u] = _fetch_one_process(u)

            t = threading.Thread(target=_run, daemon=True)
            threads.append((url, t))
            t.start()

        # Attendre la fin de chaque thread (le process interne a déjà son timeout)
        # +5s de marge au cas où le spawn est lent
        for url, t in threads:
            t.join(timeout=ITEM_TIMEOUT + 5)
            result  = bucket.get(url) or {"erreur": "timeout thread", "url": url}
            results[url] = result
            done   += 1
            if progress_callback:
                progress_callback(done, total)
            if item_callback:
                item_callback(url, result)

        time.sleep(0.2)

    return results


def _parse_detail_html(html: str, url: str) -> dict:
    """Extrait les coordonnées depuis le HTML d'une fiche producteur."""
    info: dict = {"url": url}

    # Restreindre au contenu avant le footer pour éviter de capturer
    # les liens du site (réseaux sociaux, etc.)
    footer_pos = html.find("<footer")
    main_html = html[:footer_pos] if footer_pos > 0 else html

    # ── Nom ──
    m = re.search(r'<h1[^>]*>\s*<span>([^<]+)</span>', main_html)
    if m:
        info["nom_fiche"] = m.group(1).strip()

    # ── Nom du producteur (ul.winemaker-profile__names) ──
    m_owner = re.search(
        r'<ul[^>]*class=["\'][^"\']*winemaker-profile__names[^"\']*["\'][^>]*>(.*?)</ul>',
        main_html, re.DOTALL
    )
    if m_owner:
        texts = re.findall(r'<li[^>]*>(.*?)</li>', m_owner.group(1), re.DOTALL)
        parts = [re.sub(r'<[^>]+>', '', t).strip() for t in texts]
        parts = [p for p in parts if p]
        if parts:
            info["nom_producteur"] = ", ".join(parts)

    # ── Téléphone (fixe et mobile) via les blocs phoneNumber / cellPhoneNumber ──
    # Structure : <p id="phoneNumber|cellPhoneNumber"><span>XX XX XX XX XX</span>...
    for phone_id, key in [("phoneNumber", "telephone"), ("cellPhoneNumber", "telephone_mobile")]:
        m2 = re.search(
            r'id=["\']' + phone_id + r'["\'][^>]*>.*?<span[^>]*>([^<]{9,20})</span>',
            main_html, re.DOTALL
        )
        if m2:
            info[key] = m2.group(1).strip()
    # Fallback : href="tel:..." si les blocs phoneNumber absents
    if "telephone" not in info:
        phones = re.findall(r'href=["\']tel:([^"\']+)["\']', main_html)
        phones = [p.strip() for p in phones if len(p.strip()) >= 9]
        if phones:
            info["telephone"] = phones[0]
            if len(phones) > 1:
                info["telephone_mobile"] = phones[1]

    # ── Email ──
    mailtos = re.findall(r'href=["\']mailto:([^"\'?]+)["\']', main_html)
    mailtos = [e for e in mailtos if "vignerons-independants" not in e]
    if mailtos:
        info["email"] = mailtos[0].strip()

    # ── Site web ──
    # Lien <a class="map-link"> contenant le texte "Site web"
    EXCLUDED_DOMAINS = (
        "vignerons-independants", "facebook.com", "instagram.com",
        "youtube.com", "twitter.com", "linkedin.com",
        "google.com/maps", "maps.google", "goo.gl",
        "cookiebot.com", "sst.vignerons",
    )
    m3 = re.search(
        r'href=["\']'
        r'(https?://[^"\']+)'
        r'["\'][^>]*(?:class=["\'][^"\']*map-link[^"\']*["\']|target=["\']_blank["\'])'
        r'[^>]*>(?:\s*<[^>]+>\s*)*Site web',
        main_html, re.DOTALL
    )
    if not m3:
        m3 = re.search(
            r'(?:class=["\'][^"\']*map-link[^"\']*["\']|target=["\']_blank["\'])'
            r'[^>]*href=["\']'
            r'(https?://[^"\']+)'
            r'["\'][^>]*>(?:\s*<[^>]+>\s*)*Site web',
            main_html, re.DOTALL
        )
    if m3:
        candidate = m3.group(1)
        if not any(excl in candidate for excl in EXCLUDED_DOMAINS):
            info["site_web"] = candidate

    # ── Adresse ──
    m5 = re.search(r'class=["\'][^"\']*\baddress\b[^"\']*["\'][^>]*>\s*<p>([^<]+)</p>', main_html)
    if m5:
        info["adresse"] = m5.group(1).strip()
    else:
        m6 = re.search(r'class=["\']address["\'][^>]*>(.*?)</div>', main_html, re.DOTALL)
        if m6:
            info["adresse"] = re.sub(r'<[^>]+>', '', m6.group(1)).strip()

    # ── Réseaux sociaux (bloc social-networks-list du producteur uniquement) ──
    # Extraire le bloc <ul class="social-networks-list"> avant le footer
    socials = {}
    social_block_m = re.search(
        r'<ul[^>]*class=["\'][^"\']*social-networks-list[^"\']*["\'][^>]*>(.*?)</ul>',
        main_html, re.DOTALL
    )
    if social_block_m:
        social_block = social_block_m.group(1)
        for name, pattern in [
            ("facebook", r'href=["\']https?://(?:[a-z-]+\.)?facebook\.com/([^"\'?/][^"\']+)["\']'),
            ("instagram", r'href=["\']https?://(?:www\.)?instagram\.com/([^"\'?/][^"\']+)["\']'),
        ]:
            ms = re.search(pattern, social_block)
            if ms:
                handle = ms.group(1).rstrip("/")
                # Exclure les comptes du site lui-même
                if name.lower() not in handle.lower() and "vigneron" not in handle.lower():
                    socials[name] = f"https://www.{name}.com/{handle}/"
    if socials:
        info["reseaux_sociaux"] = socials

    # ── Description ──
    m7 = re.search(
        r'class=["\'][^"\']*(?:description|presentation|about)[^"\']*["\'][^>]*>(.*?)</div>',
        main_html, re.DOTALL | re.IGNORECASE
    )
    if m7:
        desc = re.sub(r'<[^>]+>', ' ', m7.group(1)).strip()
        desc = re.sub(r'\s+', ' ', desc)
        if len(desc) > 30:
            info["description"] = desc[:600] + ("..." if len(desc) > 600 else "")

    return info


# ──────────────────────────────────────────────
# Compat async (wrappers pour l'ancienne interface)
# Ces fonctions sont gardées pour compatibilité
# avec app.py si besoin, mais ne sont plus utilisées.
# ──────────────────────────────────────────────

async def _async_not_used():
    pass
