"""
Envoi via l'API Brevo v4 (brevo-python >= 4.0) pour la campagne email FIDEwine.

Configuration dans .streamlit/secrets.toml :
  [brevo]
  api_key    = "xkeysib-..."           # Brevo > SMTP & API > Clés API
  from_email = "contact@fidewine.com"  # expéditeur vérifié dans Brevo
  from_name  = "FIDEwine"              # nom par défaut (écrasé au moment de l'envoi)

Ou via variables d'environnement : BREVO_API_KEY, BREVO_FROM_EMAIL, BREVO_FROM_NAME.
"""

import os


def _get_config() -> dict | None:
    """Lit la configuration Brevo depuis st.secrets ou l'environnement."""
    try:
        import streamlit as st
        b = st.secrets.get("brevo", {})
        api_key    = b.get("api_key")    or os.environ.get("BREVO_API_KEY", "")
        from_email = b.get("from_email") or os.environ.get("BREVO_FROM_EMAIL", "")
        from_name  = b.get("from_name")  or os.environ.get("BREVO_FROM_NAME", "FIDEwine")
        if api_key and from_email:
            return {"api_key": api_key, "from_email": from_email, "from_name": from_name}
    except Exception:
        pass
    return None


def is_smtp_configured() -> bool:
    return _get_config() is not None


def get_smtp_user() -> str:
    cfg = _get_config()
    return cfg["from_email"] if cfg else ""


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    from_name: str = "FIDEwine",
) -> tuple[bool, str]:
    """
    Envoie un email HTML via l'API transactionnelle Brevo (v4).
    from_name : nom affiché de l'expéditeur (ex : "Sébastien Roud").
    Retourne (succès, message_erreur).
    """
    cfg = _get_config()
    if not cfg:
        return False, "Brevo non configuré (clé API manquante dans secrets.toml)"

    try:
        import brevo

        client = brevo.Brevo(api_key=cfg["api_key"])
        client.transactional_emails.send_transac_email(
            sender=brevo.SendTransacEmailRequestSender(
                name=from_name,
                email=cfg["from_email"],
            ),
            to=[brevo.SendTransacEmailRequestToItem(email=to_email)],
            reply_to=brevo.SendTransacEmailRequestReplyTo(email=cfg["from_email"]),
            subject=subject,
            html_content=html_body,
        )
        return True, ""

    except ImportError:
        return False, "Package 'brevo-python' manquant — lancez : pip install brevo-python"
    except Exception as exc:
        # Extraire le message d'erreur Brevo si disponible dans le corps de la réponse
        msg = str(exc)
        import re
        m = re.search(r'"message"\s*:\s*"([^"]+)"', msg)
        return False, (m.group(1) if m else msg[:150])
