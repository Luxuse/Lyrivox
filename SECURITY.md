# Politique de Sécurité Lyrivox

Ce document décrit la politique de sécurité pour les scripts Python du projet Lyrivox (Générateur et Décodeur sonores textuels).

## Comment signaler une Vulnérabilité

Si vous pensez avoir découvert une vulnérabilité de sécurité dans Lyrivox, veuillez la signaler de manière responsable. Nous apprécions l'aide des chercheurs en sécurité pour identifier et corriger les problèmes.

Étant donné la nature actuelle de ce projet (développé et partagé potentiellement de manière informelle), il n'y a pas de canal de signalement de vulnérabilité formel ou public (comme un bug tracker dédié à la sécurité ou une adresse email spécifique).

**Pour signaler une vulnérabilité :**

Veuillez contacter directement l'auteur principal ou le responsable du code. Si vous avez obtenu ce code dans un contexte particulier (par exemple, un dépôt en ligne, un forum), veuillez utiliser les moyens de contact associés à cette source pour joindre l'auteur.

Lorsque vous signalez une vulnérabilité, veuillez inclure autant de détails que possible :

-   Une description claire et concise de la vulnérabilité.
-   Les étapes pour reproduire la vulnérabilité.
-   Les versions des scripts Lyrivox utilisées.
-   Votre environnement (Système d'exploitation, version de Python, bibliothèques installées comme `sounddevice`).
-   Tout impact potentiel de la vulnérabilité.

Veuillez ne pas divulguer publiquement la vulnérabilité avant qu'elle n'ait été examinée et corrigée.

## Approche de la Sécurité

Lyrivox est conçu comme un outil de conversion texte-son et son-texte basé sur un simple mappage de fréquences. Il est important de noter ce qui suit concernant la sécurité :

1.  **Aucune gestion de Données Sensibles :** Les scripts eux-mêmes ne sont pas conçus pour gérer, stocker ou transmettre des données utilisateur sensibles (mots de passe, informations financières, etc.). Si vous choisissez d'encoder/décoder de telles données, elles seront traitées localement comme n'importe quel autre texte.
2.  **Aucune Connectivité Réseau :** Les scripts n'établissent aucune connexion réseau entrante ou sortante. Cela réduit considérablement la surface d'attaque distante.
3.  **Fiabilité de l'Encodage Audio :** La méthode d'encodage/décodage basée sur des fréquences audio est **non cryptographique** et **hautement sensible au bruit et aux interférences**. Elle n'offre aucune garantie de confidentialité, d'intégrité ou d'authenticité des données transmises par ce canal audio. Le décodage peut facilement produire des erreurs si le signal audio est dégradé. L'encodage Base64 ajoute une couche de formatage, mais ne rend pas la transmission plus robuste face à la corruption audio, comme démontré par les erreurs de décodage Base64 en cas de corruption du signal.
4.  **Exécution Locale :** Le générateur lance le décodeur via une commande système (`subprocess.Popen`). Si les fichiers script Lyrivox sont remplacés par du code malveillant sur votre système local, cela pourrait présenter un risque d'exécution locale. Assurez-vous de toujours obtenir les scripts d'une source fiable.
5.  **Manipulation de Fichiers Locaux :** Le générateur écrit des fichiers `.wav` dans le répertoire courant et les ouvre. Assurez-vous que le répertoire où les scripts sont exécutés dispose des permissions appropriées et n'est pas un emplacement système sensible où un fichier `.wav` pourrait causer des problèmes s'il était malformé ou mal nommé (bien que les mesures de base aient été prises pour le nommage).

Lyrivox est un outil simple pour l'expérimentation et la communication non sécurisée via audio. Il ne convient pas aux cas d'utilisation nécessitant une sécurité ou une fiabilité des données élevées.

## Problèmes Connus Liés à la Sécurité (par conception/limitation)

-   La méthode d'encodage/décodage est intrinsèquement non sécurisée et non fiable en raison des limitations du canal audio. Le bruit peut causer des erreurs de décodage significatives.
-   La robustesse du décodage (particulièrement pour Base64) dépend fortement de la qualité du signal audio capturé.

---

## Avertissement sur l'Utilisation Audio

Lyrivox génère des tons audio basés sur du texte converti en fréquences. L'écoute de ces tons, en particulier via des systèmes de lecture audio (enceintes, écouteurs, casques), et notamment à des volumes élevés ou prolongés, peut potentiellement causer des dommages :

-   **À vos équipements audio** (distorsion, surcharge des haut-parleurs).
-   **À votre audition** (lésions auditives temporaires ou permanentes).

Vous êtes entièrement responsable du contrôle du volume de lecture sur votre système audio et de toute conséquence directe ou indirecte (dommages matériels ou corporels) qui pourrait résulter de l'utilisation du son généré par Lyrivox. L'auteur, les contributeurs ou toute personne associée au projet Lyrivox ne sauraient être tenus responsables de tels dommages.

**Utilisez toujours Lyrivox avec un volume sonore faible à modéré et soyez attentifs à votre environnement et à la sensibilité de vos équipements/oreilles.**

---

Ce fichier `SECURITY.md` a été créé le 19 Avril 2025. Il pourra être mis à jour si le projet évolue ou si de nouvelles préoccupations de sécurité apparaissent.
