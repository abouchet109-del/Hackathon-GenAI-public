# Avancement

Mettre à jour à chaque étape terminée (date, ce qui marche, ce qui bloque, prochaine étape).

## État au 27 octobre 2026

### Fait
- Environnement : Zetaris installé en local ; provider Meterless Runtime codé et testé contre un faux runtime (`agent/llm.py`).
- Choix du use case : Atlas (voir [use-case-atlas.md](use-case-atlas.md)). Track 03.
- Organisation du repo et documentation de reprise. Repo GitHub public : https://github.com/abouchet109-del/Hackathon-GenAI-public (branche `main`).
- **27/10 — Connexions vérifiées** (`smoke_test.py`, `python -m agent.llm`) :
  - Zetaris : interface web et SQL via l'API REST, avec la clé de l'équipe ;
  - Nightshift : runtime en ligne sur le port 8088, réponse reçue via `meterless/auto` ;
  - Nemotron : répond via la route `MODEL_*`.
- **27/10 — Fondations déterministes**, 36 tests unitaires au vert (`python -m unittest -v`) :
  - `agent/decisions.py` : enregistrement d'une décision, décision en vigueur, détection des conflits ;
  - `agent/progress.py` : classement de l'avancement en quatre cas (ok, retard, obsolète, réunion nécessaire) ;
  - `agent/alerts.py` : boîtes d'alertes par membre, récupérées une seule fois.
- **27/10 — H-MEM** : implémentation de référence installée dans `external/meterless`, suite de conformité officielle au vert (13/13) via `scripts/hmem-conformance.ps1`.
- **27/10, 18:10 — H-MEM intégré (n° 8, porte 2)** : service `services/hmem/` autour de la référence inchangée, client `agent/hmem.py` (décisions avec provenance et confiance, « pourquoi le 10 novembre ? » par le journal de confiance, retours helpful/wrong, rappel des enseignements) ; résolution automatique des conflits jamais appelée ; repli local en Python (`SAMPLE_MODE` ou service absent). Test d'intégration au vert, conformité 13/13. Enseignements d'Orion et Vega chargés par `scripts/load_org_memory.py` (n° 9 côté mémoire).
- **27/10, 18:30 — World Model intégré (n° 7)** : service `services/world_model/`, adaptateur `agent/world_model.py` qui implémente `StateStore` (interface de `agent/state.py` inchangée) ; état relu depuis World Model identique à l'état JSON, réingestion sans événement, arêtes datées ; conformité 8/8 ; repli sur l'état JSON. Lancement : `python scripts/engine_service.py hmem|world_model` (README, section Engines).

### Bloquants
- [x] Nightshift installé et lancé (27/10).
- [x] Clé API Zetaris renseignée et vérifiée (27/10).
- [x] Nemotron imposé dans Nightshift et modèle réellement utilisé journalisé (27/10, 17:58) : voir l'incrément 0 ci-dessous.
- [ ] Données Atlas : déposer le kit dans `external/kit-demo-atlas/`, ou demander à Claude de générer le corpus dans `data/sample/`. Ajouter les tâches et objectifs de chaque membre et un projet passé (« Orion »).

### En cours
- Architecture : brouillon du 27/10 dans [architecture.md](architecture.md), notes manuscrites dans [architecture-notes/](architecture-notes/). Deuxième revue intégrée (27/10) : briques 4 et 5, orchestrateur, trois couches Zetaris / World Model / H-MEM (D12, D13). Restent : sources Zetaris définitives, flux de données, seuils et limites, tests, périmètre minimal.
- **27/10, 17:00 — Brique 7 (remontées et vue manager)** : document et notes de l'équipe intégrés dans [architecture.md](architecture.md) (propositions R, S, T ; D14 acquise). Trois modes (point périodique, exception, à la demande), règles R1 à R7 en code, interface par l'IA du manager via un skill et MCP. Cœur estimé à environ 3 h de construction : il faut réduire la brique 5 pour le faire tenir.
- À coder (repéré à la revue) : contradiction entre membres (S6) et blocages par tickets (règle 5) dans `agent/progress.py` ; signaux de coordination à la place des réunions du cas 4.

### Question ouverte apparue
- ~~Intégrer H-MEM à l'application~~ : tranché par D11 bis (service TypeScript autour de la référence), fait le 27/10 à 18:10.
- ~~À brancher par l'orchestrateur~~ : fait (incrément 1) : `WorldModelStateStore` pour l'état persistant, `load_org_lessons()` à chaque run. Reste le rappel d'Orion dans la brique 5 ou le brief, pour que S9 passe de bout en bout.
- **Écart S1 (incrément 1)** : Nemotron Ultra lit MSG-001 (Léa, 15/09, « avec l'export CSV ») comme une décision sur `csv-export/export_formats` = csv, qui entre en vigueur ; les attendus n'en prévoient pas. Conséquence pour S6 (incrément 6) : le travail de Sarah (csv,xlsx) sort « obsolète » au lieu d'une contradiction entre membres. À trancher par l'équipe : accepter la lecture, ou exiger qu'une décision venue d'un message soit inscrite au registre.
- **H-MEM à vider avant la démo** : le service (`.state/hmem/`) garde des décisions écrites par des runs de mise au point avant le correctif de chronologie (DEC-MSG-001-1, DEC-MSG-004-1) ; `explain atlas-launch launch_date` les montre. Arrêter le service et repartir d'un dossier vide (décision de l'équipe).
- **D17 à valider** : le registre fait foi par lui-même (DEC-003 de Léa, alors que la table des rôles ne lui donne pas `csv-export/owner`).

### Prochaines étapes
Détail, estimations et méthode : [PLAN.md](PLAN.md) (27/10, 17:20). Gel du code à 22:30, soumission vers 00:15 (heure de Paris).
1. **Fait — incrément 0** : contrats entre composants, corpus Atlas et résultats attendus, enregistrement dans Zetaris, client Zetaris, Nemotron imposé et journalisé, appel LLM commun.
   - **27/10, 17:31 — Contrats écrits** ([agent/contracts.py](../agent/contracts.py), testés) : information candidate, proposition de mise à jour, résultat du contrôleur, affirmation et passage périmé d'un livrable, remontée de la brique 7. Le rapport d'avancement reste `Report` ([agent/progress.py](../agent/progress.py)), complété par les blocages ; `Task` gagne une date de début, et un `Milestone` lit sa date dans la décision en vigueur. Relus et validés par l'équipe.
   - **27/10, 17:40 — Corpus Atlas synthétique** dans `data/sample/` (9 sources : documents, messages, tickets, décisions, tâches, jalons, rapports, rôles, projets passés), variantes S2 et S3 dans `data/scenarios/`, attendus S1 à S9 dans `data/expected/` (modèles dans [agent/sources.py](../agent/sources.py) et `evaluation/expected.py`). Tests : chaque fichier se charge, les références se résolvent, les pièges sont présents ; sur ce corpus, le code existant donne le 10 novembre, le SSO en v2, la tâche CSV en retard et le travail de Sarah obsolète. Relu par l'équipe. Points ouverts : horizon d'urgence H (10 jours ouvrés supposés pour que R1 soit P1 dans la démo, 5 dans l'architecture) ; la réunion attendue inclut Sarah par transitivité des dépendances, ce que `progress.py` ne fait pas encore (il donne Hugo et Inès).
   - **27/10, 17:49 — Zetaris de bout en bout** (environ 30 min, sans repli) : base `ATLAS`, 9 tables REST sur jsDelivr épinglé, enregistrées par `scripts/register_zetaris.py` ; les 9 sources relues en SQL sont identiques au corpus. Client `agent/zetaris.py` (timeout, cache commité pour `SAMPLE_MODE`, repli sur le cache en cas de panne), testé avec un faux serveur. Détail : [architecture.md](architecture.md), section 5.
   - **27/10, 17:58 — Nemotron imposé et appel LLM commun.** Nightshift liste des identifiants `nvidia/nemotron-*` à côté des modes `meterless/*` : on les impose par le champ `model`. Vérifié : `nvidia/nemotron-3.5-lightning-30b-a3b` (défaut, environ 2 s) et `nvidia/nemotron-3-ultra-550b-a55b` répondent ; `nemotron-3-super-120b` rend une erreur NVIDIA 404 ; les deux Llama-Nemotron sont désactivés dans les sources de calcul de Nightshift. La réponse porte un reçu (`meterless.routed_model`, `winning_route.provider = nvidia`, `receipt_id`), d'où le modèle tracé. `agent/structured.py` : sortie JSON validée par un schéma pydantic, une nouvelle tentative avec l'erreur, puis `LLMOutputError` ; timeout de 90 s ; routes Nightshift puis `MODEL_*`, puis cache (`data/cache/llm/`, seul utilisé en `SAMPLE_MODE`) ; trace JSONL dans `logs/llm-trace.jsonl`. Testé contre un faux runtime (8 tests) et par un appel réel. À noter : la route `MODEL_*` du `.env` pointe aussi sur Nightshift (`meterless/auto`), donc le repli n'est pas indépendant de Nightshift ; et le prompt de l'extracteur devra donner la date du message (le modèle a répondu 2024 pour « 12 novembre »).
   - **Incrément 0 terminé à 17:58**, en avance sur le point de contrôle de 19:45.
2. À trancher par l'équipe après l'incrément 0 : D11, sort de World Model, fusion de l'analyste, brique 5 réduite, choix des incréments (PLAN, sections 3 et 4).
3. **Fait — incrément 1 (bout en bout), 27/10, 19:25** : état versionné, extracteur, agent de mise à jour, contrôleur (une révision, puis escalade), écriture avec alertes et H-MEM, agent manager, orchestrateur, `POST /run`. Runs réels S1 (47 appels, 6 min 30) et S3 (escalade à Marc) sur Nemotron 3 Ultra, rejoués en `SAMPLE_MODE` par les tests ; 167 tests au vert. Avec l'incrément 2, le projet est soumissible.
4. Incréments suivants selon le temps : remontées (brique 7), MCP et skill manager, correction du brief.
5. README final, `.env.example`, `SAMPLE_MODE`, test depuis un clone propre.
6. Vidéo, deck, explication des sponsors, soumission.

### Avant la soumission
- [ ] Le repo est public depuis le 26/10 : décider si l'on garde `docs/strategie/` et `docs/hackathon/`.
- [ ] Scanner les secrets (voir la checklist de disqualification, section 11).
