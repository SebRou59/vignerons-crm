"""
Template HTML du mail de campagne FIDEwine.
Variables : {{PRENOM}}, {{PRENOM_NOM}}, {{REGION}}, {{TELEPHONE}}, {{INITIAL}}, {{EMAIL_EXPEDITEUR}}
"""

SUBJECT = "🍷 J'utilise le QR code nutri pour vendre mieux. Je vous montre comment."

TEMPLATE = """\
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>FIDEwine</title>
</head>
<body style="margin:0;padding:0;background-color:#f0ede8;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.65;color:#333333;">

<!-- Preheader invisible -->
<div style="display:none;max-height:0;max-width:0;overflow:hidden;opacity:0;font-size:1px;line-height:1px;color:#f0ede8;mso-hide:all;">
  J'utilise le QR code nutri pour vendre mieux. Je vous montre comment, en 20 min.&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;
</div>

<!-- Wrapper externe -->
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color:#f0ede8;">
  <tr>
    <td align="center" style="padding:24px 12px;">

      <!-- Carte principale 600px -->
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width:600px;margin:0 auto;border-radius:12px;overflow:hidden;box-shadow:0 2px 16px rgba(0,0,0,0.10);">

        <!-- HEADER fond sombre -->
        <tr>
          <td style="background-color:#1a1a2e;padding:22px 32px;border-radius:12px 12px 0 0;">
            <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
              <tr>
                <td style="vertical-align:middle;">
                  <span style="font-family:Georgia,'Times New Roman',serif;font-size:24px;font-weight:bold;color:#ffffff;letter-spacing:2px;">FIDE<span style="color:#c9a84c;">wine</span></span>
                </td>
                <td align="right" style="vertical-align:middle;">
                  <span style="font-family:Georgia,'Times New Roman',serif;font-size:11px;color:#c9a84c;font-style:italic;line-height:1.7;">par un producteur,<br>pour les producteurs</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- CORPS blanc -->
        <tr>
          <td style="background-color:#ffffff;padding:32px 32px 28px 32px;">

            <!-- Salutation -->
            <p style="margin:0 0 20px 0;font-size:15px;color:#333333;line-height:1.65;">
              Bonjour {{PRENOM}},
            </p>

            <!-- H1 Accroche -->
            <h1 style="margin:0 0 22px 0;font-family:Georgia,'Times New Roman',serif;font-size:20px;font-weight:bold;color:#1a1a2e;line-height:1.45;mso-line-height-rule:exactly;">
              Comme vous, j'ai d&#251; coller un QR code nutritionnel sur mes bouteilles.
              Contrairement &#224; la plupart des producteurs, j'ai d&#233;cid&#233; d'en faire quelque chose.
            </h1>

            <!-- Para 1 : terroir / IA -->
            <p style="margin:0 0 16px 0;font-size:15px;color:#444444;line-height:1.7;">
              Mes vins racontent un terroir, une m&#233;thode, une histoire. J'ai connect&#233; mon QR code r&#233;glementaire &#224; un agent IA entra&#238;n&#233; sur mes propres contenus : c&#233;pages, pratiques culturales, profils aromatiques, r&#233;ponses habituelles aux questions des cavistes et restaurateurs.
            </p>

            <!-- Para 2 : gain de temps -->
            <p style="margin:0 0 28px 0;font-size:15px;color:#444444;line-height:1.7;">
              Mes acheteurs repartent avec une vraie connaissance de mes vins. Je passe moins de temps &#224; r&#233;pondre aux m&#234;mes questions et chaque bouteille porte maintenant une conversation compl&#232;te sur le domaine, accessible en un scan. Pas un gadget. Un outil qui travaille &#224; ma place.
            </p>

            <!-- Encadr&#233; "Ce que ca change conc&#232;tement" -->
            <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom:28px;">
              <tr>
                <td style="background-color:#f8f5f0;border-left:4px solid #c9a84c;padding:20px 22px;border-radius:0 8px 8px 0;">
                  <p style="margin:0 0 12px 0;font-weight:bold;color:#1a1a2e;font-size:14px;text-transform:uppercase;letter-spacing:0.5px;">
                    Ce que &#231;a change concr&#232;tement
                  </p>
                  <p style="margin:0 0 10px 0;color:#444444;font-size:14px;line-height:1.7;">
                    Un caviste ou un restaurateur scanne le QR code devant un client.
                  </p>
                  <p style="margin:0 0 10px 0;color:#444444;font-size:14px;line-height:1.7;">
                    La question arrive : <em>"Ce vin est-il adapt&#233; &#224; un accord avec du gibier en sauce ?"</em>
                  </p>
                  <p style="margin:0 0 10px 0;color:#777777;font-size:14px;line-height:1.7;">
                    Sans FIDEwine : la question reste sans r&#233;ponse ou donne lieu &#224; une approximation.
                  </p>
                  <p style="margin:0;color:#1a1a2e;font-size:14px;line-height:1.7;font-weight:bold;">
                    Avec FIDEwine : l'agent IA r&#233;pond instantan&#233;ment, avec mes mots, mes arguments, ma connaissance du vin.
                  </p>
                </td>
              </tr>
            </table>

            <!-- Deux colonnes visuelles -->
            <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom:28px;">
              <tr>
                <!-- Page consommateur (bleu) -->
                <td width="48%" valign="top" style="padding-right:6px;">
                  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                    <tr>
                      <td style="background-color:#1a3358;padding:20px 16px;border-radius:8px;text-align:center;">
                        <p style="margin:0 0 10px 0;color:#ffffff;font-weight:bold;font-size:12px;text-transform:uppercase;letter-spacing:1px;">
                          Page consommateur
                        </p>
                        <p style="margin:0;color:#a8c8e8;font-size:12px;line-height:1.8;">
                          C&#233;pages, terroir,<br>
                          accords mets-vins,<br>
                          histoire du domaine<br>
                          accessibles en un scan
                        </p>
                      </td>
                    </tr>
                  </table>
                </td>
                <!-- Espace -->
                <td width="4%"></td>
                <!-- Agent IA (vert) -->
                <td width="48%" valign="top" style="padding-left:6px;">
                  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                    <tr>
                      <td style="background-color:#1a3d2e;padding:20px 16px;border-radius:8px;text-align:center;">
                        <p style="margin:0 0 10px 0;color:#ffffff;font-weight:bold;font-size:12px;text-transform:uppercase;letter-spacing:1px;">
                          Agent IA int&#233;gr&#233;
                        </p>
                        <p style="margin:0;color:#a8d8b8;font-size:12px;line-height:1.8;">
                          R&#233;pond aux questions<br>
                          avec vos mots,<br>
                          vos arguments,<br>
                          24h/24
                        </p>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>

            <!-- CTA fond sombre -->
            <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom:28px;">
              <tr>
                <td style="background-color:#1a1a2e;padding:24px 28px;border-radius:8px;text-align:center;">
                  <p style="margin:0 0 12px 0;font-family:Georgia,'Times New Roman',serif;font-size:18px;font-weight:bold;color:#c9a84c;">
                    Je vous montre en 20 min
                  </p>
                  <p style="margin:0;color:#cccccc;font-size:13px;line-height:1.7;">
                    Appelez-moi ou r&#233;pondez directement &#224; ce mail.<br>
                    Je vous fais une d&#233;monstration sur votre propre domaine, gratuitement.
                  </p>
                </td>
              </tr>
            </table>

            <!-- Signature -->
            <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
              <tr>
                <td width="52" valign="top" style="padding-right:14px;">
                  <div style="width:44px;height:44px;background-color:#1a1a2e;border-radius:50%;text-align:center;line-height:44px;color:#c9a84c;font-weight:bold;font-size:20px;font-family:Georgia,'Times New Roman',serif;">
                    {{INITIAL}}
                  </div>
                </td>
                <td valign="top">
                  <p style="margin:0 0 3px 0;font-weight:bold;color:#1a1a2e;font-size:14px;">{{PRENOM_NOM}}</p>
                  <p style="margin:0 0 3px 0;color:#666666;font-size:13px;">Fondateur FIDEwine, Producteur {{REGION}}</p>
                  <p style="margin:0 0 3px 0;color:#666666;font-size:13px;">{{TELEPHONE}}</p>
                  <p style="margin:0;"><a href="https://fidewine.com" style="color:#c9a84c;text-decoration:none;font-size:13px;font-weight:bold;">fidewine.com</a></p>
                </td>
              </tr>
            </table>

          </td>
        </tr>

        <!-- FOOTER -->
        <tr>
          <td style="background-color:#eae7e2;padding:16px 32px;border-radius:0 0 12px 12px;text-align:center;">
            <p style="margin:0;color:#999999;font-size:11px;line-height:1.8;">
              Vous recevez ce message car vous exercez en tant que producteur vigneron ind&#233;pendant.<br>
              Pour ne plus recevoir nos messages, r&#233;pondez &#224; cet email avec l'objet <em>D&#233;sinscription</em>
              ou &#233;crivez-nous &#224; <a href="mailto:{{EMAIL_EXPEDITEUR}}" style="color:#aaaaaa;text-decoration:none;">{{EMAIL_EXPEDITEUR}}</a>.
            </p>
          </td>
        </tr>

      </table>
    </td>
  </tr>
</table>

</body>
</html>
"""


def render_email(
    prenom: str,
    prenom_nom: str,
    region: str,
    telephone: str,
    email_expediteur: str,
) -> tuple[str, str]:
    """
    Retourne (sujet, html) avec les variables remplacées.
    prenom          : prénom du destinataire
    prenom_nom      : prénom + nom de l'expéditeur (pour la signature)
    region          : région viticole de l'expéditeur
    telephone       : téléphone de l'expéditeur
    email_expediteur: adresse email de l'expéditeur (lien désinscription)
    """
    initial = prenom_nom[0].upper() if prenom_nom and prenom_nom.strip() else "F"
    html = TEMPLATE
    html = html.replace("{{PRENOM}}", prenom or "Producteur")
    html = html.replace("{{PRENOM_NOM}}", prenom_nom or "")
    html = html.replace("{{REGION}}", region or "")
    html = html.replace("{{TELEPHONE}}", telephone or "")
    html = html.replace("{{INITIAL}}", initial)
    html = html.replace("{{EMAIL_EXPEDITEUR}}", email_expediteur or "")
    return SUBJECT, html
