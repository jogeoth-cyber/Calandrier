import json
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
import requests

# Créer le calendrier final unifié
cal_final = Calendar()
cal_final.add('prodid', '-//Calendrier Rugby UBB & XV de France//FR')
cal_final.add('version', '2.0')

# En-têtes pour simuler un vrai navigateur et éviter d'être bloqué par la FFR
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# ==========================================
# 1. RÉCUPÉRATION UBB (via flux .ics)
# ==========================================
URL_CALENDRIER_UBB = "https://outlook.office365.com/owa/calendar/37c08efc33d44ded957504f36cc15d21@ubbrugby.com/78982c22d7ef4797a377ffa2fde39a331268884149740782852/calendar.ics"  # Remplacez par le vrai lien .ics de l'UBB

try:
    reponse_ubb = requests.get(URL_CALENDRIER_UBB, headers=HEADERS, timeout=15)
    if reponse_ubb.status_code == 200:
        cal_ubb = Calendar.from_ical(reponse_ubb.text)
        for composant in cal_ubb.walk():
            if composant.name == "VEVENT":
                titre = str(composant.get('summary'))
                composant['summary'] = f"[UBB] {titre}"
                cal_final.add_component(composant)
        print("Matchs UBB ajoutés avec succès.")
    else:
        print(f"Erreur HTTP {reponse_ubb.status_code} pour l'UBB")
except Exception as e:
    print(f"Impossible de récupérer l'UBB : {e}")


# ==========================================
# 2. RÉCUPÉRATION XV DE FRANCE (Scraping FFR)
# ==========================================
URL_FFR_MATCHS = "https://www.ffr.fr/equipe-de-france/rugby-a-xv/xv-de-france-masculin/rencontres"

def extraire_matchs_ffr():
    matchs_trouves = []
    try:
        reponse = requests.get(URL_FFR_MATCHS, headers=HEADERS, timeout=15)
        if reponse.status_code != 200:
            print(f"Erreur HTTP {reponse.status_code} sur le site de la FFR")
            return matchs_trouves

        soup = BeautifulSoup(reponse.text, 'html.parser')

        # Méthode A : Rechercher les données structurées JSON-LD (très fiable quand présentes)
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                # Gérer le cas d'une liste ou d'un objet unique
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get('@type') == 'SportsEvent':
                        nom = item.get('name', 'Match XV de France')
                        date_str = item.get('startDate')
                        lieu = item.get('location', {}).get('name', 'Stade à définir')
                        if date_str:
                            dt_debut = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            matchs_trouves.append({
                                "titre": nom,
                                "debut": dt_debut,
                                "fin": dt_debut + timedelta(hours=2),
                                "lieu": lieu
                            })
            except Exception:
                continue

        # Méthode B (Secours) : Lecture directe des cartes de matchs HTML si JSON-LD absent
        if not matchs_trouves:
            # Recherche des blocs contenant les rencontres sur la page FFR
            cartes = soup.find_all(['article', 'div'], class_=re.compile(r'match|rencontre|fixture|event', re.I))
            for carte in cartes:
                texte = carte.get_text(" ", strip=True)
                # Filtrer pour ne garder que les blocs contenant "France" et une date
                if "France" in texte and re.search(r'\d{2}/\d{2}/\d{4}|\d{1,2}\s+[a-zéû]+\s+20\d{2}', texte, re.I):
                    # Extraction basique du titre et de la date si la structure HTML est détectée
                    titre_el = carte.find(['h2', 'h3', 'h4', 'a'])
                    time_el = carte.find('time')
                    if titre_el and time_el and time_el.has_attr('datetime'):
                        try:
                            dt_debut = datetime.fromisoformat(time_el['datetime'].replace('Z', '+00:00'))
                            matchs_trouves.append({
                                "titre": titre_el.get_text(strip=True),
                                "debut": dt_debut,
                                "fin": dt_debut + timedelta(hours=2),
                                "lieu": "FFR / Stade officiel"
                            })
                        except ValueError:
                            continue

    except Exception as e:
        print(f"Erreur lors du scraping FFR : {e}")

    return matchs_trouves

matchs_ffr = extraire_matchs_ffr()

# Dédoublonnage et ajout au calendrier
deja_ajoutes = set()
for match in matchs_ffr:
    cle_unique = f"{match['titre']}_{match['debut'].strftime('%Y%m%d')}"
    if cle_unique not in deja_ajoutes:
        deja_ajoutes.add(cle_unique)
        event = Event()
        event.add('summary', f"[XV de France] {match['titre']}")
        event.add('dtstart', match['debut'])
        event.add('dtend', match['fin'])
        event.add('location', match['lieu'])
        event.add('description', f"Source : {URL_FFR_MATCHS}")
        cal_final.add_component(event)

print(f"{len(deja_ajoutes)} matchs du XV de France ajoutés.")

# ==========================================
# 3. SAUVEGARDE DU FICHIER .ICS FINAL
# ==========================================
with open("calendrier_ubb_xv_france.ics", "wb") as f:
    f.write(cal_final.to_ical())

print("Fichier calendrier_ubb_xv_france.ics généré avec succès !")
