# Open Agent Hackathon 2026 — mémoire projet partagée entre IA

> Projet en cours de construction pour l'[Open Agent Hackathon 2026](https://hackathon.genai.works/event/open-agent-hackathon-2026). Clôture des soumissions : **27 octobre 2026, 23:45 UTC**.

## Le problème
Dans une équipe, chacun travaille avec son IA (ChatGPT, Claude, Cursor…), qui garde sa propre mémoire. Les décisions, l'avancement et le contexte du projet se dispersent : un brief reprend une date abandonnée, deux personnes avancent dans des directions contradictoires, et personne ne voit l'incohérence avant qu'elle ne parte chez le client.

## Notre réponse
Une mémoire projet autonome, qui appartient à l'entreprise et garde l'équipe coordonnée :
- elle rapproche les sources dispersées du projet (documents, messages, tickets, tâches, registre de décisions), servies par **Zetaris** ;
- elle distingue ce qui fait foi (une décision approuvée par une personne habilitée) de ce qui ne fait pas foi (une proposition, un message, une information remplacée) ;
- elle suit l'avancement de chaque membre par rapport à ses tâches et objectifs, et détecte les travaux contradictoires avant qu'ils ne produisent un livrable ;
- elle prépare la correction des livrables périmés, avec les sources de chaque changement ;
- elle recommande une réunion quand l'avancement de chacun l'exige, avec les bonnes personnes et un ordre du jour ;
- elle donne au manager une vue d'ensemble, sur un petit comme sur un gros projet, et lui remonte automatiquement ce qui compte ;
- elle garde la mémoire de l'avancement du projet et celle des projets passés de l'organisation ;
- chaque membre récupère l'état du projet depuis son IA via **MCP**.

Cas de démonstration : **Atlas**, le lancement d'un portail client fictif dont les sources se contredisent. Détail : [docs/use-case-atlas.md](docs/use-case-atlas.md).

## Technologies
| Technologie | Rôle |
|---|---|
| Zetaris | Couche de données : les sources du projet exposées comme des tables SQL |
| Meterless H-MEM | Mémoires du projet : décisions et leur historique, rôles et avancement de chaque membre (choix du brouillon d'architecture) |
| Meterless World Model (option) | État partagé entre agents, si l'architecture finale le retient |
| Meterless Nightshift | Fournisseur IA principal |
| NVIDIA Nemotron | Modèles des agents, via Nightshift |
| MCP | Accès à l'état du projet depuis l'IA de chaque membre |

## État d'avancement
Détail : [docs/STATUS.md](docs/STATUS.md).

| Étape | État |
|---|---|
| Environnement (Zetaris en local, provider Meterless Runtime testé contre un faux runtime) | Fait |
| Zetaris | Connexion vérifiée le 27/10 : SQL via l'API REST avec la clé de l'équipe |
| Meterless Nightshift | **Fonctionne** (27/10) : runtime en ligne sur le port 8088, réponse reçue via `meterless/auto` |
| Modèle Nemotron | Répond via la route `MODEL_*` (test de fumée) ; le choix explicite de Nemotron dans Nightshift reste à vérifier |
| Cas d'usage Atlas | Défini |
| Architecture | **Brouillon en cours** (27/10) |
| Fondations déterministes | **Faites et testées** (27/10) : format des décisions, classement en quatre cas, boîtes d'alertes |
| Engine H-MEM | Implémentation de référence installée, **suite de conformité officielle au vert (13/13)** ; intégration à l'application à décider |
| Données Atlas pour Zetaris | À créer |
| Agents LLM, MCP, vue manager | Pas commencés (attendent l'architecture finale) |

**Fondations déjà codées** (toutes couvertes par des tests unitaires, 36 tests au vert) :
- `agent/decisions.py` : l'enregistrement d'une décision (sujet, attribut, valeur, statut, auteur, source, date, confiance, décision remplacée) et les règles qui disent quelle décision est en vigueur. Deux décisions approuvées incompatibles sont un conflit à arbitrer, jamais « la dernière gagne ».
- `agent/progress.py` : le classement de l'avancement de chaque membre en quatre cas (tout va bien, retard, travail rendu obsolète par une décision, réunion nécessaire).
- `agent/alerts.py` : les boîtes d'alertes par membre, déposées par l'algorithme de notification et récupérées une seule fois via MCP.
- `scripts/hmem-conformance.ps1` : récupère le repo Meterless et lance la suite de conformité H-MEM.

**Track : 03 — Reasoning Architecture.**

**Brouillon d'architecture du 27/10** ([docs/architecture.md](docs/architecture.md), notes manuscrites dans [docs/architecture-notes/](docs/architecture-notes/)). C'est un brouillon de travail, loin de l'architecture finale. Il définit :
- **Suivi des décisions** : un extracteur tire les décisions des réunions et du canal commun ; un agent les rapproche des décisions déjà prises et propose ce qui fait foi ; un contrôleur vérifie preuves, habilitations et conflits, demande une révision ou escalade au manager ; un algorithme dépose une alerte chez chaque personne concernée. Les décisions sont gardées dans H-MEM.
- **Avancement par membre** : un skill installé sur l'IA de chaque collaborateur remonte son avancement via MCP et récupère ses alertes ; un agent, en lecture seule, le compare aux tâches et objectifs ; un algorithme classe chaque situation en quatre cas (tout va bien, retard, travail rendu obsolète, réunion nécessaire).
- **Agent manager** : répond à la requête du manager (`POST /run`), rédige les recommandations de réunion et les remontées automatiques.

## Structure du repo
```text
agent/              Logique de l'agent (provider Meterless Runtime déjà en place : agent/llm.py)
tests/              Tests (dont le provider Meterless)
data/sample/        Petits jeux de données (corpus Atlas, à venir)
scripts/            Scripts utilitaires (enregistrement des sources dans Zetaris, à venir)
input_examples/     Exemples d'entrées (à venir)
output_examples/    Exemples de sorties (à venir)
logs/               Traces des agents (créées à l'exécution)
docs/               Documentation du projet (voir ci-dessous)
external/           Matériel tiers pas encore relu (ignoré par git)
smoke_test.py       Test de connexion à Zetaris et au modèle
.env.example        Variables d'environnement (valeurs factices uniquement)
```

## Documentation
| Document | Pour quoi faire |
|---|---|
| [docs/CONTEXT.md](docs/CONTEXT.md) | **À lire en premier** : le hackathon, l'idée, le cas d'usage, l'environnement |
| [docs/use-case-atlas.md](docs/use-case-atlas.md) | Le cas d'usage en détail : scénario, règles, données, démo |
| [docs/architecture.md](docs/architecture.md) | L'architecture (en cours) |
| [docs/STATUS.md](docs/STATUS.md) | Ce qui est fait, ce qui bloque, la suite |
| [docs/reference/guide-architecture-agentique.md](docs/reference/guide-architecture-agentique.md) | Les principes d'architecture que l'on suit |
| [docs/strategie/](docs/strategie/) | Prompt jury et évaluation des use cases |
| [docs/hackathon/](docs/hackathon/) | Documents officiels du hackathon |

## Installation (état actuel)
Prérequis : Python 3.12, Zetaris en local, Meterless Nightshift.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install openai pydantic requests python-dotenv
cp .env.example .env
```

Remplir `.env` avec ses propres valeurs (jamais de clé dans le repo), puis :

```bash
.venv/Scripts/python -m unittest -v
```

```bash
.venv/Scripts/python smoke_test.py
```

```bash
.venv/Scripts/python -m agent.llm status
```

Suite de conformité H-MEM (Node.js requis) :

```bash
powershell -File scripts/hmem-conformance.ps1
```

Les instructions complètes (sources Zetaris, `SAMPLE_MODE`, point d'entrée de l'agent) seront ajoutées au fil de la construction.

## Travailler sur le projet
- Lire [docs/CONTEXT.md](docs/CONTEXT.md), puis [docs/STATUS.md](docs/STATUS.md).
- Une étape à la fois : on teste, on committe, on met à jour `docs/STATUS.md`.
- Ne jamais committer `.env` ni aucune clé.
