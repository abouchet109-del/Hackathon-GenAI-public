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

Cas de démonstration : **Atlas**, le lancement d'un portail client fictif dont les sources se contredisent. Détail : [docs/use-case-atlas.md](use-case-atlas.md).

## Technologies
| Technologie | Rôle |
|---|---|
| Zetaris | Couche de données : les sources du projet exposées comme des tables SQL |
| Meterless World Model | État courant du projet : membres et rôles, tâches et dépendances, décisions en vigueur, blocages ; chaque changement crée une nouvelle version (D12) |
| Meterless H-MEM | Mémoires à trois échelles : la journée, le projet en cours (historique des décisions, comptes rendus, verdicts sur les réunions) et l'organisation (enseignements des projets passés) (D12) |
| Meterless Nightshift | Fournisseur IA principal |
| NVIDIA Nemotron | Modèles des agents, via Nightshift |
| MCP | Accès à l'état du projet depuis l'IA de chaque membre |

## État d'avancement
Détail : [docs/STATUS.md](STATUS.md).

| Étape | État |
|---|---|
| Environnement (Zetaris en local, provider Meterless Runtime testé contre un faux runtime) | Fait |
| Zetaris | **Fonctionne** (27/10) : base `ATLAS`, une table REST par source Atlas (jsDelivr épinglé), relues en SQL par `atlas/zetaris.py` ; cache pour `SAMPLE_MODE` |
| Meterless Nightshift | **Fonctionne** (27/10) : runtime en ligne sur le port 8088, réponse reçue via `meterless/auto` |
| Modèle Nemotron | **Imposé dans Nightshift** (27/10) par son identifiant (`nvidia/nemotron-3.5-lightning-30b-a3b`) ; le modèle réellement utilisé est lu dans le reçu de Nightshift et écrit dans la trace JSONL (`atlas/structured.py`) |
| Cas d'usage Atlas | Défini |
| Architecture | **Brouillon complété** (27/10) : trois revues intégrées ; briques 1, 2, 4, 5 et 7, orchestrateur, couches Zetaris / World Model / H-MEM, schéma fonctionnel |
| Fondations déterministes | **Faites et testées** (27/10) : format des décisions, classement en quatre cas, boîtes d'alertes, contrats entre composants (`atlas/contracts.py`), appel LLM commun (sortie JSON validée, une nouvelle tentative, timeout, repli, trace) |
| Engine H-MEM | **Intégré** (27/10, 18:10) : service TypeScript `services/hmem/` autour de l'implémentation de référence, inchangée (D11 bis), client Python `atlas/hmem.py` (décisions avec provenance et confiance, journal de confiance qui répond à « pourquoi le 10 novembre ? », retours helpful/wrong, enseignements d'Orion) ; **conformité officielle 13/13** ; repli local en Python |
| Engine World Model | **Intégré** (27/10, 18:30) : service `services/world_model/` autour de la référence, inchangée ; `atlas/world_model.py` implémente l'interface d'état (`atlas/state.py`) : événements en ajout seul, pas de doublon à la réingestion, arêtes datées ; **conformité officielle 8/8** ; repli sur l'état JSON (D12) |
| Données Atlas pour Zetaris | **Faites** (27/10) : corpus synthétique, variantes S2 et S3, résultats attendus S1 à S9 |
| Brique 1 et bout en bout (incrément 1) | **Fait** (27/10, 19:25) : état du projet versionné (`atlas/state.py`), extracteur, agent de mise à jour, contrôleur (contrôles en code, puis preuves vérifiées par le LLM ; une révision, puis escalade), écriture de l'état avec alertes et H-MEM, agent manager, orchestrateur (limites, replis, `SAMPLE_MODE`, traces) et `POST /run` ; runs réels S1 et S3 comparés aux attendus |
| Serveur MCP, remontées (brique 7), livrables (brique 4), réunions (brique 5) | Pas commencés |

**Fondations déjà codées** (toutes couvertes par des tests unitaires, 36 tests au vert) :
- `atlas/decisions.py` : l'enregistrement d'une décision (sujet, attribut, valeur, statut, auteur, source, date, confiance, décision remplacée) et les règles qui disent quelle décision est en vigueur. Deux décisions approuvées incompatibles sont un conflit à arbitrer, jamais « la dernière gagne ».
- `atlas/progress.py` : le classement de l'avancement de chaque membre en quatre cas (tout va bien, retard, travail rendu obsolète par une décision, réunion nécessaire).
- `atlas/alerts.py` : les boîtes d'alertes par membre, déposées par l'algorithme de notification et récupérées une seule fois via MCP.
- `scripts/engine_service.py` lance un service d'engine Meterless (H-MEM ou World Model) ; `scripts/engines_conformance.py` lance leurs deux suites de conformité officielles ; `scripts/load_org_memory.py` charge les enseignements des projets passés dans la mémoire de l'organisation (S9).

**Track : 03 — Reasoning Architecture.**

**Architecture du 27/10** ([docs/architecture.md](architecture.md), avec un schéma fonctionnel en tête ; notes manuscrites dans [docs/architecture-notes/](architecture-notes/)). Brouillon complété par deux revues, pas encore l'architecture finale. Six agents LLM, chacun avec une seule mission ; tout le reste est en code. Principe directeur : **le LLM qualifie, le code tranche** (D13).
- **Brique 1 — Contexte fiable** : un extracteur tire les informations des sources lues dans Zetaris ; l'agent de mise à jour les rattache au bon sujet et les qualifie ; des règles en code décident ce qui fait foi ; un contrôleur vérifie habilitations, conflits et preuves, demande une révision au plus ou escalade. Un seul écrivain met à jour l'état (World Model) et l'historique (H-MEM), puis un algorithme dépose une alerte chez chaque personne concernée.
- **Brique 2 — Avancement par membre** : l'IA de chaque collaborateur remonte un rapport structuré par l'outil MCP `report_progress` (un skill dit quand et quoi déclarer) ; ce rapport est aussi une source de la brique 1. Un algorithme, sans LLM, classe chaque tâche : tout va bien, retard, travail obsolète, contradiction entre membres, ou signal de coordination.
- **Brique 4 — Correction des livrables** : les affirmations d'un livrable sont comparées en code à l'état du projet ; un rédacteur corrige seulement les passages périmés ; un validateur vérifie que chaque changement cite sa source. Résultat : un diff proposé, jamais appliqué automatiquement.
- **Brique 5 — Recommandation de réunion** : un tri en code note des réunions candidates à partir de déclencheurs tirés de la littérature (Gersick, Thompson, Vroom & Yetton…) moins leurs coûts, et choisit entre réunion et message ; au-dessus du seuil, un analyste en lecture seule juge en s'appuyant sur les précédents gardés dans H-MEM ; le verdict humain est enregistré et sert aux fois suivantes.
- **Brique 7 — Remontées et vue manager** : trois modes. Un point périodique part même quand tout va bien (tenue du planning, changements, avancement par membre). Les exceptions sont décidées par des règles en code (tolérance de délai dépassée en prévision, décision hors délégation, changement d'une date ou du périmètre…), avec un niveau de priorité et leurs preuves. Le manager peut aussi poser ses questions. Il passe par son IA, avec un skill qui appelle le serveur MCP.
- **Agent manager et orchestrateur** : l'orchestrateur, en code, enchaîne un run complet ; l'agent manager rédige le point périodique et répond aux questions du manager (`POST /run` ou MCP) ; un contrôle en code vérifie qu'aucune remontée urgente n'est omise.

## Structure du repo
**Les données de `data/` sont synthétiques** (entreprise et projet fictifs, règlement §11.1) ; chaque fichier le déclare (`"synthetic": true`).

```text
agent/              Logique de l'agent (provider Meterless Runtime déjà en place : agent/llm.py)
tests/              Tests (dont le provider Meterless)
data/sample/        Corpus Atlas synthétique : un JSON {"records": [...]} par source Zetaris
data/scenarios/     Variantes injectées pour les scénarios S2, S3 et S8
data/expected/      Résultats attendus des scénarios S1 à S9 (évaluation seulement, jamais lus par les agents)
evaluation/         Chargement des résultats attendus
scripts/            Scripts utilitaires (register_zetaris.py : sources Zetaris ; engine_service.py : services H-MEM et World Model)
services/           Services locaux autour des engines Meterless (H-MEM, World Model), en TypeScript
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
| [docs/CONTEXT.md](CONTEXT.md) | **À lire en premier** : le hackathon, l'idée, le cas d'usage, l'environnement |
| [docs/use-case-atlas.md](use-case-atlas.md) | Le cas d'usage en détail : scénario, règles, données, démo |
| [docs/architecture.md](architecture.md) | L'architecture (en cours) |
| [docs/STATUS.md](STATUS.md) | Ce qui est fait, ce qui bloque, la suite |
| [docs/atlas/PLAN.md](PLAN.md) | Ce qu'il reste à construire, estimations, incréments et méthode de travail |
| [docs/reference/guide-architecture-agentique.md](reference/guide-architecture-agentique.md) | Les principes d'architecture que l'on suit |
| [docs/strategie/](strategie/) | Prompt jury et évaluation des use cases |
| [docs/hackathon/](hackathon/) | Documents officiels du hackathon |

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
.venv/Scripts/python -m atlas.llm status
```

### Engines Meterless (H-MEM et World Model)
Node.js 20 ou plus requis. Les implémentations de référence (Apache-2.0) ne sont pas copiées dans le repo : au premier lancement, le script clone https://github.com/Meterless/Meterless dans `external/meterless` (ignoré par git) et installe leurs outils de développement (`npm ci`, sans dépendance d'exécution). Chaque service tourne dans son propre terminal :

```bash
.venv/Scripts/python scripts/engine_service.py hmem
```

```bash
.venv/Scripts/python scripts/engine_service.py world_model
```

H-MEM écoute sur `http://127.0.0.1:8765` (`ATLAS_HMEM_URL` ; `HMEM_URL` désigne le service Steward `hmem-service/` sur 8787, dont l’API est différente), World Model sur `http://127.0.0.1:8766` (`WORLD_MODEL_URL`) ; les données restent dans `.state/` (ignoré par git). Sans service, ou avec `SAMPLE_MODE=true`, les clients Python prennent leur repli (mémoire locale pour H-MEM, état JSON pour World Model) et le disent (`origin`). Les tests d'intégration (`tests/test_hmem_service.py`, `tests/test_world_model.py`) sont ignorés, avec un message, quand les services ne tournent pas ; ils écrivent sous un sujet ou un projet de test à eux.

Charger les enseignements des projets passés (Orion, Vega) dans la mémoire de l'organisation ; puis, une fois qu'un run a enregistré les décisions validées (l'écrivain, `atlas/writer.py`, les écrit dans H-MEM), demander « pourquoi cette date ? » :

```bash
.venv/Scripts/python scripts/load_org_memory.py
```

```bash
.venv/Scripts/python -m atlas.hmem explain atlas-launch launch_date
```

Suites de conformité officielles (H-MEM 13/13, World Model 8/8) :

```bash
.venv/Scripts/python scripts/engines_conformance.py
```

### Lancer le système : un run, ou `POST /run`
Un run lit les sources dans Zetaris, fait passer les messages par l'extracteur, l'agent de mise à jour et le contrôleur (une révision au plus, puis escalade), écrit l'état (World Model, repli JSON) et les décisions validées (H-MEM), dépose les alertes, puis l'agent manager répond à la question du manager. Le point d'entrée est `atlas/orchestrator.py` ; `atlas/api.py` l'expose en HTTP.

Sans aucun service ni clé, en `SAMPLE_MODE` (la vraie logique, sur les caches commités de Zetaris et de Nemotron) :

```bash
SAMPLE_MODE=true .venv/Scripts/python -m atlas.orchestrator --today 2026-10-27
```

Le scénario S3 (deux décisions approuvées incompatibles) :

```bash
SAMPLE_MODE=true .venv/Scripts/python -m atlas.orchestrator --today 2026-10-27 --scenario S3
```

En réel (clé Zetaris dans `.env`, Nightshift lancé ; services H-MEM et World Model conseillés), même commande sans `SAMPLE_MODE` : environ 5 à 7 minutes et 45 à 50 appels à Nemotron 3 Ultra (D16). Le serveur HTTP :

```bash
.venv/Scripts/python -m atlas.api --port 8080
```

```bash
curl -X POST http://127.0.0.1:8080/run -H "Content-Type: application/json" -d "{\"today\": \"2026-10-27\", \"scenario\": \"S3\"}"
```

Entrée (`RunRequest`, tous les champs sont facultatifs ; un champ inconnu est refusé avec un 400 détaillé) :

| Champ | Défaut | Rôle |
|---|---|---|
| `project` | `atlas` | Projet dont on lit l'état |
| `question` | la requête de la section 1 de l'architecture | Question du manager, à laquelle répond l'agent manager |
| `today` | date du serveur | Date de référence des règles (retards, échéances) |
| `scenario` | aucun | `S2` ou `S3` : ajoute `data/scenarios/<s>-*.json` aux sources |
| `fresh_state` | vrai pour un scénario, faux sinon | Faux : l'état persiste d'un run à l'autre et un second run ne relit que ce qui est nouveau (S5) |
| `max_llm_calls` | 120 | Budget d'appels LLM du run |
| `timeout_s` | 900 | Durée maximale du run |

Sortie (`RunResult`) : `run_id`, `state_store` et `state_version` (où et quelle version de l'état), `sources` (d'où chaque source a été lue : `zetaris`, `cache`, `cache-fallback`, `files`), `memory` (H-MEM : service ou repli local), `in_force` et `conflicts` (décisions en vigueur et conflits à arbitrer), `verdicts` (chaque verdict du contrôleur, révisions comprises), `escalations` (à qui, pourquoi), `alerts` (déposées chez les membres concernés), `facts` (jalons avec leur verdict calculé en code, avancement par membre, blocages, réunions), `report` (la réponse de l'agent manager et son contrôle), `limits` (appels, durée, arrêt anticipé), `degraded` (replis pris, messages sautés) et `trace_file`.

Chaque run écrit une trace JSONL dans `logs/run-<run_id>.jsonl` : chaque appel LLM (agent, action, version du prompt, modèle **réellement utilisé** lu dans le reçu de Nightshift, tentatives, statut) et chaque étape (lecture des sources, verdict du contrôleur, écriture, alertes).

Après une modification d'un prompt, le cache LLM de `SAMPLE_MODE` ne correspond plus : le régénérer par deux runs réels. `LLM_CACHE_FIRST=true` réutilise une réponse déjà enregistrée, pour que S1 et S3 se rejouent de façon cohérente (le modèle n'est pas déterministe) :

```bash
LLM_CACHE_FIRST=true .venv/Scripts/python -m atlas.orchestrator --today 2026-10-27 --fresh
```

```bash
LLM_CACHE_FIRST=true .venv/Scripts/python -m atlas.orchestrator --today 2026-10-27 --scenario S3
```

## Travailler sur le projet
- Lire [docs/CONTEXT.md](CONTEXT.md), puis [docs/STATUS.md](STATUS.md).
- Une étape à la fois : on teste, on committe, on met à jour `docs/STATUS.md`.
- Ne jamais committer `.env` ni aucune clé.
