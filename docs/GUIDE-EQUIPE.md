# Guide équipe OSEF (FR)

État au 23/10 au soir : squelette complet qui tourne en mode échantillon (sans Zetaris ni Nightshift), testé hors ligne. Cas d'usage par défaut : bureau admin perso (à confirmer en équipe ; pour en changer, on remplace le dossier `domains/admin/`, pas le code).

## Ce qui marche déjà

- `python run.py run --input input_examples/example_1.json` : une décision complète, trace dans `logs/`.
- `python run.py demo-memory` : la démo en 3 sessions (escalade, correction, paiement qui cite la correction).
- `python run.py ablation` : tableau de ce que chaque brique apporte, sur 30 cas étiquetés.
- `python -m pytest -q` : 5 tests hors ligne.
- `cd hmem-service && npm run conformance` : 13/13 sur la conformité officielle H-MEM.

En mode échantillon, l'ablation donne 97 % pour le profil complet ; le seul cas raté (c30, une newsletter) demande du jugement, donc un modèle. Le profil `model_only` n'a pas de modèle hors ligne : ses chiffres n'ont de sens qu'avec Nightshift.

## Ce qu'il reste à faire, dans l'ordre

1. Brancher Nightshift (Console : URL et jeton dans `.env`) et lancer `python run.py run ...` sans `SAMPLE_MODE` : la trace doit montrer `model: nvidia/...`.
2. Brancher Zetaris : `docker compose up -d osef-db`, puis `scripts/zetaris/register_sources.sql` (voir `docs/ZETARIS-DATA.md`).
3. Relancer `python run.py ablation --repeats 3` avec Nightshift : c'est le tableau de la démo.
4. Relire et améliorer les prompts (`domains/admin/prompts/`) et les cas (`scripts/make_cases.py`).
5. Interface (optionnel, 10 points Produit) : une page qui appelle `POST /run` et `POST /learn`.
6. Vidéo (`docs/submission/demo-script.md`), deck (`deck-outline.md`), explication sponsors (`sponsor-tech.md`).

## Règles d'équipe

- Rien dans `.env` ne part sur GitHub (déjà dans `.gitignore`).
- Toute réponse de modèle réelle est enregistrée dans `data/llm_cache.jsonl` : la commiter permet au mode échantillon de rejouer la démo sans clé.
- Toute nouvelle brique arrive avec un profil dans `config/harness.yaml` pour pouvoir la mesurer.
