"""
Couche d'accès à Supabase pour le CRM Vignerons.
"""

from datetime import datetime, timezone
from supabase_client import get_client

PAGE_SIZE = 1000  # max rows par requête Supabase


# ──────────────────────────────────────────────
# Vignerons
# ──────────────────────────────────────────────

def upsert_vignerons(producers: list[dict]) -> int:
    """
    Insère ou met à jour les vignerons (listing scraper).
    Ne touche pas aux colonnes CRM (statut, derniere_interaction_*).
    Retourne le nombre de lignes traitées.
    """
    client = get_client()
    rows = [_map_producer(p) for p in producers]
    for i in range(0, len(rows), 100):
        chunk = rows[i : i + 100]
        client.table("vignerons").upsert(chunk, on_conflict="slug").execute()
    return len(rows)


def update_details(url_fiche: str, details: dict) -> None:
    """Met à jour les coordonnées d'un vigneron après scraping de sa fiche."""
    client = get_client()
    row = {
        "telephone":          details.get("telephone", "") or "",
        "telephone_mobile":   details.get("telephone_mobile", "") or "",
        "email":              details.get("email", "") or "",
        "site_web":           details.get("site_web", "") or "",
        "facebook":           details.get("reseaux_sociaux", {}).get("facebook", "") or "",
        "instagram":          details.get("reseaux_sociaux", {}).get("instagram", "") or "",
        "description":        details.get("description", "") or "",
        "details_scrapped_at": _now(),
    }
    if details.get("nom_producteur"):
        row["nom_producteur"] = details["nom_producteur"]
    client.table("vignerons").update(row).eq("url_fiche", url_fiche).execute()


def get_all_vignerons() -> list[dict]:
    """Récupère tous les vignerons (pagination automatique)."""
    client = get_client()
    all_data: list[dict] = []
    offset = 0
    while True:
        resp = (
            client.table("vignerons")
            .select("*")
            .order("nom")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        all_data.extend(resp.data)
        if len(resp.data) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return all_data


def update_nom_producteur(url_fiche: str, nom_producteur: str) -> None:
    """Met à jour uniquement le nom du producteur."""
    client = get_client()
    client.table("vignerons").update({"nom_producteur": nom_producteur}).eq("url_fiche", url_fiche).execute()


def update_statut(vigneron_id: str, statut: str) -> None:
    client = get_client()
    client.table("vignerons").update({"statut": statut}).eq("id", vigneron_id).execute()


def update_email(vigneron_id: str, email: str) -> None:
    """Met à jour l'adresse email d'un vigneron."""
    get_client().table("vignerons").update({"email": email}).eq("id", vigneron_id).execute()


def add_prospect(data: dict) -> str:
    """
    Crée un vigneron manuellement (prospect sans scraping).
    Retourne l'id généré par Supabase.
    data doit contenir au minimum : nom
    """
    import re
    import uuid

    nom = data.get("nom", "").strip()
    # Générer un slug unique à partir du nom
    slug_base = re.sub(r"[^a-z0-9]+", "-", nom.lower()).strip("-")
    slug = f"{slug_base}-{uuid.uuid4().hex[:8]}"

    row = {
        "slug":             slug,
        "nom":              nom,
        "nom_producteur":   data.get("nom_producteur", "") or "",
        "region":           data.get("region", "") or "",
        "appellation":      data.get("appellation", "") or "",
        "commune":          data.get("commune", "") or "",
        "code_postal":      data.get("code_postal", "") or "",
        "departement":      data.get("departement", "") or "",
        "adresse_complete": data.get("adresse_complete", "") or "",
        "telephone":        data.get("telephone", "") or "",
        "telephone_mobile": data.get("telephone_mobile", "") or "",
        "email":            data.get("email", "") or "",
        "site_web":         data.get("site_web", "") or "",
        "facebook":         data.get("facebook", "") or "",
        "instagram":        data.get("instagram", "") or "",
        "statut":           data.get("statut", "prospect"),
        "details_scrapped_at": _now(),  # marquer comme rempli manuellement
    }
    client = get_client()
    resp = client.table("vignerons").insert(row).execute()
    return resp.data[0]["id"]


# ──────────────────────────────────────────────
# Interactions
# ──────────────────────────────────────────────

def add_interaction(
    vigneron_id: str,
    type_: str,
    date_str: str,
    notes: str,
    auteur: str,
) -> None:
    """
    Ajoute une interaction et met à jour derniere_interaction_* sur le vigneron.
    date_str : ISO 8601 (ex: "2026-04-02T14:30:00")
    """
    client = get_client()
    client.table("interactions").insert({
        "vigneron_id": vigneron_id,
        "type":        type_,
        "date":        date_str,
        "notes":       notes,
        "auteur":      auteur,
    }).execute()
    client.table("vignerons").update({
        "derniere_interaction_at":   date_str,
        "derniere_interaction_type": type_,
    }).eq("id", vigneron_id).execute()


def get_interactions(vigneron_id: str) -> list[dict]:
    client = get_client()
    resp = (
        client.table("interactions")
        .select("*")
        .eq("vigneron_id", vigneron_id)
        .order("date", desc=True)
        .execute()
    )
    return resp.data


def delete_interaction(interaction_id: str, vigneron_id: str) -> None:
    """Supprime une interaction et recalcule la dernière interaction du vigneron."""
    client = get_client()
    client.table("interactions").delete().eq("id", interaction_id).execute()
    # Recalculer la dernière interaction restante
    remaining = get_interactions(vigneron_id)
    if remaining:
        last = remaining[0]  # déjà trié desc
        client.table("vignerons").update({
            "derniere_interaction_at":   last["date"],
            "derniere_interaction_type": last["type"],
        }).eq("id", vigneron_id).execute()
    else:
        client.table("vignerons").update({
            "derniere_interaction_at":   None,
            "derniere_interaction_type": None,
        }).eq("id", vigneron_id).execute()


# ──────────────────────────────────────────────
# Campagne email
# ──────────────────────────────────────────────

def record_mail_campagne(vigneron_ids: list[str], auteur: str = "Campagne") -> None:
    """Loggue l'envoi de la campagne email comme interaction de type 'email'."""
    now = _now()
    for vid in vigneron_ids:
        add_interaction(
            vigneron_id=vid,
            type_="email",
            date_str=now,
            notes="Email campagne FIDEwine envoyé",
            auteur=auteur,
        )


def get_email_interaction_map() -> dict[str, str]:
    """
    Retourne {vigneron_id: date_du_dernier_email} pour tous les vignerons
    ayant au moins une interaction de type 'email'.
    """
    client = get_client()
    resp = (
        client.table("interactions")
        .select("vigneron_id, date")
        .eq("type", "email")
        .order("date", desc=True)
        .execute()
    )
    result: dict[str, str] = {}
    for row in resp.data:
        vid = row["vigneron_id"]
        if vid not in result:   # premier = plus récent (tri desc)
            result[vid] = row["date"]
    return result


# ──────────────────────────────────────────────
# Helpers internes
# ──────────────────────────────────────────────

def _map_producer(p: dict) -> dict:
    """Transforme un dict scraper en row Supabase (sans colonnes CRM)."""
    return {
        "slug":             p.get("slug", ""),
        "nom":              p.get("nom", ""),
        "region":           p.get("region", ""),
        "appellation":      p.get("appellation", ""),
        "commune":          p.get("commune", ""),
        "code_postal":      p.get("code_postal", ""),
        "departement":      p.get("departement", ""),
        "adresse_complete": p.get("adresse_complete", ""),
        "couleurs":         p.get("couleurs", ""),
        "nb_vins":          p.get("nb_vins") or None,
        "a_email":          bool(p.get("a_email", False)),
        "latitude":         p.get("latitude") or None,
        "longitude":        p.get("longitude") or None,
        "url_fiche":        p.get("url_fiche", ""),
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
