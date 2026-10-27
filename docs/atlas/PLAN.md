# Plan de construction

Établi le 27/10/2026 à 17:20 (heure de Paris), à partir de [architecture.md](architecture.md) et de la grille du jury ([strategie/prompt-jury.md](strategie/prompt-jury.md)). **Les décisions de la section 3 et le choix des incréments ne sont pas encore tranchés** : l'équipe décidera après les données, Zetaris et le modèle (incrément 0).

---

## 1. Le temps disponible

| Créneau (Paris) | Quoi |
|---|---|
| 17:30 → 22:30 | Développement, environ 5 h |
| 22:30 | **Gel du code** : on garde le dernier incrément qui tourne et qui est poussé |
| 22:30 → 23:15 | README final, `.env.example`, test depuis un clone propre, vérification de `SAMPLE_MODE` |
| 23:15 → 00:00 | Enregistrement et mise en ligne de la vidéo |
| 00:00 → 00:15 | Formulaire, recherche de secrets, déclaration du travail préexistant, **soumission** |
| 00:45 | Clôture officielle (27/10, 23:45 UTC). Les 30 minutes de marge servent en cas d'imprévu ; soumettre tôt départage aussi les égalités |

Le deck peut être préparé en parallèle du développement.

---

## 2. Inventaire complet, avec estimations probable et maximale

Hypothèse : Claude code, l'équipe relit. L'estimation **maximale** est celle d'une intégration qui se passe mal ; c'est la limite de temps de chaque tâche (section 6). « Porte » renvoie aux portes éliminatoires du prompt jury.

| # | Élément | Probable | Max | Critère servi | Fait quand… |
|---|---|---|---|---|---|
| **Données et Zetaris** ||||||
| 1 | Corpus Atlas synthétique : documents, messages, tickets, registre des décisions, tâches (début, échéance, dépendances, responsable), rapports d'avancement, table des rôles, projet passé Orion ; **résultats attendus dans des fichiers séparés**, jamais lus par les agents | 30 min | 45 min | Toutes | Chaque fichier se charge dans les modèles de `atlas/` ; les pièges du cas d'usage sont présents ; l'équipe a relu |
| 2 | Enregistrement des sources dans Zetaris : table REST sur une URL (jsDelivr épinglé sur un commit) ; repli : API locale via `host.docker.internal`, ou fichier sur S3 | 30 min | **1 h 30** | Sponsor, porte 2 | Une requête SQL sur chaque source rend les enregistrements attendus ; le script d'enregistrement est dans `scripts/` |
| 3 | Client Zetaris en Python : requêtes SQL, timeout, repli sur le cache de `SAMPLE_MODE` | 20 min | 30 min | Technical | Test unitaire avec un faux serveur ; requête réelle vérifiée ; cache écrit et relu |
| **Modèle** ||||||
| 4 | Imposer Nemotron dans Nightshift et journaliser le modèle réellement utilisé | 15 min | 30 min | Sponsor, prix NVIDIA | Le modèle est lu dans la réponse et écrit dans la trace ; sinon, la route `MODEL_*` qui marche est documentée comme repli |
| 5 | Appel LLM commun : sortie JSON validée par un schéma, une nouvelle tentative au plus, timeout, trace | 20 min | 30 min | Technical | Test contre le faux runtime ; une sortie invalide déclenche une seule nouvelle tentative, puis une erreur claire |
| **État et mémoire** ||||||
| 6 | État du projet en JSON : seul écrivain, versions, ingestion sans doublon | 30 min | 45 min | Technical | Tests : une nouvelle version par écriture ; réingérer la même source ne change rien (S5) |
| 7 | World Model réellement intégré | 1 h 30 | 3 h | Sponsor (déjà couvert par H-MEM) | Suite de conformité au vert et état lu depuis World Model |
| 8 | H-MEM : petit serveur TypeScript autour de l'implémentation de référence, client Python, test | 45 min | 1 h 30 | **Porte 2** | Une décision écrite avec sa provenance ; le journal de confiance répond à « pourquoi le 10 novembre ? » ; test d'intégration au vert |
| 9 | Mémoire de l'organisation : l'enseignement d'Orion rappelé (S9) | 20 min | 40 min | Track 03 | S9 passe |
| **Briques** ||||||
| 10 | Brique 1 : analyste (extraction et qualification fusionnées) | 30 min | 1 h | Porte 3 | Sur le corpus, les informations attendues sont retrouvées |
| 11 | Brique 1 : agent de mise à jour séparé de l'extracteur | 20 min | 45 min | Peu de chose | — |
| 12 | Brique 1 : contrôleur (code, puis LLM), avec une révision au plus puis escalade | 30 min | 1 h | **Porte 3**, Technical | La boucle de révision et l'escalade sont visibles dans les traces |
| 13 | Écriture de l'état et notification (`atlas/alerts.py` existe déjà) | 10 min | 20 min | Technical | Une décision validée dépose une alerte chez les membres concernés |
| 14 | Brique 2 : cas 5 (contradiction entre membres, S6), tickets bloquants, date de début des tâches | 30 min | 45 min | Demo | S6 passe |
| 15 | Brique 4 complète : affirmations, comparaison en code, rédacteur, validateur | 45 min | 1 h 30 | Impact (« un vrai travail »), Demo | Diff du brief : chaque changement cite sa source, rien d'autre n'est modifié |
| 16 | Brique 5 complète : score, analyste outillé, verdict, calibration | 2 h | 3 h 15 | Innovation | — |
| 17 | Brique 5 réduite : signaux déjà codés, recommandation rédigée, verdict enregistré dans H-MEM | 20 min | 45 min | Track 03 | S7 donne une réunion recommandée avec participants, raison et ordre du jour |
| 18 | Brique 7, cœur : règles R1, R2 et R4, routage, dédoublonnage, boîte de remontées, ligne d'en-tête | 1 h | 1 h 45 | Track 03, Demo, UX | Tests S1, S3, S7, S8 et dédoublonnage de la brique 7 au vert |
| 19 | Brique 7 : point périodique et contrôle du rapport | 30 min | 50 min | UX, Technical | Le point est produit même sans remontée ; un rapport qui omet une P1 est rejeté |
| 20 | Brique 7 : R5, R7, R3, R6 | 45 min | 1 h 30 | Peu de chose | — |
| 21 | Agent manager | 20 min | 45 min | Impact, UX | Rapport structuré qui répond à la requête de la section 1 de l'architecture |
| **Exécution** ||||||
| 22 | Orchestrateur, traces JSONL, limites, `SAMPLE_MODE` | 40 min | 1 h | **Porte 4**, Technical | Un run complet tourne en `SAMPLE_MODE` sans Zetaris ni Nightshift |
| 23 | `POST /run` | 15 min | 30 min | **Porte 4** | Entrée et sortie structurées, documentées dans le README |
| 24 | Serveur MCP, trois outils : `report_progress`, `get_alerts`, `get_manager_brief` | 40 min | 1 h | Impact, Innovation | Les trois outils répondent depuis un vrai client |
| 25 | Outils MCP supplémentaires : `ask_project`, `mark_escalation`, `get_project_context` | 15 min | 30 min | UX | — |
| 26 | Skills membre et manager | 15 min | 30 min | UX | Le skill manager présente le point, P1 en tête |
| 27 | Configuration et test dans de vrais clients : Claude Desktop pour le manager, Claude Code ou Cursor pour un membre | 20 min | 45 min | Demo | S2 : le second client récupère la nouvelle date et ses sources |
| 28 | Page HTML pour le manager | 30 min | 45 min | UX | — |
| 29 | Script de scénarios qui compare la sortie aux résultats attendus | 30 min | 1 h | Technical | Le script affiche le résultat de chaque scénario |
| **Soumission** ||||||
| 30 | README final, `.env.example`, test depuis un clone propre | 30 min | 45 min | Porte 4 | Un clone neuf s'installe et tourne en suivant le README |
| 31 | Vidéo | 1 h | 1 h 30 | Demo | En ligne, durée conforme au règlement |
| 32 | Deck | 30 min | 45 min | Impact | — |
| 33 | Formulaire, recherche de secrets, déclaration du travail préexistant | 15 min | 20 min | Portes 1 et 7 | Soumis |

**Totaux** : environ **16 h** de développement en probable, **29 h** en maximal, plus 2 h 15 à 3 h 20 pour la soumission. Il reste environ 5 h de développement : l'architecture complète représente plus de trois fois le temps disponible.

---

## 3. Décisions proposées, à trancher par l'équipe

| Proposition | Gain (max) | Effet sur le jury |
|---|---|---|
| D11 : H-MEM via un petit serveur TypeScript autour de la référence (n° 8), plutôt qu'un portage Python | ~1 h 30 | Aucun : la conformité officielle reste au vert |
| World Model remplacé par l'état JSON déjà prévu en repli (n° 6 au lieu du n° 7) ; World Model passe en feuille de route | 1 h 30 à 3 h | Faible : H-MEM suffit à l'obligation d'engine |
| Extracteur et agent de mise à jour fusionnés en un analyste pour le MVP (n° 10 sans le n° 11) | ~45 min | Aucun : la porte 3 demande deux agents et une boucle, le contrôleur la fournit |
| Brique 5 réduite (n° 17 au lieu du n° 16) ; littérature et calibration sur le deck | ~2 h 30 | Faible sur Innovation si le deck l'explique |

---

## 4. Incréments proposés

Chaque incrément laisse une démo qui tourne et peut être poussée. À 22:30, on gèle le code au dernier incrément terminé.

| Incrément | Contenu (n°) | Probable | Max | Ce que ça débloque | Note estimée si on s'arrête là |
|---|---|---|---|---|---|
| **0. Contrats, données, Zetaris, modèle** | Schémas JSON entre composants (15 à 30 min), 1, 2, 3, 4, 5 | 2 h 10 | 4 h 15 | Plus rien n'est hypothétique côté infrastructure | — |
| **1. Bout en bout** | 6, 10, 12, 13, 21, 22, 23 | 2 h 55 | 5 h 20 | Portes 3 et 4 ; S1 et S3 | Pas soumissible sans H-MEM |
| **2. H-MEM** | 8 | 45 min | 1 h 30 | **Porte 2** : le projet devient soumissible | ~60–68 / 100 |
| **3. Remontées** | 18, 19 | 1 h 30 | 2 h 35 | Track 03, scène « une P1 apparaît » ; S7, S8 | ~68–74 |
| **4. Interface multi-IA** | 24, 26 (manager), 27 | 1 h 15 | 2 h 15 | La promesse du produit et la réponse à « pourquoi pas Jira ? » ; S2 | ~74–80 |
| **5. Livrables** | 15 | 45 min | 1 h 30 | Le diff du brief avec ses sources | ~77–83 |
| **6. Bonus** | 14, 17, 9, 28, 29 | 2 h | 3 h 30 | S6, S7 complet, S9, visuel, scénarios automatisés | ~80–86 |
| Feuille de route | 7, 11, 16, 20, 25, mail et Slack | — | — | Slide « future enhancements » | — |

Les notes sont des estimations, à prendre comme un ordre de grandeur.

Ordre : les portes d'abord (1 et 2), car sans elles la note s'effondre. Puis la brique 7 : du code testable, le cœur du track 03, la meilleure scène de démo. Puis MCP : sans lui, le manager n'a pas d'interface et l'argument multi-IA reste une affirmation. La brique 4 en dernier car plus chère ; elle peut passer avant l'incrément 4 si l'équipe juge que la correction du brief est le moment fort de la vidéo.

**Réaliste** : les incréments 0 et 1 font à eux seuls environ 5 h en probable, soit tout le temps de développement. **Sans parallélisme, on atteint à peine le projet soumissible** (incréments 0 à 2). Avec deux ou trois sessions en parallèle après l'incrément 0 (section 6), on peut viser les incréments 0 à 4. Conséquence : **H-MEM (n° 8) doit être construit en parallèle de l'incrément 1**, pas après, car c'est une porte éliminatoire.

### Risques qui peuvent tout décaler
- Enregistrement dans Zetaris (n° 2) : jamais testé. À traiter en premier, avec un repli prêt.
- Nemotron imposé dans Nightshift (n° 4) : si c'est impossible, documenter la route `MODEL_*` qui fonctionne.
- Clients MCP réels (n° 27) : la configuration de Claude Desktop peut demander un redémarrage et des essais.

---

## 5. Incrément 0 en détail (en cours)

### 5.1 Contrats (avant tout code)
Les schémas des objets échangés : information candidate, proposition de mise à jour, résultat du contrôleur, remontée, rapport d'avancement, affirmation d'un livrable. On part des modèles existants (`atlas/decisions.py`, `atlas/progress.py`, `atlas/alerts.py`) et du format de remontée de la brique 7. Tant qu'ils ne sont pas écrits, deux sessions ne peuvent pas coder en parallèle.

### 5.2 Données (n° 1)
- Un fichier JSON par source, au format attendu par Zetaris (un objet qui contient un tableau : `{"records": [...]}`), dans `data/sample/`.
- Identifiants stables et lisibles (`DEC-001`, `TSK-004`, `TCK-QA-012`), pour que les preuves se lisent dans les traces et la vidéo.
- Les pièges du cas d'usage, chacun traçable à un scénario : ancien brief au 3 novembre, registre au 10 novembre avec SSO en v2, message qui recopie l'ancienne date, ticket QA CSV bloquant, brouillon commercial « tout est prêt », une information d'un autre projet (S4), un doublon (S5), deux membres en contradiction (S6), une tâche bloquante en retard (S7), Orion (S9).
- Les résultats attendus dans `data/expected/`, jamais lus par les agents.
- Les données sont déclarées synthétiques dans chaque fichier et dans le README.
- Vérification : chaque fichier se charge dans les modèles Python ; l'équipe relit en 5 minutes (un humain repère vite ce qui sonne faux).

### 5.3 Zetaris (n° 2 et 3)
- Suivre `D:\zetaris-platform\getting-started\AGENTS.md` : lecture seule d'abord, demander avant toute création.
- **Une seule source de bout en bout d'abord** (la plus petite), avant les autres : publier, enregistrer, interroger en SQL. On ne généralise qu'une fois ce chemin vérifié.
- URL jsDelivr épinglée sur un commit (pas sur `main`, qui est mis en cache).
- Script d'enregistrement idempotent dans `scripts/`, et une requête de vérification par source.
- Limite : 1 h 30. Au-delà, repli (API locale via `host.docker.internal`, ou S3) et on le documente.
- Noter dans [architecture.md](architecture.md), section 5, les sources et les requêtes réellement utilisées.

### 5.4 Modèle (n° 4 et 5)
- Chercher dans Nightshift (onglet Providers, contrat provider v4) comment imposer un modèle ; tester une requête et lire le modèle dans la réponse.
- Toujours écrire le modèle réellement utilisé dans la trace, pas celui qu'on a demandé.
- Si Nemotron ne peut pas être imposé, documenter la route `MODEL_*` (déjà vérifiée par `smoke_test.py`) et le dire dans le README.
- L'appel commun valide la sortie JSON contre un schéma pydantic, retente une fois, puis échoue clairement.

---

## 6. Méthode de travail

### Principes
1. **Le risque d'abord.** Ce qui n'a jamais été testé (Zetaris par URL, Nemotron) passe avant ce qui est sûr (du code pur).
2. **Les contrats avant le code.** Les schémas entre composants sont écrits et relus avant de coder les composants.
3. **Une tâche = un critère « fait » vérifiable** (colonne « Fait quand… » de la section 2). Pas de tâche « à peu près finie ».
4. **Une limite de temps par tâche** : l'estimation maximale. Au-delà, on prend le repli prévu ou on coupe, et on le note dans `docs/STATUS.md`.
5. **Fin de chaque tâche** : tests au vert, commit, push, `docs/STATUS.md` à jour. Le repo est la mémoire du projet, pas la conversation.
6. **`SAMPLE_MODE` et traces dès le premier composant**, pas à la fin.
7. **Rien de codé en dur** : chaque résultat est calculé à partir des données ; les attendus servent seulement à évaluer.
8. **Vérifié ou supposé** : la documentation dit toujours lequel des deux.
9. **Relecture humaine courte et ciblée** : relire le diff des schémas, des règles et des prompts ; inutile de relire chaque ligne de code testée.

### Une conversation ou plusieurs ?
- **Une nouvelle conversation par incrément** (ou par grosse tâche), une fois l'incrément précédent poussé et `docs/STATUS.md` à jour. Une conversation trop longue est résumée automatiquement et perd des détails ; une conversation neuve repart de `CLAUDE.md`, `docs/STATUS.md` et de ce plan, qui sont à jour.
- **Pas une conversation par petit sous-élément** : chacune repart de zéro et relit le contexte. Le bon grain est « un incrément » ou « une tâche de la section 2 d'au moins 30 minutes ».
- **Message de départ type** : « Lis `CLAUDE.md`, `docs/STATUS.md` et `docs/atlas/PLAN.md`. On fait l'incrément N, tâches X à Y. Planifie, puis construis et teste tâche par tâche ; commit et push à chaque tâche au vert. »
- **En parallèle** : seulement après l'incrément 0 (contrats figés), et seulement pour des tâches qui touchent des fichiers différents, chacune dans sa propre session et son propre worktree. Bons candidats : état JSON (n° 6), règles de la brique 7 (n° 18), serveur H-MEM (n° 8). Une session principale fait l'intégration et fusionne.
- **Une conversation « architecte »** peut rester ouverte pour les décisions et les arbitrages, sans y coder.

### Fin de session
Chaque session met à jour `docs/JOURNAL.md`, la section 7 ci-dessous, `docs/STATUS.md` et le README, pousse, puis fait le bilan à l'humain : ce qui est fini, où en est le plan, ce qui reste, quelle session lancer ensuite (section 8 de `CLAUDE.md`).

### Points de contrôle
| Heure | Question |
|---|---|
| 19:45 | L'incrément 0 est-il fini ? Sinon, on prend les replis (Zetaris, Nemotron) et on passe à la suite |
| 22:00 | Les incréments 1 et 2 sont-ils finis (projet soumissible) ? Sinon, tout le reste est coupé |
| 22:30 | Gel du code, quoi qu'il arrive |

---

## 7. Suivi

Mis à jour par chaque session à chaque tâche terminée (heure de Paris). États : à faire, en cours, faite, repli, coupée. Le récit des sessions est dans [JOURNAL.md](JOURNAL.md).

| Incrément | Tâche (n° de la section 2) | État | Mis à jour | Note |
|---|---|---|---|---|
| 0 | Contrats entre composants | Faite | 27/10 17:31 | `atlas/contracts.py` (76d3b58) |
| 0 | 1. Corpus Atlas et résultats attendus | Faite | 27/10 17:40 | Variantes S2 et S3, attendus S1 à S9 (8501863) ; relu par l'équipe |
| 0 | 2. Enregistrement dans Zetaris | Faite | 27/10 17:49 | Sources Atlas enregistrées, script `scripts/register_zetaris.py` (167c618) |
| 0 | 3. Client Zetaris | Faite | 27/10 17:49 | `atlas/zetaris.py`, cache dans `data/cache/zetaris/` (167c618) ; 60 tests au vert à 17:58 |
| 0 | 4. Nemotron imposé et journalisé | Faite | 27/10 17:58 | Identifiant `nvidia/nemotron-3.5-lightning-30b-a3b` dans Nightshift ; modèle lu dans le reçu `meterless.routed_model` |
| 0 | 5. Appel LLM commun | Faite | 27/10 17:58 | `atlas/structured.py`, testé contre un faux runtime et par un appel réel |
| 1 | 6. État du projet | Faite | 27/10 18:15 | `atlas/state.py`, interface `StateStore` (463e2f2) ; World Model branché derrière |
| 1 | 10. Extracteur | Faite | 27/10 19:15 | `atlas/extractor.py`, prompt versionné (4a71d20, eb8199f) ; Nemotron 3 Ultra (D16) |
| 1 | 11. Agent de mise à jour | Faite | 27/10 19:15 | `atlas/updater.py`, séparé de l'extracteur (D15) (4a71d20, eb8199f) |
| 1 | 12. Contrôleur | Faite | 27/10 19:15 | `atlas/controller.py` : contrôles en code, puis preuves par le LLM ; une révision, puis escalade, visibles dans les traces des runs réels (MSG-008 révisé ; DEC-007 et MSG-004 escaladés à Marc en S3) (6c6f965, eb8199f) |
| 1 | 13. Écriture de l'état et notification | Faite | 27/10 18:35 | `atlas/writer.py` : seul écrivain, alertes, décisions validées dans H-MEM (f21fc0b) |
| 1 | 21. Agent manager | Faite | 27/10 18:45 | `atlas/manager.py` : verdicts en code, rapport LLM contrôlé, une révision (5aaf2a9) |
| 1 | 22. Orchestrateur | Faite | 27/10 19:20 | `atlas/orchestrator.py` : Zetaris, limites, replis, `SAMPLE_MODE`, traces JSONL ; runs réels S1 et S3 comparés aux attendus (abfaa7d) |
| 1 | 23. `POST /run` | Faite | 27/10 19:20 | `atlas/api.py`, documenté dans le README (abfaa7d). Incrément 1 terminé à 19:25, environ 1 h 20, sous le probable |
| 2 | 8. H-MEM | Faite | 27/10 18:10 | Service `services/hmem/` autour de la référence inchangée, client `atlas/hmem.py` avec repli local ; décision avec provenance, « pourquoi le 10 novembre ? » par le journal de confiance, test d'intégration au vert, conformité 13/13 (499df21, 0bd1728) ; environ 1 h, sous le maximum |
| 2 | 9. Mémoire de l'organisation (Orion) | Faite (côté mémoire) | 27/10 18:10 | `scripts/load_org_memory.py` ; Orion-1 rappelé en premier depuis le vrai engine ; le rappel dans la brique 5 ou le brief reste à brancher pour que S9 passe de bout en bout |
| 2 | 7. World Model | Faite | 27/10 18:30 | Service `services/world_model/`, adaptateur `atlas/world_model.py` (interface de `atlas/state.py` inchangée), repli sur l'état JSON ; conformité 8/8, état relu depuis World Model identique à l'état JSON (7aa6e21) ; environ 25 min, sous le maximum. L'orchestrateur choisit encore le store à utiliser |
| 3 | 18, 19 | À faire | — | — |
| 4 | 24, 26, 27 | À faire | — | — |
| 5 | 15 | À faire | — | — |
| 6 | 14, 17, 9, 28, 29 | À faire | — | — |
| Soumission | 30 à 33 | À faire | — | — |
