# Contexte du projet

Document de reprise : à lire en premier par toute personne (ou toute session Claude) qui rejoint le projet. Mis à jour le 26 octobre 2026.

## Le hackathon
- **Open Agent Hackathon 2026**, organisé par GenAI Works. Page : https://hackathon.genai.works/event/open-agent-hackathon-2026
- **Clôture des soumissions : 27 octobre 2026, 23:45 UTC** (28 octobre, 00:45 à Paris). Délai ferme. Objectif interne : soumettre le 27 octobre vers 18:00 UTC.
- Documents officiels copiés dans [hackathon/](hackathon/). En cas de désaccord, les règles officielles priment.
- **Obligations techniques** : Zetaris comme couche de données ; au moins un engine Meterless (H-MEM, Markovian, World Model ou Scout Intent) dans une fonctionnalité qui marche, avec un test qui passe ; Meterless Nightshift comme fournisseur IA principal ; NVIDIA là où il apporte quelque chose (prix séparé pour le meilleur usage de Nemotron).
- **À rendre** : vidéo de 1 à 4 minutes, deck, repo GitHub public avec README, explication de l'usage des sponsors.
- **Notation** : Impact 30, Technical 20, Innovation 15, Demo 15, Product & UX 10, Sponsor Tech 10. Jury : CTO de Zetaris, responsables d'ingénierie de GenAI Works et de SpaceXAI.

## L'idée de l'équipe
Chacun a déjà son IA (ChatGPT, Claude…) avec sa mémoire et son contexte ; les entreprises imposent un fournisseur unique et le contexte reste enfermé chez lui. Notre réponse : une mémoire projet qui appartient à l'entreprise, accessible depuis n'importe quelle IA via MCP.

**Ce qui nous différencie** (le partage de mémoire multi-IA existe déjà chez Mem0 / OpenMemory ou Supermemory) :
- la mémoire est autonome : elle suit l'avancement de chaque membre et garde l'équipe coordonnée ;
- elle empêche que deux personnes fassent deux choses contradictoires ;
- elle distingue ce qui fait foi (décision approuvée) de ce qui ne fait pas foi ;
- elle agit : elle corrige un livrable périmé, avec ses preuves ;
- une vue manager permet de suivre le projet de loin.

## Le cas d'usage retenu
**Atlas** : une équipe produit prépare le lancement d'un portail client fictif ; ses sources se contredisent (date, périmètre, état de préparation) et ses membres travaillent avec des IA différentes. Détail : [use-case-atlas.md](use-case-atlas.md). Track visé : 01 — Solving Fragmented Intelligence.

Historique du choix : une première évaluation recommandait d'autres use cases (allégations alimentaires, puis vulnérabilités CISA KEV, voir [strategie/evaluation-use-case.md](strategie/evaluation-use-case.md)). Atlas a été retenu le 26 octobre parce qu'il démontre directement le produit que l'équipe veut construire.

## L'environnement
- Projet : `D:\open-agent-hack` (Python, venv `.venv`). Provider Meterless Runtime déjà codé et testé contre un faux runtime : `agent/llm.py`, `tests/test_meterless.py`.
- Zetaris : installé en local dans `D:\zetaris-platform` (Docker via WSL). Repo d'onboarding avec les sources testées et les limitations connues : `D:\zetaris-platform\getting-started`.
- Machine : 16 Go de RAM (le minimum pour Zetaris), GPU NVIDIA GTX 1060.
- Règle de l'équipe : tout sur le disque D:, jamais sur C:.

## Documents
| Document | Contenu |
|---|---|
| [use-case-atlas.md](use-case-atlas.md) | Le cas d'usage en détail |
| [architecture.md](architecture.md) | L'architecture (à remplir) |
| [STATUS.md](STATUS.md) | Avancement, blocages, prochaines étapes |
| [reference/guide-architecture-agentique.md](reference/guide-architecture-agentique.md) | Principes d'architecture agentique à suivre |
| [strategie/prompt-jury.md](strategie/prompt-jury.md) | Prompt qui simule le jury, pour évaluer nos choix |
| [strategie/evaluation-use-case.md](strategie/evaluation-use-case.md) | Évaluation des use cases (historique) |
| [hackathon/](hackathon/) | Documents officiels du hackathon |
