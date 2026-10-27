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

## 27/10 18:12–20:55 — Unification avec Steward sur la branche `unify` (session A, Ryan avec Claude)
- Fait : fusion des deux historiques ; `agent/` devient `atlas/` (imports réécrits, rien supprimé), les documents de l'équipe passent dans `docs/atlas/`, `docs/DECISIONS.md` garde la numérotation (D1–D17) et continue (D24–D36). `atlas.decisions`, `atlas.progress`, `atlas.alerts` tournent dans Steward (`app/coordination/bridge.py`). Le client `atlas/hmem.py` lit `ATLAS_HMEM_URL` (8765) pour ne pas entrer en collision avec `HMEM_URL` du service Steward (8787). Deux fusions des commits de l'équipe (`eb8199f`, `801575a`) sans perte.
- Tâches du plan : hors plan Atlas (prompt d'unification de Ryan) ; les briques 4, 5 et 7 restent telles quelles dans `atlas/`.
- Commits : 35c18ee (fusion), d81f26f (atlas/), 9889b6b et 903d1b2 (fusions de main), 23dd2a1 (état à 20:55) ; branche `unify` poussée sur GitHub.
- Vérifié : `python -m pytest -q` = 197 passés, 9 ignorés (vos tests d'intégration sans services) ; CI du dépôt verte sur `unify` (Linux, Windows, conformité H-MEM). Non vérifié : vos services `services/hmem` et `services/world_model` n'ont pas été lancés dans cette session.

## 27/10 19:25 — Incrément 1 : bout en bout (n° 6, 10, 11, 12, 13, 21, 22, 23) (session dédiée)
- Fait : état du projet versionné derrière `StateStore` (`atlas/state.py`) ; extracteur et agent de mise à jour séparés, prompts versionnés dans `atlas/prompts/` ; contrôleur (contrôles en code, puis preuves par le LLM, une révision, puis escalade à l'arbitre de la table des rôles) ; écriture de l'état (seul écrivain, alertes, décisions validées dans H-MEM) ; agent manager (verdicts en code, rapport contrôlé) ; orchestrateur (Zetaris, World Model, H-MEM, limites, replis, `SAMPLE_MODE`, trace JSONL par run) ; `POST /run`. Décisions D16 (Nemotron 3 Ultra pour les runs) et D17 (le registre fait foi, chronologie).
- Tâches du plan : n° 6, 10, 11, 12, 13, 21, 22 et 23 (incrément 1), faites.
- Commits : 463e2f2, 4a71d20, 6c6f965, f21fc0b, 5aaf2a9, eb8199f, abfaa7d, puis le commit de cette entrée.
- Vérifié : 167 tests au vert ; runs réels via Zetaris, Nightshift (Ultra), H-MEM et World Model : S1 conforme aux attendus sur les décisions en vigueur attendues, les messages non appliqués (MSG-007 à 010), le retard, le blocage et le travail obsolète ; S3 conforme (conflit DEC-004 / DEC-007, escalade à Marc, aucune date appliquée). Révision (MSG-008) et escalades visibles dans `logs/run-*.jsonl`. Les deux runs se rejouent en `SAMPLE_MODE` (test `tests/test_sample_run.py`).
- Non vérifié ou repli : Lightning 30B lisait trop mal les sources, d'où Ultra (D16). Écart S1 : MSG-001 lu comme une décision sur `export_formats` (voir STATUS). Le service H-MEM garde des décisions de runs de mise au point (à vider avant la démo).
- Reste / prochaine session : brique 7 (n° 18, 19), qui part de `RunResult.escalations` et `RunResult.facts` ; MCP (n° 24, 26, 27) ; brique 4 (n° 15) ; arbitrer l'écart MSG-001 et D17.

## 27/10 18:30 — Incrément 2 : H-MEM (n° 8), Orion (n° 9), World Model (n° 7) (session dédiée)
- Fait : client `atlas/hmem.py` (décision avec provenance et confiance, `explain` qui répond à « pourquoi le 10 novembre ? » par l'historique et le journal de confiance, retours helpful/not_helpful/wrong, rappel des enseignements), avec repli local en Python ; service `services/hmem/` autour de la référence H-MEM inchangée (résolution automatique des conflits jamais appelée) ; `scripts/load_org_memory.py` (enseignements d'Orion et Vega lus via Zetaris) ; service `services/world_model/` et adaptateur `atlas/world_model.py` qui implémente `StateStore` sans toucher à `atlas/state.py`, repli sur l'état JSON ; `scripts/engine_service.py` (lancement des deux services) et `scripts/engines_conformance.py` (les deux suites officielles).
- Tâches du plan : n° 8 faite ; n° 9 faite côté mémoire (le rappel reste à brancher dans la brique 5 ou le brief) ; n° 7 faite.
- Commits : 499df21, 0bd1728, 7aa6e21, puis le commit de cette entrée.
- Vérifié : 144 tests au vert avec les deux services lancés (intégration H-MEM 5/5, World Model 4/4 contre les vrais services) ; sans service, ces tests sont ignorés avec un message ; conformité H-MEM 13/13 et World Model 8/8 ; chargement d'Orion contre le service, sur repli et en `SAMPLE_MODE`.
- Non vérifié : le lanceur PowerShell (`.ps1`) ne peut pas s'exécuter sur ce poste (politique d'exécution) : lanceurs écrits en Python à la place ; `scripts/hmem-conformance.ps1` est gardé tel quel.
- Reste / prochaine session : brancher `WorldModelStateStore` et `HMem` dans l'orchestrateur (fichiers de l'incrément 1), recharger les enseignements à chaque run en `SAMPLE_MODE`, rappeler Orion dans la brique 5 ou le brief (S9).

## 27/10 17:58 — Incrément 0, tâches 4 et 5 (session dédiée)
- Fait : Nemotron imposé dans Nightshift par son identifiant ; appel LLM commun `atlas/structured.py` (schéma pydantic, une nouvelle tentative, timeout, routes Nightshift puis `MODEL_*` puis cache, trace JSONL avec le modèle lu dans le reçu de Nightshift). Horodatages de `docs/STATUS.md` corrigés (des heures fausses avaient été écrites pour les tâches 1 à 3).
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
- Fait : contrats entre composants dans `atlas/contracts.py` ; corpus Atlas synthétique, variantes S2 et S3, résultats attendus de S1 à S9.
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
- Fait : brouillon de l'équipe et propositions de la première revue ; `atlas/decisions.py`, `atlas/progress.py`, `atlas/alerts.py` (36 tests au vert) ; script de conformité H-MEM (13/13) ; connexions Zetaris, Nightshift et Nemotron vérifiées.
- Commits : d0cc125, 2e4d5d1, 1476314, 7a378de, a5b098e.

## 26/10 23:21–23:51 — Organisation du repo et cas Atlas
- Fait : structure du repo, documentation du cas Atlas, alignement du prompt jury, extension du produit (avancement, réunions, remontées au manager).
- Commits : 6483a71, e97b04c, 3a9ebdf, 8aad208.
