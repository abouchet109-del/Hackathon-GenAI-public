# Avancement

Mettre à jour à chaque étape terminée (date, ce qui marche, ce qui bloque, prochaine étape).

## État au 26 octobre 2026

### Fait
- Environnement : Zetaris installé en local (test de fumée passé le 23/10) ; provider Meterless Runtime codé et testé contre un faux runtime (`agent/llm.py`).
- Choix du use case : Atlas (voir [use-case-atlas.md](use-case-atlas.md)).
- Organisation du repo et documentation de reprise.
- Repo GitHub public : https://github.com/abouchet109-del/Hackathon-GenAI-public (branche `main`).

### Bloquants (à faire par l'équipe, Claude ne peut pas créer de comptes ni saisir de clés)
- [ ] Installer et lancer Meterless Nightshift (le port 8088 ne répondait pas le 26/10).
- [ ] Ajouter la clé NVIDIA (build.nvidia.com) dans l'onglet Providers de Nightshift.
- [ ] Créer la clé API Zetaris dans l'interface et la mettre dans `.env`.
- [ ] Données Atlas : déposer le kit dans `external/kit-demo-atlas/`, ou demander à Claude de générer le corpus dans `data/sample/`. Sans elles, Zetaris n'a rien à servir.

### Prochaines étapes
1. Architecture : remplir [architecture.md](architecture.md), puis revue avec Claude.
2. Tests bloquants (deux heures au plus) : une requête Zetaris sur les sources Atlas, un appel Nemotron via Nightshift avec le modèle journalisé, l'implémentation de référence du World Model et sa suite de conformité, un client MCP connecté.
3. Parcours complet minimal sur le scénario S1, avec traces.
4. Scénarios S2 à S6 et les 14 cas de test.
5. Second client MCP, détection des travaux contradictoires, vue manager.
6. README final, `.env.example`, `SAMPLE_MODE`, test depuis un clone propre.
7. Vidéo, deck, explication des sponsors, soumission.

### Avant la soumission
- [ ] Le repo est public depuis le 26/10 : décider si l'on garde `docs/strategie/` et `docs/hackathon/`.
- [ ] Scanner les secrets (voir la checklist de disqualification, section 11).
