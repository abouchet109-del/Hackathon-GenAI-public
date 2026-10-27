# Journal du projet

Historique horodaté de ce qui a été fait, session par session (heure de Paris). L'entrée la plus récente est en haut. Chaque session ajoute une entrée avant son dernier push (section 8 de `CLAUDE.md`). Le détail ligne à ligne reste dans `git log`.

Format d'une entrée :

```text
## JJ/MM HH:MM — titre de la session
- Fait : ...
- Tâches du plan : n° ... (incrément ...), état
- Commits : ...
- Vérifié : tests, exécution réelle...
- Reste / prochaine session : ...
```

---

## 27/10 18:30 — Incrément 2 : H-MEM (n° 8), Orion (n° 9), World Model (n° 7) (session dédiée)
- Fait : client `agent/hmem.py` (décision avec provenance et confiance, `explain` qui répond à « pourquoi le 10 novembre ? » par l'historique et le journal de confiance, retours helpful/not_helpful/wrong, rappel des enseignements), avec repli local en Python ; service `services/hmem/` autour de la référence H-MEM inchangée (résolution automatique des conflits jamais appelée) ; `scripts/load_org_memory.py` (enseignements d'Orion et Vega lus via Zetaris) ; service `services/world_model/` et adaptateur `agent/world_model.py` qui implémente `StateStore` sans toucher à `agent/state.py`, repli sur l'état JSON ; `scripts/engine_service.py` (lancement des deux services) et `scripts/engines_conformance.py` (les deux suites officielles).
- Tâches du plan : n° 8 faite ; n° 9 faite côté mémoire (le rappel reste à brancher dans la brique 5 ou le brief) ; n° 7 faite.
- Commits : 499df21, 0bd1728, 7aa6e21, puis le commit de cette entrée.
- Vérifié : 144 tests au vert avec les deux services lancés (intégration H-MEM 5/5, World Model 4/4 contre les vrais services) ; sans service, ces tests sont ignorés avec un message ; conformité H-MEM 13/13 et World Model 8/8 ; chargement d'Orion contre le service, sur repli et en `SAMPLE_MODE`.
- Non vérifié : le lanceur PowerShell (`.ps1`) ne peut pas s'exécuter sur ce poste (politique d'exécution) : lanceurs écrits en Python à la place ; `scripts/hmem-conformance.ps1` est gardé tel quel.
- Reste / prochaine session : brancher `WorldModelStateStore` et `HMem` dans l'orchestrateur (fichiers de l'incrément 1), recharger les enseignements à chaque run en `SAMPLE_MODE`, rappeler Orion dans la brique 5 ou le brief (S9).

## 27/10 17:58 — Incrément 0, tâches 4 et 5 (session dédiée)
- Fait : Nemotron imposé dans Nightshift par son identifiant ; appel LLM commun `agent/structured.py` (schéma pydantic, une nouvelle tentative, timeout, routes Nightshift puis `MODEL_*` puis cache, trace JSONL avec le modèle lu dans le reçu de Nightshift). Horodatages de `docs/STATUS.md` corrigés (des heures fausses avaient été écrites pour les tâches 1 à 3).
- Tâches du plan : n° 4 et 5 (incrément 0), faites. Incrément 0 terminé.
- Commits : voir le commit « Impose Nemotron in Nightshift and add the common LLM call ».
- Vérifié : 68 tests au vert ; appel réel via Nightshift (MSG-007 → proposition, modèle `nvidia/nemotron-3.5-lightning-30b-a3b`, reçu tracé).
- Reste : décisions de l'équipe (D11, World Model, fusion de l'analyste, brique 5 réduite), puis incréments 1 et 2.

## 27/10 17:49 — Incrément 0, tâches 2 et 3 (session dédiée)
- Fait : sources Atlas enregistrées dans Zetaris (script idempotent), client Zetaris avec cache pour `SAMPLE_MODE`.
- Tâches du plan : n° 2 et 3 (incrément 0), faites.
- Commits : 167c618. Vérifié : 60 tests au vert (suite relancée à 17:58).
- Reste : n° 4 et 5 (Nemotron, appel LLM commun).

## 27/10 17:55 — Instructions de Claude et suivi du projet
- Fait : `CLAUDE.md` réécrit (synchronisation au démarrage, boucle comprendre, planifier, tester, faire, vérifier, relire, livrer ; principes de code et des systèmes agentiques ; relecture avant commit ; git en parallèle ; protocole de fin de session) ; ce journal ; section 7 « Suivi » dans `docs/PLAN.md`. Un `AGENTS.md` créé à 17:48 (e7d38b5) a été fusionné dans `CLAUDE.md` puis supprimé, à la demande de l'équipe.
- Commits : e7d38b5, puis le commit de ce journal.

## 27/10 17:31–17:40 — Incrément 0, tâches 1 et 2 (session dédiée)
- Fait : contrats entre composants dans `agent/contracts.py` ; corpus Atlas synthétique, variantes S2 et S3, résultats attendus de S1 à S9.
- Tâches du plan : contrats et n° 1 (incrément 0), faits.
- Commits : 76d3b58, 8501863. Tests : 52 au vert (rapport de la session).
- Reste : n° 2 (enregistrement dans Zetaris, en attente de l'accord de l'équipe pour créer la base et la première table), n° 3 à 5.

## 27/10 17:17–17:27 — Brique 7 et plan de construction
- Fait : brique 7 (remontées au manager, interface par l'IA du manager via un skill et MCP, D14) dans `docs/architecture.md` ; plan de construction `docs/PLAN.md` (inventaire, estimations probable et maximale, incréments, méthode).
- Commits : 2c84fcd, b836289.

## 27/10 11:40–11:55 — Deuxième revue de l'architecture (équipe)
- Fait : briques 4 et 5, couches Zetaris, World Model et H-MEM (D12, D13), schéma fonctionnel, mise à jour du README.
- Commits : 7e3f655 (PR #1, a506ef8), 85fd9af, a9e76dc, 961f320.

## 27/10 00:12–01:34 — Brouillon d'architecture et fondations déterministes
- Fait : brouillon de l'équipe et propositions de la première revue ; `agent/decisions.py`, `agent/progress.py`, `agent/alerts.py` (36 tests au vert) ; script de conformité H-MEM (13/13) ; connexions Zetaris, Nightshift et Nemotron vérifiées.
- Commits : d0cc125, 2e4d5d1, 1476314, 7a378de, a5b098e.

## 26/10 23:21–23:51 — Organisation du repo et cas Atlas
- Fait : structure du repo, documentation du cas Atlas, alignement du prompt jury, extension du produit (avancement, réunions, remontées au manager).
- Commits : 6483a71, e97b04c, 3a9ebdf, 8aad208.
