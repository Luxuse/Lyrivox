# Lyrivox : Convertir et Écouter du Texte par Audio

Lyrivox est un projet innovant qui permet de transformer du texte en une expérience audio unique. Il se compose de deux modules distincts :

* **Lyrivox-S :** Le synthétiseur audio textuel, responsable de la conversion de texte en un fichier sonore.
* **Lyrivox-LST :** Le lecteur audio Lyrivox, conçu pour écouter les fichiers audio générés par Lyrivox-S.

## Description

### Lyrivox-S : Synthétiseur Audio Textuel

Lyrivox-S est le cœur de la conversion. Il prend en entrée un fichier texte contenant le message que vous souhaitez « entendre ». Chaque caractère de ce texte est méticuleusement transformé en une tonalité sonore distincte, créant ainsi une représentation auditive du contenu textuel. Le résultat de cette conversion est un fichier audio standard au format WAV, prêt à être écouté.

### Lyrivox-LST : Lecteur Audio Lyrivox

Une fois que Lyrivox-S a généré le fichier audio, Lyrivox-LST entre en jeu. Ce module est un lecteur audio simple mais efficace, spécialement conçu pour lire les fichiers WAV produits par Lyrivox-S. Il prend le fichier audio généré et le diffuse via les haut-parleurs de votre ordinateur, vous permettant d'écouter le message originalement sous forme de texte.

## Fonctionnalités Clés

* **Lyrivox-S : Conversion Texte-vers-Son**
    * Prend en charge la lecture de fichiers texte comme source.
    * Transforme chaque caractère en une tonalité sonore unique.
    * Génère un fichier audio de sortie au format WAV, compatible avec la plupart des lecteurs audio.
* **Lyrivox-LST : Lecture Audio Dédiée**
    * Lit les fichiers audio WAV créés par Lyrivox-S.
    * Interface utilisateur simple pour la lecture audio.
    * Permet d'écouter le texte converti via les haut-parleurs de l'ordinateur.

## Exemple de Workflow Utilisateur

1.  **Préparation du Texte :** Commencez par écrire le message que vous souhaitez entendre dans un fichier texte, ou chargez un fichier texte existant.
2.  **Synthèse Audio avec Lyrivox-S :** Exécutez le module Lyrivox-S en lui fournissant le fichier texte préparé. Ce processus convertira le texte en un fichier audio au format WAV.
3.  **Écoute avec Lyrivox-LST :** Lancez le module Lyrivox-LST et ouvrez le fichier audio WAV généré à l'étape précédente. Le lecteur diffusera alors le son, vous permettant d'écouter le contenu du texte original.
