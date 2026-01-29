#  The Circle of Life - Simulation d'écosystème 

## Présentation du Projet
Ce projet est une simulation d'un écosystème composé de **prédateurs**, de **proies** et d'**herbe**. L'objectif est d'observer l'évolution des populations en fonction des ressources disponibles, des interactions biologiques et des aléas climatiques.

La simulation repose sur une architecture multi-processus en Python, utilisant diverses méthodes de communication inter-processus pour garantir la synchronisation des données.

---

## Architecture du Système

Le projet est divisé en quatre types de processus indépendants :

### 1. `env` (Environnement)
* **Gestionnaire central** : Il suit l'état des populations (prédateurs, proies, herbe), les conditions climatiques et les épidémies
* **Serveur Socket** : Il héberge un serveur TCP pour permettre aux individus de rejoindre la simulation.
* **Cycle de vie végétal** : Il gère la croissance de l'herbe et les épisodes de sécheresse.
* **Communication** : Il traite les ordres provenant de l'affichage via une **Message Queue**.

### 2. `predator` & `prey` (Individus)
* **Autonomie** : Chaque individu possède ses propres attributs comme l'énergie, un état (actif ou passif) et un âge.
* **Comportement** : Les individus consomment de l'énergie au fil du temps. Ils cherchent à se nourrir (herbe pour les proies, proies pour les prédateurs) et peuvent se reproduire si leur énergie est suffisante.
* **Mort** : Un processus se termine et notifie l'environnement si l'énergie de l'individu tombe à zéro ou si son âge dépasse un certain seuil.

### 3. `display` (Interface de Contrôle)
* **Visualisation** : Permet à l'opérateur d'observer les statistiques (naissances, décès, population) en temps réel.
* **Contrôle** : Permet d'initialiser les populations au démarrage et d'envoyer des signaux pour modifier l'environnement (sécheresse et épidémie).

---

## Mécanismes de Communication 

| Mécanisme | Utilisation dans le projet |
| :--- | :--- |
| **Shared Memory** | Stockage des compteurs de populations (entre autres) via `mp.Value`, protégés par un `mp.Lock`. |
| **Sockets (TCP)** | Communication entre les individus et `env` pour les messages de type JOIN, FEED, REPRODUCE et DEATH. |
| **Message Queue** | Échange de commandes (`cmd_queue`) et de données (`data_queue`) entre `display` et `env`. |
| **Signals (SIGUSR1/2)** | Déclenchement instantané d'une sécheresse ou d'une épidémie envoyé du processus `display` vers `env`. |

---

## Installation et Lancement

### Prérequis
* Python 3.x
* Un système compatible avec le module `multiprocessing` (Linux/macOS recommandé pour la gestion complète des signaux `os.kill`).

### Exécution
1. Placez tous les fichiers (`env_process.py`, `predator_process.py`, `prey_process.py`, `display_process2.py`, `config.py`) dans le même dossier.
2. Lancez le script principal :
   ```bash
   python display_process2.py