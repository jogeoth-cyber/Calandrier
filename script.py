import json
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
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
                        debut = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        lieu = data.get('location', 'Stade à définir')
                        if isinstance(lieu, dict):
                            lieu = lieu.get('name', 'Stade à définir')
                        evenements.append({
                            'titre': data.get('name', 'Match'),
                            'debut': debut,
                            'fin': debut + timedelta(hours=2),
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
            cartes = soup.find_all(['article', 'div', 'li'], class_=re.compile(r'match|rencontre|fixture|event', re.I))
            for carte in cartes:
                titre_el = carte.find(['h2', 'h3', 'h4'])
                time_el = carte.find('time')
                if not titre_el or not time_el or not time_el.get('datetime'):
                    continue
                try:
                    debut = datetime.fromisoformat(time_el['datetime'].replace('Z', '+00:00'))
                    matchs.append({
                        'titre': titre_el.get_text(' ', strip=True),
                        'debut': debut,
                        'fin': debut + timedelta(hours=2),
                        'lieu': 'Stade à définir'
                    })
                except ValueError:
                    continue
    except Exception as e:
        print(f"Erreur lors de la récupération de {nom_equipe} : {e}")

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
        event.add('description', f"Source : {source}")
        cal_final.add_component(event)
    return len(deja_ajoutes)


# ==========================================
# 1. RÉCUPÉRATION UBB (scraping du calendrier officiel)
# ==========================================
URL_UBB_MATCHS = "https://www.ubbrugby.com/equipes/equipe-premiere/calendrier-resultats.html"
matchs_ubb = extraire_matchs_page(URL_UBB_MATCHS, 'UBB')
nb_matchs_ubb = ajouter_matchs_au_calendrier(matchs_ubb, 'UBB', URL_UBB_MATCHS)
print(f"{nb_matchs_ubb} matchs de l'UBB ajoutés.")


# ==========================================
# 2. RÉCUPÉRATION XV DE FRANCE (Scraping FFR)
# ==========================================
URL_FFR_MATCHS = "https://www.ffr.fr/equipe-de-france/rugby-a-xv/xv-de-france-masculin/rencontres"
matchs_ffr = extraire_matchs_page(URL_FFR_MATCHS, 'la FFR')
nb_matchs_ffr = ajouter_matchs_au_calendrier(matchs_ffr, 'XV de France', URL_FFR_MATCHS)
print(f"{nb_matchs_ffr} matchs du XV de France ajoutés.")

# ==========================================
# 3. SAUVEGARDE DU FICHIER .ICS FINAL
# ==========================================
with open("calendrier_ubb_xv_france.ics", "wb") as f:
    f.write(cal_final.to_ical())

print("Fichier calendrier_ubb_xv_france.ics généré avec succès !")
