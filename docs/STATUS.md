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

### Bloquants
- [x] Nightshift installé et lancé (27/10).
- [x] Clé API Zetaris renseignée et vérifiée (27/10).
- [ ] Clé NVIDIA dans l'onglet Providers de Nightshift : à confirmer. Nightshift n'expose que des modes de routage (`meterless/auto`, `fast`, `deep`…), pas d'identifiant Nemotron : il faut vérifier comment imposer Nemotron et journaliser le modèle réellement utilisé (prix NVIDIA).
- [ ] Données Atlas : déposer le kit dans `external/kit-demo-atlas/`, ou demander à Claude de générer le corpus dans `data/sample/`. Ajouter les tâches et objectifs de chaque membre et un projet passé (« Orion »).

### En cours
- Architecture : brouillon du 27/10 dans [architecture.md](architecture.md), notes manuscrites dans [architecture-notes/](architecture-notes/). Deuxième revue intégrée (27/10) : briques 4 et 5, orchestrateur, trois couches Zetaris / World Model / H-MEM (D12, D13). Restent : sources Zetaris définitives, flux de données, seuils et limites, tests, périmètre minimal.
- **27/10, 17:00 — Brique 7 (remontées et vue manager)** : document et notes de l'équipe intégrés dans [architecture.md](architecture.md) (propositions R, S, T ; D14 acquise). Trois modes (point périodique, exception, à la demande), règles R1 à R7 en code, interface par l'IA du manager via un skill et MCP. Cœur estimé à environ 3 h de construction : il faut réduire la brique 5 pour le faire tenir.
- À coder (repéré à la revue) : contradiction entre membres (S6) et blocages par tickets (règle 5) dans `agent/progress.py` ; signaux de coordination à la place des réunions du cas 4.

### Question ouverte apparue
- **Intégrer H-MEM à l'application** (voir [DECISIONS.md](DECISIONS.md), D11). H-MEM est une spécification avec une implémentation de référence en TypeScript, alors que l'application est en Python.

### Prochaines étapes
Détail, estimations et méthode : [PLAN.md](PLAN.md) (27/10, 17:20). Gel du code à 22:30, soumission vers 00:15 (heure de Paris).
1. **En cours — incrément 0** : contrats entre composants, corpus Atlas et résultats attendus, enregistrement dans Zetaris, client Zetaris, Nemotron imposé et journalisé, appel LLM commun.
   - **27/10, 17:45 — Contrats écrits** ([agent/contracts.py](../agent/contracts.py), testés) : information candidate, proposition de mise à jour, résultat du contrôleur, affirmation et passage périmé d'un livrable, remontée de la brique 7. Le rapport d'avancement reste `Report` ([agent/progress.py](../agent/progress.py)), complété par les blocages ; `Task` gagne une date de début, et un `Milestone` lit sa date dans la décision en vigueur. **En attente de relecture par l'équipe.**
2. À trancher par l'équipe après l'incrément 0 : D11, sort de World Model, fusion de l'analyste, brique 5 réduite, choix des incréments (PLAN, sections 3 et 4).
3. Incréments 1 (bout en bout) et 2 (H-MEM, en parallèle) : le projet devient soumissible.
4. Incréments suivants selon le temps : remontées (brique 7), MCP et skill manager, correction du brief.
5. README final, `.env.example`, `SAMPLE_MODE`, test depuis un clone propre.
6. Vidéo, deck, explication des sponsors, soumission.

### Avant la soumission
- [ ] Le repo est public depuis le 26/10 : décider si l'on garde `docs/strategie/` et `docs/hackathon/`.
- [ ] Scanner les secrets (voir la checklist de disqualification, section 11).
