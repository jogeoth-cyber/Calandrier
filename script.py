import requests
from icalendar import Calendar

# 1. URLs des flux iCalendar (exemples de liens d'abonnement officiels LNR / FFR)
# Note : Il faut récupérer l'URL exacte du bouton "Ajouter au calendrier" sur le site de l'UBB et de la FFR
URL_CALENDRIER_UBB = "https://outlook.office365.com/owa/calendar/37c08efc33d44ded957504f36cc15d21@ubbrugby.com/78982c22d7ef4797a377ffa2fde39a331268884149740782852/calendar.ics" 
URL_CALENDRIER_XV_FRANCE = "https://exemple-lien-ical-ffr.ics"

# Créer le calendrier final qui regroupera tout
cal_final = Calendar()
cal_final.add('prodid', '-//Mon Calendrier Rugby UBB & XV de France//FR')
cal_final.add('version', '2.0')

def ajouter_evenements_depuis_url(url, tag_equipe):
    reponse = requests.get(url)
    if reponse.status_code == 200:
        cal_source = Calendar.from_ical(reponse.text)
        for composant in cal_source.walk():
            if composant.name == "VEVENT":
                # Optionnel : ajouter un préfixe au titre pour bien les repérer
                titre_actuel = str(composant.get('summary'))
                composant['summary'] = f"[{tag_equipe}] {titre_actuel}"
                
                # Ajouter le match au calendrier final
                cal_final.add_component(composant)
    else:
        print(f"Erreur lors de la récupération pour {tag_equipe}")

# 2. Récupérer et fusionner les deux équipes
ajouter_evenements_depuis_url(URL_CALENDRIER_UBB, "UBB")
ajouter_evenements_depuis_url(URL_CALENDRIER_XV_FRANCE, "XV de France")

# 3. Sauvegarder le fichier fusionné
with open("calendrier_ubb_xv_france.ics", "wb") as f:
    f.write(cal_final.to_ical())

print("Calendrier UBB + XV de France généré avec succès !")
