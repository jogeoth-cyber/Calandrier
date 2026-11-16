# Guide d’abonnement au calendrier rugby

Le calendrier généré est le fichier `calendrier_ubb_xv_france.ics`. Il regroupe les rencontres de l’UBB et du XV de France trouvées par le script, dans la limite d’un an à venir.

## Importer le fichier ICS

L’import ajoute une copie des événements présents dans le fichier au moment de l’import. Cette copie ne se met pas automatiquement à jour lorsque le script regénère le fichier.

- **Google Agenda** : sur un ordinateur, ouvrez Google Agenda, choisissez **Paramètres** puis **Importer et exporter**, sélectionnez `calendrier_ubb_xv_france.ics` et le calendrier de destination, puis lancez l’import.
- **Outlook** : ouvrez le fichier ICS pour l’ajouter au calendrier, ou utilisez la fonction d’importation de calendrier disponible dans votre version d’Outlook. Les intitulés peuvent varier selon la version.
- **Apple Calendrier** : ouvrez le fichier ICS avec Calendrier, choisissez le calendrier de destination et confirmez l’ajout.

Après une nouvelle génération du fichier, réimportez-le si vous souhaitez actualiser cette copie. Selon l’application, les événements déjà importés peuvent être dupliqués ; il peut être préférable de supprimer l’ancien calendrier importé avant de recommencer.

## S’abonner depuis un iPhone

Le calendrier est publié sur GitHub à une adresse stable. Touchez ce lien depuis l’iPhone pour ouvrir l’abonnement dans Calendrier :

**[S’abonner au calendrier UBB et XV de France](webcal://raw.githubusercontent.com/jogeoth-cyber/Calandrier/main/calendrier_ubb_xv_france.ics)**

Si le lien ne lance pas Calendrier, copiez cette adresse HTTPS :

`https://raw.githubusercontent.com/jogeoth-cyber/Calandrier/main/calendrier_ubb_xv_france.ics`

Puis, sur les versions récentes d’iOS : **Réglages > Apps > Calendrier > Comptes Calendrier > Ajouter un compte > Autre > Ajouter un calendrier avec abonnement**. Collez l’adresse HTTPS dans le champ **Serveur**, puis validez. Sur les anciennes versions, le chemin commence par **Réglages > Calendrier > Comptes**.

Le calendrier est public : les personnes disposant du lien peuvent consulter les rencontres. Un workflow GitHub actualise le fichier chaque jour vers 06:00 UTC ; Calendrier récupère ensuite les changements selon son propre rythme de synchronisation.

## S’abonner avec d’autres applications

- **Google Agenda** : dans **Autres agendas**, choisissez **À partir de l’URL**, collez l’adresse HTTPS ci-dessus, puis ajoutez le calendrier.
- **Outlook** : utilisez l’ajout d’un calendrier à partir d’Internet ou d’une URL, puis collez l’adresse HTTPS.
- **Apple Calendrier sur Mac** : choisissez **Fichier > Nouvel abonnement au calendrier…**, puis collez l’adresse HTTPS.

Un import du fichier ICS local est une copie ponctuelle et ne se met pas automatiquement à jour. Pour profiter des mises à jour, abonnez-vous à l’adresse ci-dessus.

## Chaînes TV

Une ligne de diffusion figure dans la description de chaque rencontre. Le script ne renseigne un nom de chaîne que si une source de données lui fournit explicitement ce nom ; sinon, le calendrier indique **« non communiquée à ce jour (à confirmer) »**. Pour les rencontres contrôlées actuellement, la source officielle FFR ne publie pas de nom de diffuseur.
