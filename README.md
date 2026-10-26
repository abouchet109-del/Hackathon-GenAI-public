# Open Agent Hackathon 2026 — mémoire projet partagée entre IA

> Projet en cours de construction pour l'[Open Agent Hackathon 2026](https://hackathon.genai.works/event/open-agent-hackathon-2026). Clôture des soumissions : **27 octobre 2026, 23:45 UTC**.

## Le problème
Dans une équipe, chacun travaille avec son IA (ChatGPT, Claude, Cursor…), qui garde sa propre mémoire. Les décisions, l'avancement et le contexte du projet se dispersent : un brief reprend une date abandonnée, deux personnes avancent dans des directions contradictoires, et personne ne voit l'incohérence avant qu'elle ne parte chez le client.

## Notre réponse
Un agent qui garde l'équipe alignée :
- il rapproche les sources dispersées du projet (documents, messages, tickets, registre de décisions), servies par **Zetaris** ;
- il distingue ce qui fait foi (une décision approuvée par une personne habilitée) de ce qui ne fait pas foi (une proposition, un message, une information remplacée) ;
- il suit l'avancement de chaque membre et détecte les travaux contradictoires avant qu'ils ne produisent un livrable ;
- il prépare la correction des livrables périmés, avec les sources de chaque changement ;
- chaque membre récupère l'état du projet depuis son IA via **MCP**, et le manager le suit dans une vue dédiée.

Cas de démonstration : **Atlas**, le lancement d'un portail client fictif dont les sources se contredisent. Détail : [docs/use-case-atlas.md](docs/use-case-atlas.md).

## Technologies
| Technologie | Rôle |
|---|---|
| Zetaris | Couche de données : les sources du projet exposées comme des tables SQL |
| Meterless World Model | État partagé du projet : décisions, observations, travail en cours de chaque membre, versions |
| Meterless Nightshift | Fournisseur IA principal |
| NVIDIA Nemotron | Modèles des agents, via Nightshift |
| MCP | Accès à l'état du projet depuis l'IA de chaque membre |

## État d'avancement
Voir [docs/STATUS.md](docs/STATUS.md). À ce jour : environnement en place, provider Meterless Runtime codé et testé contre un faux runtime, cas d'usage défini, architecture en cours de conception. L'agent n'est pas encore construit.

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
