"""
CRM Vignerons Indépendants — Application Streamlit + Supabase
"""

import time
from datetime import datetime, date

import pandas as pd
import streamlit as st

import db
from supabase_client import get_client, is_scraping_enabled, refresh_auth

# Scraping uniquement si activé (mode local)
if is_scraping_enabled():
    from scraper import fetch_all_producers, scrape_producer_details_batch

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Vignerons — CRM",
    page_icon="🍷",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.main .block-container { padding-top: 1.5rem; }
.stButton>button { width: 100%; }
</style>
""", unsafe_allow_html=True)

STATUTS = ["prospect", "contacté", "à relancer", "refus", "signé"]
STATUT_ICON = {
    "prospect":    "⚪",
    "contacté":    "🔵",
    "à relancer":  "🟠",
    "refus":       "🔴",
    "signé":       "🟢",
}
TYPES_INTERACTION = ["appel", "email", "visite", "message", "autre"]
TYPE_ICON = {
    "appel":   "📞",
    "email":   "📧",
    "visite":  "🚗",
    "message": "💬",
    "autre":   "📝",
}


# ──────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────
def render_login():
    """Écran de connexion — bloque l'accès tant que non authentifié."""
    col = st.columns([1, 1.2, 1])[1]
    with col:
        st.markdown("## 🍷 Vignerons — CRM")
        st.markdown("Connectez-vous pour accéder à l'application.")
        email    = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter", type="primary", use_container_width=True):
            if email and password:
                try:
                    resp = get_client().auth.sign_in_with_password(
                        {"email": email, "password": password}
                    )
                    st.session_state.auth_user  = resp.user
                    st.session_state.auth_token = resp.session.access_token
                    st.rerun()
                except Exception as e:
                    st.error(f"Identifiants incorrects. ({e})")
            else:
                st.warning("Renseignez email et mot de passe.")


def _logout():
    try:
        get_client().auth.sign_out()
    except Exception:
        pass
    for k in ["auth_user", "auth_token", "page", "selected_vigneron", "auteur"]:
        st.session_state.pop(k, None)
    st.rerun()


def _current_user_email() -> str:
    user = st.session_state.get("auth_user")
    return user.email if user else ""


# ──────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────
def _init_state():
    defaults = {
        "auth_user":  None,
        "auth_token": None,
        "page": "list",
        "selected_vigneron": None,
        "auteur": "",
        "f_search": "",
        "f_region": "Toutes régions",
        "f_dept":   "Tous depts",
        "f_statut": "Tous statuts",
        "f_phone":  False,
        "f_web":    False,
        "f_no_details": False,
        "last_viewed_id": None,
        "prospect_form_error": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v




_init_state()

# ── Vérification auth ──
if not st.session_state.auth_user:
    render_login()
    st.stop()


# ──────────────────────────────────────────────
# Cache DB
# ──────────────────────────────────────────────
@st.cache_data(ttl=15)
def load_vignerons():
    return db.get_all_vignerons()


@st.cache_data(ttl=5)
def load_interactions(vigneron_id: str):
    return db.get_interactions(vigneron_id)


def _refresh():
    st.cache_data.clear()
    st.rerun()


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def _fmt_date(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        delta = datetime.now(dt.tzinfo) - dt
        if delta.days == 0:
            return "Aujourd'hui"
        if delta.days == 1:
            return "Hier"
        if delta.days < 7:
            return f"Il y a {delta.days}j"
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return iso[:10]


def _statut_label(s: str) -> str:
    return f"{STATUT_ICON.get(s, '⚪')} {s.capitalize()}"


# ──────────────────────────────────────────────
# Sidebar commune
# ──────────────────────────────────────────────
def _sidebar_scraping():
    # ── Utilisateur connecté ──
    st.caption(f"👤 {_current_user_email()}")
    if st.button("Se déconnecter", use_container_width=True):
        _logout()
    st.divider()

    if not is_scraping_enabled():
        st.caption("🖥️ Mode cloud — scraping local uniquement.")
        st.divider()
        st.text_input("👤 Votre nom (interactions)", key="auteur")
        return

    st.header("⚙️ Scraping")

    max_pages = st.number_input(
        "Pages max", min_value=1, max_value=500, value=5,
        help="24 producteurs/page · 224 pages au total",
    )
    region_options = {
        "Toutes les régions": None,
        "Alsace": "alsace",
        "Auvergne": "auvergne",
        "Bordeaux": "bordeaux",
        "Bourgogne / Beaujolais": "bourgogne_beaujolais",
        "Champagne": "champagne",
        "Cognac / Charentes": "cognac_charentes",
        "Corse": "corse",
        "Jura": "jura",
        "Languedoc-Roussillon": "languedoc_roussillon",
        "Loire": "loire",
        "Provence": "provence",
        "Rhône": "rhone",
        "Savoie": "savoie",
        "Sud-Ouest": "sud_ouest",
    }
    selected_label = st.selectbox("Région", list(region_options.keys()))
    selected_region = region_options[selected_label]

    fetch_details = st.checkbox("📞 Récupérer les coordonnées", value=True)

    st.divider()
    if st.button("🔍 Lancer le scraping", type="primary"):
        _run_scraping(max_pages, selected_region, fetch_details)

    all_v = load_vignerons()
    sans_nom = sum(1 for v in all_v if not v.get("nom_producteur"))
    if st.button(f"👤 Récupérer les noms producteurs ({sans_nom} fiches)", type="secondary"):
        _run_scraping_noms()

    st.divider()
    st.text_input("👤 Votre nom (pour les interactions)", key="auteur")


MAX_WORKERS = 4


def _scrape_coordonnees(urls: list[str]) -> tuple[int, int]:
    """
    Scrape les coordonnées de toutes les URLs en un seul appel.
    Sauvegarde dans Supabase dès réception de chaque fiche.
    Retourne (n_tel, n_mail).
    """
    total   = len(urls)
    counters = {"tel": 0, "mail": 0}

    status_box  = st.empty()
    bar         = st.progress(0)
    inner_label = st.empty()
    inner_bar   = st.progress(0)
    log_box     = st.empty()
    statuses: dict[str, str] = {}

    def _render_log():
        lines = [f"{v}  —  `{k}`" for k, v in statuses.items()]
        log_box.markdown("\n\n".join(lines[-20:]))

    def on_start(url):
        slug = url.rstrip("/").split("/")[-1]
        statuses[slug] = "🔄 en cours…"

    def on_progress(done, _total):
        bar.progress(done / total)
        inner_label.caption(f"Fiche {done} / {total}")
        inner_bar.progress(done / total)
        status_box.info(
            f"📞 **{done} / {total}** fiches "
            f"({int(done/total*100)} %) · "
            f"✅ {counters['tel']} tél · {counters['mail']} emails"
        )

    _refresh_counter = {"n": 0}

    def on_each(url, result):
        _refresh_counter["n"] += 1
        if _refresh_counter["n"] % 50 == 0:
            refresh_auth()
        db.update_details(url, result)
        if not result.get("erreur"):
            if result.get("telephone"):
                counters["tel"] += 1
            if result.get("email"):
                counters["mail"] += 1
        slug = url.rstrip("/").split("/")[-1]
        tel  = result.get("telephone", "")
        err  = result.get("erreur", "")
        statuses[slug] = f"⚠️ {err[:60]}" if err else (f"✅ {tel}" if tel else "➖ pas de tél")
        _render_log()

    scrape_producer_details_batch(
        urls,
        progress_callback=on_progress,
        item_callback=on_each,
        start_callback=on_start,
        max_workers=MAX_WORKERS,
    )

    bar.progress(1.0)
    status_box.success(
        f"✅ {total} fiches · {counters['tel']} tél · {counters['mail']} emails"
    )
    st.cache_data.clear()
    return counters["tel"], counters["mail"]


def _run_scraping_noms():
    """Passe légère : scrape uniquement le nom_producteur sur toutes les fiches déjà en base."""
    all_db = db.get_all_vignerons()
    urls = [v["url_fiche"] for v in all_db if v.get("url_fiche") and not v.get("nom_producteur")]
    if not urls:
        st.warning("Aucune fiche en base.")
        return

    total = len(urls)
    status_box = st.empty()
    bar = st.progress(0)
    done = 0

    def on_progress(d, _):
        nonlocal done
        done = d
        bar.progress(d / total)
        status_box.info(f"👤 **{d} / {total}** fiches traitées")

    _refresh_counter = {"n": 0}

    def on_each(url, result):
        _refresh_counter["n"] += 1
        if _refresh_counter["n"] % 50 == 0:
            refresh_auth()
        nom = result.get("nom_producteur")
        if nom:
            db.update_nom_producteur(url, nom)

    scrape_producer_details_batch(
        urls,
        progress_callback=on_progress,
        item_callback=on_each,
        max_workers=MAX_WORKERS,
    )
    bar.progress(1.0)
    status_box.success(f"✅ Noms producteurs mis à jour sur {total} fiches.")
    st.cache_data.clear()
    time.sleep(1)
    st.rerun()


def _run_scraping(max_pages, selected_region, fetch_details):
    filters = {}
    if selected_region:
        filters["wine_region"] = selected_region

    status_box = st.empty()
    progress_bar = st.progress(0)

    status_box.info("⏳ Connexion à l'API vignerons-independants.com…")

    def on_progress(page_num, total_pages, n):
        progress_bar.progress(min(page_num / total_pages, 1.0))
        status_box.info(f"⏳ Page **{page_num}** / {total_pages} — **{n}** producteurs")

    producers = fetch_all_producers(
        progress_callback=on_progress,
        max_pages=int(max_pages),
        filters=filters or None,
    )
    progress_bar.progress(1.0)

    if not producers:
        status_box.error("❌ Aucun producteur trouvé.")
        return

    # Sauvegarder dans Supabase
    status_box.info(f"💾 Enregistrement de **{len(producers)}** producteurs dans Supabase…")
    db.upsert_vignerons(producers)
    status_box.success(f"✅ **{len(producers)}** producteurs enregistrés.")

    if fetch_details:
        all_db = db.get_all_vignerons()
        region_filter = selected_region.replace("_", " ").title() if selected_region else None
        urls_todo = [
            v["url_fiche"] for v in all_db
            if v.get("url_fiche")
            and not v.get("details_scrapped_at")
            and (not region_filter or v.get("region", "").lower() == region_filter.lower())
        ]
        if urls_todo:
            _scrape_coordonnees(urls_todo)

    st.cache_data.clear()
    time.sleep(1)
    st.rerun()


# ──────────────────────────────────────────────
# Page : Liste
# ──────────────────────────────────────────────
def render_list():
    with st.sidebar:
        _sidebar_scraping()

    col_title, col_btn = st.columns([5, 1])
    with col_title:
        st.title("🍷 Vignerons Indépendants — CRM")
    with col_btn:
        st.markdown("<div style='padding-top:14px'></div>", unsafe_allow_html=True)
        if st.button("➕ Nouveau prospect", type="primary", use_container_width=True):
            st.session_state.page = "add_prospect"
            st.rerun()

    vignerons = load_vignerons()
    if not vignerons:
        st.info("👈 Aucun producteur en base. Lancez le scraping depuis la barre latérale.")
        return

    # ── Filtres (index= explicite pour résister aux navigations de page) ──
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    with c1:
        f_search = st.text_input("🔎 Rechercher", value=st.session_state.f_search,
                                 label_visibility="collapsed", placeholder="Nom, région, commune…")
        st.session_state.f_search = f_search
    with c2:
        regions = ["Toutes régions"] + sorted({v.get("region", "") for v in vignerons if v.get("region")})
        r_idx = regions.index(st.session_state.f_region) if st.session_state.f_region in regions else 0
        f_region = st.selectbox("Région", regions, index=r_idx, label_visibility="collapsed")
        st.session_state.f_region = f_region
    with c3:
        depts = ["Tous depts"] + sorted({v.get("departement", "") for v in vignerons if v.get("departement")})
        d_idx = depts.index(st.session_state.f_dept) if st.session_state.f_dept in depts else 0
        f_dept = st.selectbox("Département", depts, index=d_idx, label_visibility="collapsed")
        st.session_state.f_dept = f_dept
    with c4:
        statut_opts = ["Tous statuts"] + STATUTS
        s_idx = statut_opts.index(st.session_state.f_statut) if st.session_state.f_statut in statut_opts else 0
        f_statut = st.selectbox("Statut", statut_opts, index=s_idx, label_visibility="collapsed")
        st.session_state.f_statut = f_statut

    c5, c6, c7 = st.columns([1, 1, 4])
    with c5:
        f_phone = st.checkbox("📞 Tél uniquement", value=st.session_state.f_phone)
        st.session_state.f_phone = f_phone
    with c6:
        f_web = st.checkbox("🌐 Site uniquement", value=st.session_state.f_web)
        st.session_state.f_web = f_web
    with c7:
        f_no_details = st.checkbox("Sans coordonnées (à scraper)", value=st.session_state.f_no_details)
        st.session_state.f_no_details = f_no_details

    # Filtrage
    filtered = vignerons
    if f_search:
        q = f_search.lower()
        filtered = [v for v in filtered if any(q in str(val).lower() for val in v.values())]
    if f_region != "Toutes régions":
        filtered = [v for v in filtered if v.get("region", "").lower() == f_region.lower()]
    if f_dept != "Tous depts":
        filtered = [v for v in filtered if v.get("departement", "") == f_dept]
    if f_statut != "Tous statuts":
        filtered = [v for v in filtered if v.get("statut") == f_statut]
    if f_phone:
        filtered = [v for v in filtered if v.get("telephone")]
    if f_web:
        filtered = [v for v in filtered if v.get("site_web")]
    if f_no_details:
        filtered = [v for v in filtered if not v.get("details_scrapped_at")]

    # ── Métriques ──
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total", len(filtered))
    m2.metric("🔵 Contactés",   sum(1 for v in filtered if v.get("statut") == "contacté"))
    m3.metric("🟠 À relancer",  sum(1 for v in filtered if v.get("statut") == "à relancer"))
    m4.metric("🟢 Signés",      sum(1 for v in filtered if v.get("statut") == "signé"))
    m5.metric("🔴 Refus",       sum(1 for v in filtered if v.get("statut") == "refus"))

    # ── Tableau ──
    st.caption(f"**{len(filtered)}** producteur(s)")

    rows = []
    for v in filtered:
        rows.append({
            "Statut":               f"{STATUT_ICON.get(v.get('statut','prospect'), '⚪')} {(v.get('statut') or 'prospect').capitalize()}",
            "Nom":                  v.get("nom", ""),
            "Producteur":           v.get("nom_producteur", ""),
            "Région":               v.get("region", ""),
            "Commune":              v.get("commune", ""),
            "Téléphone":            v.get("telephone", ""),
            "Site web":             v.get("site_web", ""),
            "Dernière interaction": f"{TYPE_ICON.get(v.get('derniere_interaction_type',''), '')} {v.get('derniere_interaction_type','') or ''}".strip(),
            "Date":                 _fmt_date(v.get("derniere_interaction_at")),
        })

    df = pd.DataFrame(rows)
    df.index = range(1, len(df) + 1)

    event = st.dataframe(
        df,
        use_container_width=True,
        height=480,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Site web": st.column_config.LinkColumn("Site web", display_text="🌐 Ouvrir"),
        },
    )

    selected_rows = event.selection.get("rows", []) if hasattr(event, "selection") else []
    if selected_rows:
        st.session_state.last_viewed_id = filtered[selected_rows[0]]["id"]
        st.session_state.selected_vigneron = filtered[selected_rows[0]]
        st.session_state.page = "fiche"
        st.rerun()

    # ── Scroll au dernier vigneron consulté ──
    if st.session_state.last_viewed_id:
        scroll_row = next(
            (i for i, v in enumerate(filtered) if v["id"] == st.session_state.last_viewed_id),
            0,
        )
        if scroll_row > 0:
            st.components.v1.html(f"""
            <script>
                setTimeout(function() {{
                    const dfs = window.parent.document.querySelectorAll('[data-testid="stDataFrame"]');
                    if (dfs.length > 0) {{
                        const scroller = dfs[0].querySelector('.dvn-scroller');
                        if (scroller) scroller.scrollTop = {scroll_row * 36};
                    }}
                }}, 300);
            </script>
            """, height=0)

    # ── Scraping coordonnées sur la sélection ──
    st.divider()
    urls_sans_details = [v["url_fiche"] for v in filtered if v.get("url_fiche") and not v.get("details_scrapped_at")]
    col_sc1, col_sc2 = st.columns([2, 3])
    with col_sc1:
        st.caption(f"**{len(urls_sans_details)}** fiche(s) sans coordonnées dans la sélection")
        if urls_sans_details and is_scraping_enabled() and st.button(f"📞 Charger les coordonnées ({len(urls_sans_details)} fiches)", type="secondary"):
            _scrape_coordonnees(urls_sans_details)
            _refresh()

    # ── Export CSV ──
    col_exp, _ = st.columns([1, 3])
    with col_exp:
        export_rows = []
        for v in filtered:
            export_rows.append({
                "nom": v.get("nom"), "region": v.get("region"),
                "appellation": v.get("appellation"), "commune": v.get("commune"),
                "code_postal": v.get("code_postal"), "departement": v.get("departement"),
                "adresse_complete": v.get("adresse_complete"),
                "telephone": v.get("telephone"), "telephone_mobile": v.get("telephone_mobile"),
                "email": v.get("email"), "site_web": v.get("site_web"),
                "facebook": v.get("facebook"), "instagram": v.get("instagram"),
                "couleurs": v.get("couleurs"), "nb_vins": v.get("nb_vins"),
                "statut": v.get("statut"),
                "derniere_interaction": v.get("derniere_interaction_type"),
                "derniere_interaction_date": (v.get("derniere_interaction_at") or "")[:10],
                "url_fiche": v.get("url_fiche"),
            })
        csv = pd.DataFrame(export_rows).to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            "📥 Exporter CSV",
            data=csv,
            file_name="vignerons_crm.csv",
            mime="text/csv",
        )


# ──────────────────────────────────────────────
# Page : Fiche vigneron
# ──────────────────────────────────────────────
def render_fiche():
    v = st.session_state.selected_vigneron
    if not v:
        st.session_state.page = "list"
        st.rerun()

    # Recharger depuis la DB pour avoir les données fraîches
    all_v = load_vignerons()
    v_fresh = next((x for x in all_v if x["id"] == v["id"]), v)
    vigneron_id = v_fresh["id"]

    # ── Header compact : retour | titre + producteur | statut ──
    h1, h2, h3 = st.columns([1, 4, 2])
    with h1:
        st.markdown("<div style='padding-top:6px'></div>", unsafe_allow_html=True)
        if st.button("← Liste", use_container_width=True):
            st.session_state.page = "list"
            st.session_state.selected_vigneron = None
            st.rerun()
    with h2:
        nom_producteur = v_fresh.get("nom_producteur", "")
        st.markdown(
            f"### 🍾 {v_fresh.get('nom', '')}"
            + (f"<br><span style='font-size:.85rem;color:gray'>👤 {nom_producteur}</span>" if nom_producteur else ""),
            unsafe_allow_html=True,
        )
    with h3:
        current_statut = v_fresh.get("statut") or "prospect"
        new_statut = st.selectbox(
            "Statut", STATUTS,
            index=STATUTS.index(current_statut),
            format_func=_statut_label,
            label_visibility="collapsed",
        )
        if new_statut != current_statut:
            db.update_statut(vigneron_id, new_statut)
            _refresh()

    st.divider()

    col_info, col_inter = st.columns([2, 3])

    # ── Colonne gauche : infos + coordonnées ──
    with col_info:
        # Coordonnées en priorité
        tel = v_fresh.get("telephone")
        mob = v_fresh.get("telephone_mobile")
        mail = v_fresh.get("email")
        web = v_fresh.get("site_web")
        fb = v_fresh.get("facebook")
        ig = v_fresh.get("instagram")

        if tel:
            clean = tel.replace(" ", "").replace(".", "")
            st.markdown(f"📞 [{tel}](tel:{clean})")
        if mob:
            clean_m = mob.replace(" ", "").replace(".", "")
            st.markdown(f"📱 [{mob}](tel:{clean_m})")
        if mail:
            st.markdown(f"📧 [{mail}](mailto:{mail})")
        if web:
            st.markdown(f"🌐 [{web}]({web})")
        if fb or ig:
            links = []
            if fb:
                links.append(f"[Facebook]({fb})")
            if ig:
                links.append(f"[Instagram]({ig})")
            st.markdown("  ·  ".join(links))
        if not any([tel, mob, mail, web]):
            st.caption("Aucune coordonnée — lancez le scraping des fiches.")

        st.divider()

        # Infos secondaires
        for label, key in [
            ("Région", "region"), ("Appellation", "appellation"),
            ("Commune", "commune"), ("Couleurs", "couleurs"), ("Nb vins", "nb_vins"),
        ]:
            val = v_fresh.get(key)
            if val:
                st.caption(f"**{label}** : {val}")

        if v_fresh.get("adresse_complete"):
            st.caption(f"📍 {v_fresh['adresse_complete']}")

        if v_fresh.get("url_fiche"):
            st.markdown(f"[🔗 Fiche sur le site]({v_fresh['url_fiche']})")

        if v_fresh.get("description"):
            with st.expander("📄 Description"):
                st.write(v_fresh["description"])

    # ── Colonne droite : formulaire en haut, historique scrollable ──
    with col_inter:
        # Formulaire d'ajout
        with st.form("add_interaction", clear_on_submit=True):
            fi1, fi2, fi3 = st.columns([2, 2, 2])
            with fi1:
                inter_type = st.selectbox(
                    "Type", TYPES_INTERACTION,
                    format_func=lambda t: f"{TYPE_ICON[t]} {t.capitalize()}",
                )
            with fi2:
                inter_date = st.date_input("Date", value=date.today())
            with fi3:
                inter_auteur = st.text_input(
                    "Auteur",
                    value=st.session_state.get("auteur", ""),
                    placeholder="Votre nom",
                )
            inter_notes = st.text_area("Notes", height=60, placeholder="Résumé de l'échange…")
            submitted = st.form_submit_button("➕ Ajouter", type="primary", use_container_width=True)
            if submitted:
                if not inter_auteur.strip():
                    st.warning("Indiquez votre nom.")
                else:
                    db.add_interaction(
                        vigneron_id=vigneron_id,
                        type_=inter_type,
                        date_str=datetime.combine(inter_date, datetime.min.time()).isoformat(),
                        notes=inter_notes.strip(),
                        auteur=inter_auteur.strip(),
                    )
                    st.session_state.auteur = inter_auteur.strip()
                    _refresh()

        st.caption("🗓️ **Historique**")

        # Historique dans un conteneur scrollable
        interactions = load_interactions(vigneron_id)
        if not interactions:
            st.caption("Aucune interaction enregistrée.")
        else:
            scroll_css = (
                "<style>.inter-scroll{max-height:340px;overflow-y:auto;}</style>"
                "<div class='inter-scroll'>"
            )
            st.markdown(scroll_css, unsafe_allow_html=True)
            for inter in interactions:
                icon = TYPE_ICON.get(inter.get("type", ""), "📝")
                dt = _fmt_date(inter.get("date"))
                type_label = (inter.get("type") or "autre").capitalize()
                auteur = inter.get("auteur") or ""
                notes = inter.get("notes") or ""

                with st.container(border=True):
                    h1, h2 = st.columns([5, 1])
                    with h1:
                        st.markdown(
                            f"{icon} **{type_label}** · {dt}"
                            + (f" · *{auteur}*" if auteur else "")
                        )
                        if notes:
                            st.caption(notes)
                    with h2:
                        if st.button("🗑️", key=f"del_{inter['id']}", help="Supprimer"):
                            db.delete_interaction(inter["id"], vigneron_id)
                            _refresh()
            st.markdown("</div>", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Page : Nouveau prospect
# ──────────────────────────────────────────────
def render_add_prospect():
    with st.sidebar:
        _sidebar_scraping()

    h1, h2 = st.columns([1, 6])
    with h1:
        st.markdown("<div style='padding-top:6px'></div>", unsafe_allow_html=True)
        if st.button("← Liste", use_container_width=True):
            st.session_state.page = "list"
            st.rerun()
    with h2:
        st.markdown("### ➕ Nouveau prospect")

    st.divider()

    all_v = load_vignerons()
    regions_existantes = sorted({v.get("region", "") for v in all_v if v.get("region")})

    with st.form("form_add_prospect", clear_on_submit=False):
        st.markdown("#### Domaine")
        c1, c2 = st.columns(2)
        with c1:
            nom = st.text_input("Nom du domaine *", placeholder="Ex : Domaine des Terres Rouges")
        with c2:
            nom_producteur = st.text_input("Nom du producteur", placeholder="Ex : Jean Dupont")

        st.markdown("#### Coordonnées")
        c3, c4 = st.columns(2)
        with c3:
            telephone = st.text_input("Téléphone fixe", placeholder="03 89 XX XX XX")
            email = st.text_input("Email", placeholder="contact@domaine.fr")
        with c4:
            telephone_mobile = st.text_input("Téléphone mobile", placeholder="06 XX XX XX XX")
            site_web = st.text_input("Site web", placeholder="https://www.domaine.fr")

        c5, c6 = st.columns(2)
        with c5:
            facebook = st.text_input("Facebook", placeholder="https://facebook.com/…")
        with c6:
            instagram = st.text_input("Instagram", placeholder="https://instagram.com/…")

        st.markdown("#### Localisation")
        c7, c8, c9 = st.columns(3)
        with c7:
            region_options = [""] + regions_existantes + ["Autre…"]
            region_select = st.selectbox("Région", region_options, format_func=lambda x: x if x else "— Choisir —")
            if region_select == "Autre…":
                region = st.text_input("Préciser la région")
            else:
                region = region_select
        with c8:
            appellation = st.text_input("Appellation", placeholder="Ex : Alsace Grand Cru")
        with c9:
            commune = st.text_input("Commune", placeholder="Ex : Ribeauvillé")

        c10, c11 = st.columns(2)
        with c10:
            code_postal = st.text_input("Code postal", placeholder="68150")
        with c11:
            departement = st.text_input("Département", placeholder="Haut-Rhin")

        adresse_complete = st.text_input("Adresse complète", placeholder="12 rue des Vignes, 68150 Ribeauvillé")

        st.markdown("#### CRM")
        statut = st.selectbox(
            "Statut initial",
            STATUTS,
            index=0,
            format_func=_statut_label,
        )

        st.divider()
        submitted = st.form_submit_button("💾 Créer le prospect", type="primary", use_container_width=True)

    if submitted:
        if not nom.strip():
            st.error("Le nom du domaine est obligatoire.")
        else:
            new_id = db.add_prospect({
                "nom":              nom.strip(),
                "nom_producteur":   nom_producteur.strip(),
                "telephone":        telephone.strip(),
                "telephone_mobile": telephone_mobile.strip(),
                "email":            email.strip(),
                "site_web":         site_web.strip(),
                "facebook":         facebook.strip(),
                "instagram":        instagram.strip(),
                "region":           region.strip(),
                "appellation":      appellation.strip(),
                "commune":          commune.strip(),
                "code_postal":      code_postal.strip(),
                "departement":      departement.strip(),
                "adresse_complete": adresse_complete.strip(),
                "statut":           statut,
            })
            st.cache_data.clear()
            # Ouvrir directement la fiche du nouveau prospect
            all_fresh = db.get_all_vignerons()
            new_v = next((v for v in all_fresh if v["id"] == new_id), None)
            if new_v:
                st.session_state.selected_vigneron = new_v
                st.session_state.last_viewed_id = new_id
                st.session_state.page = "fiche"
            else:
                st.session_state.page = "list"
            st.rerun()


# ──────────────────────────────────────────────
# Routeur principal
# ──────────────────────────────────────────────
if st.session_state.page == "fiche" and st.session_state.selected_vigneron:
    render_fiche()
elif st.session_state.page == "add_prospect":
    render_add_prospect()
else:
    render_list()
