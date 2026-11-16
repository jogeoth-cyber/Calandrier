# Guide d’abonnement au calendrier rugby

Le calendrier généré est le fichier `calendrier_ubb_xv_france.ics`. Il regroupe les rencontres de l’UBB et du XV de France trouvées par le script, dans la limite d’un an à venir.

## Importer le fichier ICS

L’import ajoute une copie des événements présents dans le fichier au moment de l’import. Cette copie ne se met pas automatiquement à jour lorsque le script regénère le fichier.

- **Google Agenda** : sur un ordinateur, ouvrez Google Agenda, choisissez **Paramètres** puis **Importer et exporter**, sélectionnez `calendrier_ubb_xv_france.ics` et le calendrier de destination, puis lancez l’import.
- **Outlook** : ouvrez le fichier ICS pour l’ajouter au calendrier, ou utilisez la fonction d’importation de calendrier disponible dans votre version d’Outlook. Les intitulés peuvent varier selon la version.
- **Apple Calendrier** : ouvrez le fichier ICS avec Calendrier, choisissez le calendrier de destination et confirmez l’ajout.

Après une nouvelle génération du fichier, réimportez-le si vous souhaitez actualiser cette copie. Selon l’application, les événements déjà importés peuvent être dupliqués ; il peut être préférable de supprimer l’ancien calendrier importé avant de recommencer.

## S’abonner avec mise à jour automatique

Pour que les modifications soient récupérées, le fichier ICS doit être publié à une adresse HTTPS stable, accessible depuis l’application de calendrier. Le fichier présent sur votre ordinateur ou dans ce dépôt ne constitue pas, à lui seul, une adresse d’abonnement synchronisée. Ce projet ne publie pas actuellement le calendrier à une telle adresse.

Une fois le fichier hébergé et son URL HTTPS disponible :

- **Google Agenda** : dans **Autres agendas**, choisissez **À partir de l’URL**, collez l’adresse HTTPS du fichier ICS, puis ajoutez le calendrier.
- **Outlook** : utilisez l’ajout d’un calendrier à partir d’Internet ou d’une URL, puis collez l’adresse HTTPS.
- **Apple Calendrier** : choisissez **Fichier > Nouvel abonnement au calendrier…**, puis collez l’adresse HTTPS.

Le rafraîchissement dépend ensuite de l’application et de son rythme de synchronisation. Une URL commençant par `webcal://` peut également être acceptée par certaines applications, mais l’adresse doit pointer vers un calendrier maintenu à jour.

## Chaînes TV

Une ligne de diffusion figure dans la description de chaque rencontre. Le script ne renseigne un nom de chaîne que si une source de données lui fournit explicitement ce nom ; sinon, le calendrier indique **« non communiquée à ce jour (à confirmer) »**. Pour les rencontres contrôlées actuellement, la source officielle FFR ne publie pas de nom de diffuseur.
