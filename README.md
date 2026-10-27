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
| Clé API Zetaris | Renseignée, connexion pas encore testée |
| Meterless Nightshift | **Bloqué** : ne fonctionne pas encore sur la machine |
| Cas d'usage Atlas | Défini |
| Architecture | **Brouillon en cours** (27/10) |
| Données Atlas pour Zetaris | À créer |
| Agents, MCP, vue manager | Pas commencés |

**Brouillon d'architecture du 27/10** ([docs/architecture.md](docs/architecture.md), notes manuscrites dans [docs/architecture-notes/](docs/architecture-notes/)) : deux briques sont définies.
- **Suivi des décisions** : un agent rédige les comptes rendus de réunion, un agent relit le canal commun et n'en garde que les décisions, un agent les rapproche des décisions déjà prises et décide ce qui fait foi, puis un algorithme prévient les personnes concernées. Les décisions sont gardées dans H-MEM.
- **Avancement par membre** : un skill installé sur l'IA de chaque collaborateur remonte son avancement ; un agent, en lecture seule, le compare aux tâches et objectifs ; un algorithme classe chaque situation (tout va bien, retard, travail rendu obsolète par une décision) et agit en conséquence. Un agent dédié remontera l'information au manager.

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

Les instructions complètes (sources Zetaris, `SAMPLE_MODE`, point d'entrée de l'agent) seront ajoutées au fil de la construction.

## Travailler sur le projet
- Lire [docs/CONTEXT.md](docs/CONTEXT.md), puis [docs/STATUS.md](docs/STATUS.md).
- Une étape à la fois : on teste, on committe, on met à jour `docs/STATUS.md`.
- Ne jamais committer `.env` ni aucune clé.
