"""
Envoi SMTP pour la campagne email FIDEwine.

Configuration dans .streamlit/secrets.toml :
  [smtp]
  host     = "smtp.gmail.com"
  port     = 587
  user     = "votre@email.com"
  password = "mot_de_passe_application"

Ou via variables d'environnement : SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _get_smtp_config() -> dict | None:
    """Lit la configuration SMTP depuis st.secrets ou l'environnement."""
    try:
        import streamlit as st
        smtp = st.secrets.get("smtp", {})
        host = smtp.get("host") or os.environ.get("SMTP_HOST", "")
        port = int(smtp.get("port") or os.environ.get("SMTP_PORT", 587))
        user = smtp.get("user") or os.environ.get("SMTP_USER", "")
        pwd  = smtp.get("password") or os.environ.get("SMTP_PASSWORD", "")
        if host and user and pwd:
            return {"host": host, "port": port, "user": user, "password": pwd}
    except Exception:
        pass
    return None


def is_smtp_configured() -> bool:
    return _get_smtp_config() is not None


def get_smtp_user() -> str:
    cfg = _get_smtp_config()
    return cfg["user"] if cfg else ""


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    from_name: str = "FIDEwine",
) -> tuple[bool, str]:
    """
    Envoie un email HTML via SMTP.
    Retourne (succes, message_erreur).
    """
    cfg = _get_smtp_config()
    if not cfg:
        return False, "SMTP non configuré"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{from_name} <{cfg['user']}>"
    msg["To"]      = to_email
    msg["Reply-To"] = cfg["user"]
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if cfg["port"] == 465:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=15) as srv:
                srv.login(cfg["user"], cfg["password"])
                srv.send_message(msg)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as srv:
                srv.ehlo()
                srv.starttls()
                srv.ehlo()
                srv.login(cfg["user"], cfg["password"])
                srv.send_message(msg)
        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, "Erreur d'authentification SMTP"
    except smtplib.SMTPRecipientsRefused:
        return False, f"Adresse refusée : {to_email}"
    except Exception as exc:
        return False, str(exc)[:100]
