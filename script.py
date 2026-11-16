import json
import re
from datetime import date, datetime, timedelta
from io import BytesIO
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from pypdf import PdfReader
from pypdf.errors import PdfReadError
import requests
import urllib3

# Désactiver l'avertissement SSL pour les sites aux certificats non standard
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Créer le calendrier final unifié
cal_final = Calendar()
cal_final.add('prodid', '-//Calendrier Rugby UBB & XV de France//FR')
cal_final.add('version', '2.0')

# En-têtes pour simuler un vrai navigateur et éviter d'être bloqué par les sites
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


def parser_date_match(date_str):
    """Renvoie une date sans heure quand l'horaire est absent ou inconnu."""
    debut = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    if 'T' not in date_str or debut.time().replace(tzinfo=None) == datetime.min.time():
        return debut.date()
    return debut


def fin_match(debut):
    """Calcule la fin d'un match, ou la borne exclusive d'un événement journée entière."""
    if isinstance(debut, datetime):
        return debut + timedelta(hours=2)
    return debut + timedelta(days=1)


def filtrer_periode_future(matchs, debut_periode, fin_periode):
    """Conserve les matchs prévus entre aujourd'hui et un an plus tard."""
    resultat = []
    for match in matchs:
        debut = match['debut']
        date_match = debut.date() if isinstance(debut, datetime) else debut
        if debut_periode <= date_match <= fin_periode:
            resultat.append(match)
    return resultat


def extraire_evenements_jsonld(soup):
    """Extrait les rencontres des données structurées SportsEvent, si présentes."""
    evenements = []

    def parcourir(data):
        if isinstance(data, list):
            for element in data:
                parcourir(element)
        elif isinstance(data, dict):
            types = data.get('@type', [])
            if isinstance(types, str):
                types = [types]

            if 'SportsEvent' in types:
                date_str = data.get('startDate')
                if date_str:
                    try:
                        debut = parser_date_match(date_str)
                        lieu = data.get('location', 'Stade à définir')
                        if isinstance(lieu, dict):
                            lieu = lieu.get('name', 'Stade à définir')
                        evenements.append({
                            'titre': data.get('name', 'Match'),
                            'debut': debut,
                            'fin': fin_match(debut),
                            'lieu': lieu
                        })
                    except (TypeError, ValueError):
                        pass

            # Les sites peuvent encapsuler leurs événements dans @graph ou d'autres objets.
            for valeur in data.values():
                if isinstance(valeur, (dict, list)):
                    parcourir(valeur)

    for script in soup.find_all('script', type='application/ld+json'):
        try:
            parcourir(json.loads(script.string or script.get_text()))
        except (json.JSONDecodeError, TypeError):
            continue

    return evenements


def extraire_matchs_page(url, nom_equipe):
    """Récupère les matchs d'une page calendrier (JSON-LD puis cartes HTML)."""
    matchs = []
    try:
        # Les sites ciblés utilisent parfois un certificat non standard ou auto-signé.
        reponse = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        if reponse.status_code != 200:
            print(f"Erreur HTTP {reponse.status_code} sur le site de {nom_equipe}")
            return matchs

        soup = BeautifulSoup(reponse.text, 'html.parser')
        matchs = extraire_evenements_jsonld(soup)

        # Secours : lecture des cartes HTML si les données JSON-LD sont absentes.
        if not matchs:
            cartes = soup.select('.upcoming-match')
            if not cartes:
                cartes = soup.find_all(
                    ['article', 'div', 'li'],
                    class_=re.compile(r'match|rencontre|fixture|event', re.I)
                )

            for carte in cartes:
                time_el = carte.find('time')
                if not time_el or not time_el.get('datetime'):
                    continue

                titre_el = carte.find(['h2', 'h3', 'h4'])
                titre = titre_el.get_text(' ', strip=True) if titre_el else ''
                if not titre:
                    equipes = [
                        image.get('alt', '').strip()
                        for image in carte.select('.upcoming-match-logo img[alt]')
                        if image.get('alt', '').strip()
                    ]
                    titre = ' - '.join(equipes)
                if not titre:
                    continue

                try:
                    debut = parser_date_match(time_el['datetime'])
                except ValueError:
                    continue

                stade_el = carte.select_one('.upcoming-match-stadium')
                matchs.append({
                    'titre': titre,
                    'debut': debut,
                    'fin': fin_match(debut),
                    'lieu': stade_el.get_text(' ', strip=True) if stade_el else 'Stade à définir'
                })

        if not matchs and 'You need to enable JavaScript to run this app' in reponse.text:
            print(
                f"Les matchs de {nom_equipe} ne sont pas présents dans le HTML reçu "
                "(la page charge ses données avec JavaScript)."
            )
    except Exception as e:
        print(f"Erreur lors de la récupération de {nom_equipe} : {e}")

    return matchs


def extraire_matchs_ubb_pdf(url_page):
    """Extrait toutes les dates du calendrier complet de saison de l'UBB."""
    try:
        reponse_page = requests.get(url_page, headers=HEADERS, timeout=15, verify=False)
        if reponse_page.status_code != 200:
            print(f"Erreur HTTP {reponse_page.status_code} sur le calendrier de l'UBB")
            return []

        soup = BeautifulSoup(reponse_page.text, 'html.parser')
        lien_pdf = next(
            (
                lien['href']
                for lien in soup.find_all('a', href=True)
                if re.search(r'\.pdf(?:$|[?#])', lien['href'], re.I)
            ),
            None
        )
        if not lien_pdf:
            print("Le calendrier complet PDF de l'UBB est introuvable.")
            return []

        url_pdf = urljoin(url_page, lien_pdf)
        reponse_pdf = requests.get(url_pdf, headers=HEADERS, timeout=30, verify=False)
        if reponse_pdf.status_code != 200:
            print(f"Erreur HTTP {reponse_pdf.status_code} sur le calendrier PDF de l'UBB")
            return []
        if not reponse_pdf.content.startswith(b'%PDF'):
            print("Le calendrier téléchargé depuis l'UBB n'est pas un fichier PDF valide.")
            return []

        lecteur = PdfReader(BytesIO(reponse_pdf.content))
        texte = '\n'.join(
            page.extract_text(extraction_mode='layout') or ''
            for page in lecteur.pages
        )
    except requests.RequestException as e:
        print(f"Erreur lors de la récupération du calendrier complet de l'UBB : {e}")
        return []
    except (PdfReadError, OSError, ValueError) as e:
        print(f"Impossible de lire le calendrier PDF de l'UBB : {e}")
        return []

    saison = re.search(r'SAISON\s+(\d{4})-(\d{4})', texte, re.I)
    if not saison:
        print("Impossible de déterminer la saison du calendrier PDF de l'UBB.")
        return []
    annee_debut, annee_fin = (int(annee) for annee in saison.groups())

    mois_patterns = [
        (re.compile(pattern, re.I), mois)
        for pattern, mois in (
            (r'JANVIER', 1), (r'F.?VRIER', 2), (r'MARS', 3), (r'AVRIL', 4),
            (r'MAI', 5), (r'JUIN', 6), (r'JUILLET', 7), (r'AO.?T', 8),
            (r'SEPTEMBRE', 9), (r'OCTOBRE', 10), (r'NOVEMBRE', 11),
            (r'D.?CEMBRE', 12)
        )
    ]
    plage_re = re.compile(r'(?<!\d)(\d{1,2}(?:-\d{1,2}){1,2})')
    jour_re = re.compile(r'(?<![\d/-])(\d{1,2})(?![\d/-])')
    lignes = texte.splitlines()
    mois_courants = []
    matchs = []
    aujourd_hui = datetime.now().date()

    for index, ligne in enumerate(lignes):
        if ligne.strip() and ligne.strip() == ligne.strip().upper():
            entetes = [
                (trouvaille.start(), mois, trouvaille.group())
                for pattern, mois in mois_patterns
                for trouvaille in pattern.finditer(ligne)
            ]
            reste = ligne
            for position, _, libelle in sorted(entetes, reverse=True):
                reste = reste[:position] + (' ' * len(libelle)) + reste[position + len(libelle):]
            if entetes and not reste.strip():
                mois_courants = sorted((position, mois) for position, mois, _ in entetes)

        plages = list(plage_re.finditer(ligne))
        jours = [(plage.start(), plage.group()) for plage in plages]
        reste = plage_re.sub('', ligne)
        if re.fullmatch(r'[\s\d]*', reste):
            jours.extend((jour.start(), jour.group()) for jour in jour_re.finditer(ligne))
        if index > 0:
            jours.extend(
                (jour.start(), jour.group())
                for jour in jour_re.finditer(ligne)
                if any(
                    abs(jour.start() - finale.start()) <= 3
                    for finale in re.finditer(r'FINALE', lignes[index - 1], re.I)
                )
            )
        jours.extend(
            (finale.start(1), finale.group(1))
            for finale in re.finditer(r'FINALE\s{0,2}(\d{1,2})', ligne, re.I)
        )

        for position, jours_str in sorted(set(jours)):
            if not mois_courants:
                continue
            mois_precedents = [entete for entete in mois_courants if entete[0] <= position]
            mois = mois_precedents[-1][1] if mois_precedents else mois_courants[0][1]
            jours_numeros = [int(jour) for jour in jours_str.split('-')]
            annee = annee_debut if mois >= 9 else annee_fin
            try:
                debut = date(annee, mois, jours_numeros[0])
                dernier_jour = debut
                for jour in jours_numeros[1:]:
                    mois_suivant = dernier_jour.month
                    annee_suivante = dernier_jour.year
                    if jour < dernier_jour.day:
                        mois_suivant += 1
                        if mois_suivant > 12:
                            mois_suivant = 1
                            annee_suivante += 1
                    dernier_jour = date(annee_suivante, mois_suivant, jour)
            except ValueError:
                print(f"Date invalide dans le calendrier PDF de l'UBB : {jours_str}")
                continue

            if dernier_jour < aujourd_hui:
                continue

            journees = []
            for ligne_proche in lignes[max(0, index - 1):min(len(lignes), index + 4)]:
                journees.extend(
                    (trouvaille.start(), trouvaille.group(1))
                    for trouvaille in re.finditer(r'J\s*(\d{1,2})\b', ligne_proche, re.I)
                    if position <= trouvaille.start() <= position + 20
                )

            if journees:
                titre = f"Match UBB - J{min(journees)[1]}"
            else:
                phases = []
                phase_patterns = (
                    (r'1/8(?:\s+DE\s+FINALES)?', "1/8 de finale (si qualifié)"),
                    (r'1/4(?:\s+DE\s+FINALES)?', "1/4 de finale (si qualifié)"),
                    (r'1/2(?:\s+FINALES)?', "Demi-finale (si qualifié)"),
                    (r'BARRAGES', "Barrages"),
                    (r'FINALE', "Finale (si qualifié)")
                )
                for ligne_proche in lignes[max(0, index - 1):min(len(lignes), index + 2)]:
                    for pattern, libelle in phase_patterns:
                        phases.extend(
                            (abs(trouvaille.start() - position), libelle)
                            for trouvaille in re.finditer(pattern, ligne_proche, re.I)
                            if abs(trouvaille.start() - position) <= 18
                        )
                titre = min(phases)[1] if phases else "Match UBB (date à confirmer)"

            lieux = []
            lieu_patterns = (
                (r'CHABAN\s+DELMAS', "Stade Chaban-Delmas"),
                (r'STADE\s+ATLANTIQUE', "Stade Atlantique"),
                (r'EXT.{0,2}RIEUR', "À l'extérieur (stade à confirmer)")
            )
            for ligne_proche in lignes[max(0, index - 1):min(len(lignes), index + 4)]:
                for pattern, lieu in lieu_patterns:
                    lieux.extend(
                        (abs(trouvaille.start() - position), lieu)
                        for trouvaille in re.finditer(pattern, ligne_proche, re.I)
                        if abs(trouvaille.start() - position) <= 18
                    )

            matchs.append({
                'titre': titre,
                'debut': debut,
                'fin': dernier_jour + timedelta(days=1),
                'lieu': min(lieux)[1] if lieux else 'Lieu à confirmer',
                'description': (
                    f"Source : {url_pdf}\n"
                    "Le jour et l'horaire précis seront communiqués au plus tard "
                    "deux semaines avant le match."
                )
            })

    if not matchs:
        print("Aucune date de match à venir n'a pu être extraite du calendrier PDF de l'UBB.")
    return matchs


def fusionner_matchs_ubb(matchs_pdf, matchs_precis):
    """Remplace les fenêtres de dates PDF par les horaires exacts disponibles."""
    matchs = list(matchs_pdf)
    for match_precis in matchs_precis:
        date_precise = (
            match_precis['debut'].date()
            if isinstance(match_precis['debut'], datetime)
            else match_precis['debut']
        )
        index_fenetre = next(
            (
                index for index, match_pdf in enumerate(matchs)
                if (
                    match_pdf['debut'].date()
                    if isinstance(match_pdf['debut'], datetime)
                    else match_pdf['debut']
                ) <= date_precise < (
                    match_pdf['fin'].date()
                    if isinstance(match_pdf['fin'], datetime)
                    else match_pdf['fin']
                )
            ),
            None
        )
        if index_fenetre is None:
            matchs.append(match_precis)
        else:
            matchs[index_fenetre] = match_precis
    return matchs


def extraire_matchs_ffr():
    """Récupère les prochains matchs du XV de France via l'API officielle FFR."""
    url_api = "https://api.www.ffr.fr/wp-json/ffr/v1/rencontres_itl"
    aujourd_hui = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    params = {
        'start_date': aujourd_hui.isoformat(timespec='seconds'),
        'equipe': 'xv-de-france-masculin',
        'per_page': 300
    }

    try:
        reponse = requests.get(url_api, params=params, headers=HEADERS, timeout=15, verify=False)
        if reponse.status_code != 200:
            raise requests.HTTPError(
                f"Erreur HTTP {reponse.status_code} sur l'API de la FFR",
                response=reponse
            )
        evenements = reponse.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Erreur lors de la récupération des matchs de la FFR : {e}") from e
    except ValueError as e:
        raise RuntimeError(f"Réponse JSON invalide de l'API FFR : {e}") from e

    if not isinstance(evenements, list):
        raise RuntimeError("Réponse inattendue de l'API FFR : une liste de matchs était attendue.")

    matchs = []
    for evenement in evenements:
        if not isinstance(evenement, dict):
            print("Un élément inattendu a été ignoré dans la réponse API FFR.")
            continue

        meta = evenement.get('meta', {})
        date_str = meta.get('date_rencontre') if isinstance(meta, dict) else None
        titre_data = evenement.get('title', {})
        titre = titre_data.get('rendered') if isinstance(titre_data, dict) else None
        if not isinstance(date_str, str) or not isinstance(titre, str):
            print("Un match FFR a été ignoré : date ou titre manquant dans la réponse API.")
            continue

        try:
            debut = parser_date_match(date_str)
        except ValueError:
            print(f"Date de match FFR invalide : {date_str}")
            continue

        if isinstance(debut, datetime):
            maintenant = datetime.now(debut.tzinfo) if debut.tzinfo else datetime.now()
            if debut < maintenant:
                continue
        elif debut < datetime.now().date():
            continue

        matchs.append({
            'titre': titre,
            'debut': debut,
            'fin': fin_match(debut),
            'lieu': meta.get('lieu') or 'Stade à définir'
        })

    return matchs


def ajouter_matchs_au_calendrier(matchs, prefixe, source):
    """Ajoute les matchs au calendrier en évitant les doublons."""
    deja_ajoutes = set()
    for match in matchs:
        cle_unique = f"{match['titre']}_{match['debut'].strftime('%Y%m%d')}"
        if cle_unique in deja_ajoutes:
            continue
        deja_ajoutes.add(cle_unique)
        event = Event()
        event.add('summary', f"[{prefixe}] {match['titre']}")
        event.add('dtstart', match['debut'])
        event.add('dtend', match['fin'])
        event.add('location', match['lieu'])
        description = match.get('description', f"Source : {source}")
        diffusion_tv = match.get('diffusion_tv')
        ligne_diffusion = (
            f"Diffusion TV : {diffusion_tv}"
            if diffusion_tv
            else "Diffusion TV : non communiquée à ce jour (à confirmer)."
        )
        event.add('description', f"{description}\n{ligne_diffusion}")
        cal_final.add_component(event)
    return len(deja_ajoutes)


# ==========================================
# 1. RÉCUPÉRATION UBB (scraping du calendrier officiel)
# ==========================================
URL_UBB_MATCHS = "https://www.ubbrugby.com/equipes/equipe-premiere/calendrier-resultats.html"
matchs_ubb_precis = extraire_matchs_page(URL_UBB_MATCHS, 'UBB')
matchs_ubb_pdf = extraire_matchs_ubb_pdf(URL_UBB_MATCHS)
matchs_ubb = fusionner_matchs_ubb(matchs_ubb_pdf, matchs_ubb_precis)
debut_periode = datetime.now().date()
fin_periode = debut_periode + timedelta(days=365)
matchs_ubb = filtrer_periode_future(matchs_ubb, debut_periode, fin_periode)
nb_matchs_ubb = ajouter_matchs_au_calendrier(matchs_ubb, 'UBB', URL_UBB_MATCHS)
print(f"{nb_matchs_ubb} matchs de l'UBB ajoutés.")


# ==========================================
# 2. RÉCUPÉRATION XV DE FRANCE (API FFR)
# ==========================================
URL_FFR_MATCHS = "https://www.ffr.fr/equipe-de-france/rugby-a-xv/xv-de-france-masculin/agenda"
matchs_ffr = extraire_matchs_ffr()
matchs_ffr = filtrer_periode_future(matchs_ffr, debut_periode, fin_periode)
nb_matchs_ffr = ajouter_matchs_au_calendrier(matchs_ffr, 'XV de France', URL_FFR_MATCHS)
print(f"{nb_matchs_ffr} matchs du XV de France ajoutés.")

# ==========================================
# 3. SAUVEGARDE DU FICHIER .ICS FINAL
# ==========================================
with open("calendrier_ubb_xv_france.ics", "wb") as f:
    f.write(cal_final.to_ical())

print("Fichier calendrier_ubb_xv_france.ics généré avec succès !")