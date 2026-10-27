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
