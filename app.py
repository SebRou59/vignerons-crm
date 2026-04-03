"""
CRM Vignerons Indépendants — Application Streamlit + Supabase
"""

import time
from datetime import datetime, date

import pandas as pd
import streamlit as st

import db
from supabase_client import get_client, is_scraping_enabled

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

    def on_each(url, result):
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
        urls_todo = [
            v["url_fiche"] for v in all_db
            if v.get("url_fiche") and not v.get("details_scrapped_at")
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

    st.title("🍷 Vignerons Indépendants — CRM")

    vignerons = load_vignerons()
    if not vignerons:
        st.info("👈 Aucun producteur en base. Lancez le scraping depuis la barre latérale.")
        return

    # ── Filtres (persistés dans session state) ──
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    with c1:
        search = st.text_input("🔎 Rechercher", value=st.session_state.f_search,
                               label_visibility="collapsed", placeholder="Nom, région, commune…",
                               key="f_search")
    with c2:
        regions = ["Toutes régions"] + sorted({v.get("region", "") for v in vignerons if v.get("region")})
        region_f = st.selectbox("Région", regions, label_visibility="collapsed",
                                index=regions.index(st.session_state.f_region) if st.session_state.f_region in regions else 0,
                                key="f_region")
    with c3:
        depts = ["Tous depts"] + sorted({v.get("departement", "") for v in vignerons if v.get("departement")})
        dept_f = st.selectbox("Département", depts, label_visibility="collapsed",
                              index=depts.index(st.session_state.f_dept) if st.session_state.f_dept in depts else 0,
                              key="f_dept")
    with c4:
        statut_opts = ["Tous statuts"] + STATUTS
        statut_f = st.selectbox("Statut", statut_opts, label_visibility="collapsed",
                                index=statut_opts.index(st.session_state.f_statut) if st.session_state.f_statut in statut_opts else 0,
                                key="f_statut")

    c5, c6, c7 = st.columns([1, 1, 4])
    with c5:
        only_phone = st.checkbox("📞 Tél uniquement", key="f_phone")
    with c6:
        only_web = st.checkbox("🌐 Site uniquement", key="f_web")
    with c7:
        only_no_details = st.checkbox("Sans coordonnées (à scraper)", key="f_no_details")

    # Filtrage
    filtered = vignerons
    if search:
        q = search.lower()
        filtered = [v for v in filtered if any(q in str(val).lower() for val in v.values())]
    if region_f != "Toutes régions":
        filtered = [v for v in filtered if v.get("region", "").lower() == region_f.lower()]
    if dept_f != "Tous depts":
        filtered = [v for v in filtered if v.get("departement", "") == dept_f]
    if statut_f != "Tous statuts":
        filtered = [v for v in filtered if v.get("statut") == statut_f]
    if only_phone:
        filtered = [v for v in filtered if v.get("telephone")]
    if only_web:
        filtered = [v for v in filtered if v.get("site_web")]
    if only_no_details:
        filtered = [v for v in filtered if not v.get("details_scrapped_at")]

    # ── Métriques ──
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total", len(filtered))
    m2.metric("🔵 Contactés",   sum(1 for v in filtered if v.get("statut") == "contacté"))
    m3.metric("🟠 À relancer",  sum(1 for v in filtered if v.get("statut") == "à relancer"))
    m4.metric("🟢 Signés",      sum(1 for v in filtered if v.get("statut") == "signé"))
    m5.metric("🔴 Refus",       sum(1 for v in filtered if v.get("statut") == "refus"))

    # ── Tableau ──
    st.caption(
        f"**{len(filtered)}** producteur(s) · "
        "☑ Cochez une ou plusieurs lignes pour charger les coordonnées · "
        "Cochez une seule ligne pour ouvrir la fiche"
    )

    rows = []
    for v in filtered:
        rows.append({
            "Statut":               f"{STATUT_ICON.get(v.get('statut','prospect'), '⚪')} {(v.get('statut') or 'prospect').capitalize()}",
            "Nom":                  v.get("nom", ""),
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
        st.session_state.selected_vigneron = filtered[selected_rows[0]]
        st.session_state.page = "fiche"
        st.rerun()

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

    # ── Navigation ──
    if st.button("← Retour à la liste"):
        st.session_state.page = "list"
        st.session_state.selected_vigneron = None
        st.rerun()

    st.title(f"🍾 {v_fresh.get('nom', '')}")

    # ── Statut ──
    col_st, col_btn = st.columns([2, 4])
    with col_st:
        current_statut = v_fresh.get("statut") or "prospect"
        new_statut = st.selectbox(
            "Statut",
            STATUTS,
            index=STATUTS.index(current_statut),
            format_func=_statut_label,
        )
        if new_statut != current_statut:
            db.update_statut(vigneron_id, new_statut)
            _refresh()

    st.divider()

    col_info, col_inter = st.columns([2, 3])

    # ── Colonne gauche : coordonnées ──
    with col_info:
        st.subheader("📋 Informations")
        for label, key in [
            ("Région", "region"), ("Appellation", "appellation"),
            ("Commune", "commune"), ("Adresse", "adresse_complete"),
            ("Couleurs", "couleurs"), ("Nb vins", "nb_vins"),
        ]:
            val = v_fresh.get(key)
            if val:
                st.markdown(f"**{label}** : {val}")

        st.subheader("📞 Coordonnées")
        tel = v_fresh.get("telephone")
        mob = v_fresh.get("telephone_mobile")
        mail = v_fresh.get("email")
        web = v_fresh.get("site_web")
        fb = v_fresh.get("facebook")
        ig = v_fresh.get("instagram")

        if tel:
            clean = tel.replace(" ", "").replace(".", "")
            st.markdown(f"📞 **Tél. fixe** : [{tel}](tel:{clean})")
        if mob:
            clean_m = mob.replace(" ", "").replace(".", "")
            st.markdown(f"📱 **Mobile** : [{mob}](tel:{clean_m})")
        if mail:
            st.markdown(f"📧 **Email** : [{mail}](mailto:{mail})")
        if web:
            st.markdown(f"🌐 **Site web** : [{web}]({web})")
        if fb:
            st.markdown(f"[Facebook]({fb})")
        if ig:
            st.markdown(f"[Instagram]({ig})")
        if not any([tel, mob, mail, web]):
            st.caption("Aucune coordonnée — lancez le scraping des fiches.")

        if v_fresh.get("url_fiche"):
            st.markdown(f"[🔗 Fiche sur le site]({v_fresh['url_fiche']})")

        if v_fresh.get("description"):
            with st.expander("📄 Description"):
                st.write(v_fresh["description"])

    # ── Colonne droite : interactions ──
    with col_inter:
        st.subheader("🗓️ Interactions")

        # Formulaire d'ajout
        with st.form("add_interaction", clear_on_submit=True):
            fi1, fi2 = st.columns([1, 1])
            with fi1:
                inter_type = st.selectbox(
                    "Type", TYPES_INTERACTION,
                    format_func=lambda t: f"{TYPE_ICON[t]} {t.capitalize()}",
                )
            with fi2:
                inter_date = st.date_input("Date", value=date.today())
            inter_notes = st.text_area("Notes", height=80, placeholder="Résumé de l'échange…")
            inter_auteur = st.text_input(
                "Auteur",
                value=st.session_state.get("auteur", ""),
                placeholder="Votre nom",
            )
            submitted = st.form_submit_button("➕ Ajouter l'interaction", type="primary")
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

        # Historique
        interactions = load_interactions(vigneron_id)
        if not interactions:
            st.caption("Aucune interaction enregistrée.")
        else:
            for inter in interactions:
                icon = TYPE_ICON.get(inter.get("type", ""), "📝")
                dt = _fmt_date(inter.get("date"))
                type_label = (inter.get("type") or "autre").capitalize()
                auteur = inter.get("auteur") or ""
                notes = inter.get("notes") or ""

                with st.container(border=True):
                    h1, h2 = st.columns([4, 1])
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


# ──────────────────────────────────────────────
# Routeur principal
# ──────────────────────────────────────────────
if st.session_state.page == "fiche" and st.session_state.selected_vigneron:
    render_fiche()
else:
    render_list()
