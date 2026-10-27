# Guide d'architecture agentique

Référentiel de conception pour construire une architecture IA de travail autour de Claude Code.
Rédigé le 26 octobre 2026. Les outils tiers cités en section 11 n'ont pas été testés : les informations viennent de leurs pages, README et d'une revue indépendante.

---

# 1. Cadre mental

**Un agent**, c'est un modèle + des outils + une boucle (observer → décider → agir → observer) + un état. **Le harness**, c'est tout ce qui entoure le modèle : ce qu'on lui donne à lire, les outils qu'il peut appeler, les règles qui le bornent, la mémoire, la vérification, l'observabilité.

Deux idées structurent tout le reste :

- **Le modèle est la partie la moins contrôlable du système.** Le travail d'architecture consiste à maximiser la fiabilité de l'ensemble malgré un composant probabiliste. On le fait en contrôlant ce qui entre (contexte), ce qui sort (vérification) et ce qui est permis (garde-fous).
- **Workflow ≠ agent.** Dans un workflow, c'est le code qui décide de l'enchaînement des étapes. Dans un agent, c'est le modèle. Un workflow est prévisible et bon marché, un agent est flexible et plus coûteux. Une bonne architecture utilise des workflows partout où le chemin est connu, et réserve l'autonomie aux endroits où il ne l'est pas.

---

# 2. Principes fondamentaux

| # | Principe | Ce que ça veut dire concrètement |
|---|---|---|
| 1 | **Simplicité d'abord** | Commencer par un seul agent bien outillé. Ajouter une brique uniquement quand une mesure montre qu'elle améliore quelque chose. |
| 2 | **Le contexte est la ressource rare** | La qualité dépend de ce qui est dans la fenêtre. Viser le plus petit ensemble d'informations à fort signal. Plus de contexte n'est pas mieux : au-delà d'un seuil, la qualité baisse (*context rot*). |
| 3 | **Déterministe dès que possible** | Ce qui doit toujours se produire passe par du code (hooks, scripts, permissions), pas par une consigne. Un prompt est une suggestion, un hook est une loi. |
| 4 | **Vérifier vaut plus que générer** | Chaque production doit avoir un mécanisme de contrôle : test, validation de schéma, juge, relecture humaine. |
| 5 | **Isolation des rôles** | Chaque agent a une mission, un contexte minimal et des outils limités. Un sous-agent renvoie un résultat condensé, pas son historique. |
| 6 | **Un seul écrivain par ressource** | Plusieurs agents peuvent lire en parallèle, mais une ressource (fichier, mémoire, branche) n'a qu'un seul écrivain à la fois. |
| 7 | **Humain dans la boucle sur l'irréversible** | Envoyer, supprimer, publier, payer, modifier hors du périmètre : validation explicite. |
| 8 | **Moindre privilège** | Un agent n'a accès qu'aux outils et données nécessaires à sa tâche. |
| 9 | **Réversibilité** | Git, snapshots, sauvegardes : toute action automatique doit pouvoir être annulée. |
| 10 | **Observabilité** | On doit pouvoir répondre à : qu'a fait l'agent, pourquoi, avec quel contexte, pour combien de tokens. |
| 11 | **Évaluation continue** | Un jeu de cas de test fixe, rejoué après chaque changement, pour savoir si le système progresse ou régresse. |
| 12 | **Le système de fichiers est une mémoire externe** | Écrire les plans, décisions et résultats intermédiaires dans des fichiers plutôt que de les garder dans le contexte. |
| 13 | **Concevoir l'interface des outils comme une UX** | Noms clairs, descriptions précises, peu d'outils, messages d'erreur qui disent quoi faire. Un mauvais outil fait échouer un bon modèle. |
| 14 | **Coût conscient** | Chaque brique a un coût en tokens. On le mesure, on le budgète, on route vers le modèle le moins cher qui fait le travail. |

---

# 3. Patterns d'orchestration

## Les patterns de base (du plus simple au plus autonome)

| Pattern | Fonctionnement | Quand l'utiliser | Risque |
|---|---|---|---|
| **Chaînage** | Étape A → B → C, avec un contrôle entre chaque | Tâche décomposable en étapes fixes | Rigide |
| **Routage** | Un classifieur envoie la demande vers le bon traitement ou le bon modèle | Demandes hétérogènes ; économie (petit modèle pour les cas simples) | Mauvais aiguillage silencieux |
| **Parallélisation par sections** | Sous-tâches indépendantes traitées en même temps | Lecture, recherche, analyse de plusieurs sources | Coût multiplié |
| **Vote / best-of-N** | N tentatives, on garde la meilleure ou la plus consensuelle | Tâches où la qualité varie beaucoup d'un essai à l'autre | Coût × N ; nécessite un bon critère de choix |
| **Orchestrateur-travailleurs** | Un agent planifie et délègue dynamiquement à des sous-agents | Tâches dont les sous-tâches ne sont pas connues à l'avance | Coordination coûteuse, perte d'information entre agents |
| **Évaluateur-optimiseur** | Un agent produit, un autre critique, boucle jusqu'au seuil | Critères de qualité explicites (code, rédaction) | Boucles infinies sans limite d'itérations |
| **Agent autonome** | Le modèle boucle seul avec ses outils jusqu'à la fin | Tâches ouvertes, chemin imprévisible | Dérive, erreurs qui s'accumulent, coût non borné |

## Patterns avancés

- **Plan-then-execute** : un plan est écrit dans un fichier, validé, puis exécuté étape par étape. Le plan sert de contrat et de point de reprise.
- **ReAct** : alternance raisonnement → action → observation. C'est la boucle de base de la plupart des agents de code.
- **Réflexion** : après une tâche, l'agent analyse ce qui a marché ou échoué et l'écrit pour la fois suivante.
- **Hiérarchique** : orchestrateur → chefs d'équipe → exécutants. Utile à grande échelle, coûteux sinon.
- **Handoff** : un agent passe la main à un autre avec un résumé de transfert (le pattern « swarm » au sens d'OpenAI).
- **Blackboard** : les agents ne se parlent pas directement, ils lisent et écrivent dans un état partagé. C'est ce que vise le World Model de Meterless.
- **Map-reduce** : découper une grosse entrée, traiter chaque morceau, agréger.
- **Débat / juge** : plusieurs agents argumentent, un juge tranche.
- **Exploration + vérificateur** : générer beaucoup de tentatives bon marché, filtrer avec un vérificateur fiable. C'est le principe des « courses » de Nightshift.

## Le débat multi-agents

Il y a deux écoles, et toutes deux ont raison dans leur domaine :

- **Pour** (Anthropic, dans son article sur son système de recherche multi-agents) : le parallélisme marche très bien pour l'exploration et la lecture, parce que chaque sous-agent a un contexte propre et rend un résumé condensé. Mais le coût est élevé : Anthropic rapporte un ordre de grandeur d'environ 4× les tokens d'un chat pour un agent, et environ 15× pour un système multi-agents.
- **Contre** (Cognition, dans « Don't Build Multi-Agents ») : chaque action contient des décisions implicites. Si des agents parallèles écrivent sans partager tout le contexte, leurs résultats deviennent incohérents.

**Règle pratique qui réconcilie les deux :** parallélise la lecture, sérialise l'écriture. Des sous-agents pour chercher, explorer, analyser ; un seul agent, avec le contexte complet, pour écrire et décider.

---

# 4. Les briques, une par une

## 4.1 Modèles et routage
- **Rôle** : choisir le bon modèle pour chaque tâche.
- **Niveaux** : modèle fort (conception, décisions difficiles), modèle intermédiaire (exécution), modèle rapide (classification, résumés, recherche), modèle local (tâches de masse, données sensibles).
- **Mécanismes** : règles fixes (« les sous-agents de recherche tournent sur le petit modèle »), classifieur de routage, escalade (on tente avec le petit modèle et on passe au gros en cas d'échec).

## 4.2 Runtime de l'agent
- **Rôle** : la boucle elle-même, la gestion des outils, des permissions et de la session.
- **Exemples** : Claude Code, Claude Agent SDK, frameworks maison.
- **À savoir** : on construit rarement sa propre boucle. On configure et on étend un runtime existant.

## 4.3 Outils et connecteurs
- **Rôle** : donner à l'agent la capacité d'agir (fichiers, shell, web, API, applications).
- **Mécanismes** : outils natifs, serveurs MCP, CLI, scripts.
- **Règles de conception** :
  - Peu d'outils, chacun avec une responsabilité claire. Chaque définition d'outil coûte des tokens à chaque tour.
  - Des sorties concises et paginées, pas des dumps de 10 000 lignes.
  - Des erreurs qui disent quoi corriger.
  - Préférer un script déterministe à une suite d'appels d'outils quand la séquence est connue.

## 4.4 Contexte (ce que l'agent lit)
- **Couches** :
  - **Permanent** : prompt système et instructions de projet (CLAUDE.md). Chargé à chaque tour, donc court.
  - **À la demande** : skills et documentation chargés seulement quand ils sont pertinents (*progressive disclosure* : l'agent voit d'abord un résumé d'une ligne, puis charge le détail si nécessaire).
  - **Récupéré** : recherche dans les fichiers, RAG, mémoire.
  - **Produit** : sorties d'outils, historique de la conversation.
- **Deux stratégies** : tout précharger (simple, coûteux, bruité) ou charger juste à temps (l'agent cherche ce dont il a besoin). La seconde passe mieux à l'échelle, à condition d'avoir de bons outils de recherche.

## 4.5 Mémoire

C'est la brique la plus sous-estimée et la plus facile à rater.

**Les types de mémoire** (inspirés des sciences cognitives) :

| Type | Contenu | Exemple d'implémentation |
|---|---|---|
| **De travail** | Ce qui est dans la fenêtre de contexte maintenant | La conversation en cours |
| **Épisodique** | Ce qui s'est passé (sessions, actions, résultats) | Journaux de session, transcripts résumés |
| **Sémantique** | Les faits durables (préférences, décisions, conventions) | MEMORY.md, base de faits |
| **Procédurale** | Comment faire les choses | Skills, playbooks, scripts |

**Les quatre politiques à définir explicitement** :
1. **Écriture** : qu'est-ce qui mérite d'être retenu ? Qui écrit (l'agent, un hook, un consolidateur) ? Avec ou sans validation ?
2. **Lecture** : qu'est-ce qui est injecté automatiquement au démarrage, et qu'est-ce qui est cherché à la demande ?
3. **Consolidation** : fusionner les doublons, corriger les faits périmés, résumer l'épisodique en sémantique (c'est ce que font les outils « dream »).
4. **Oubli** : ce qui expire, ce qui est archivé. Sans oubli, la mémoire devient du bruit.

**Les dimensions à trancher** :
- **Portée** : utilisateur, projet, agent, session.
- **Stockage** : fichiers markdown (lisibles, versionnables, recherchables avec grep), base vectorielle (recherche sémantique), graphe (relations), hybride.
- **Provenance** : chaque souvenir doit dire d'où il vient et quand. C'est indispensable pour trancher les contradictions.
- **Concurrence** : qui a le droit d'écrire en même temps.

**Règle d'or** : une mémoire sans politique d'écriture et de consolidation se dégrade plus vite qu'elle ne s'enrichit.

## 4.6 Gestion des longues tâches
- **Rôle** : travailler plus longtemps que ne le permet une fenêtre de contexte.
- **Techniques** :
  - **Compaction** : résumer l'historique quand il devient trop long.
  - **Prise de notes structurée** : l'agent tient un fichier de progression qu'il relit.
  - **Délégation** : l'exploration lourde part dans un sous-agent, qui ne renvoie que la conclusion.
  - **Découpage borné** (approche Markovian) : chaque morceau démarre avec un état condensé plutôt qu'avec tout l'historique.
  - **Troncature des sorties** : couper les sorties d'outils volumineuses.

## 4.7 État et coordination
- **Rôle** : faire travailler plusieurs agents ou sessions sans conflit.
- **Mécanismes** : liste de tâches partagée, blackboard, verrous, worktrees git (une copie isolée par agent), fichiers de handoff, artefacts comme contrat entre agents.
- **Règle** : les agents échangent des artefacts (fichiers, résumés, diffs), pas des transcripts complets.

## 4.8 Planification et tâches de fond
- **Rôle** : faire travailler le système sans toi.
- **Mécanismes** : cron, planificateur Windows, tâches planifiées du runtime, files de jobs, déclencheurs (nouveau fichier, nouveau mail, commit).
- **Règle** : toute tâche de fond a un budget, une limite de durée, et produit un rapport lisible.

## 4.9 Garde-fous
- **Rôle** : empêcher les dégâts.
- **Couches** :
  - **Permissions** : quels outils et commandes sont autorisés, demandés ou interdits.
  - **Sandbox** : isolation du système de fichiers et du réseau.
  - **Hooks** : contrôles déterministes avant ou après une action.
  - **Filtres d'injection** : traiter tout contenu externe (page web, mail, fichier cloné) comme non fiable.
  - **Budgets et coupe-circuit** : limite de tokens, d'itérations, de durée.
- **Le « lethal trifecta »** (formulé par Simon Willison) : un agent qui a à la fois (1) accès à des données privées, (2) exposition à du contenu non fiable et (3) un moyen de communiquer vers l'extérieur peut se faire voler des données par injection de prompt. Il faut casser au moins une des trois branches.

## 4.10 Vérification et évaluation
- **En ligne** (pendant l'exécution) : tests, linters, validation de schéma, LLM-juge, relecture humaine.
- **Hors ligne** (pour faire évoluer le système) : un jeu de cas représentatifs avec résultats attendus, rejoué après chaque modification.
- **Règle** : un agent ne valide pas son propre travail. Le vérificateur doit être indépendant (un autre agent avec un contexte neuf, un test, un humain).

## 4.11 Observabilité
- **Rôle** : comprendre ce qui se passe et ce que ça coûte.
- **Contenu** : traces des actions, contexte utilisé, décisions, tokens par tâche et par brique, taux d'échec.
- **Règle** : si tu ne peux pas dire combien coûte une tâche type, tu ne peux pas optimiser.

## 4.12 Amélioration continue
- **Rôle** : faire progresser le système sans réentraîner le modèle.
- **Mécanismes** : réflexion après tâche, raffinement des skills, distillation de la mémoire, optimisation des prompts à partir des échecs.
- **Règle** : chaque amélioration automatique passe par une évaluation, sinon elle peut dégrader le système sans qu'on s'en aperçoive.

## 4.13 Interface humaine
- **Rôle** : te garder informé et aux commandes.
- **Mécanismes** : demandes d'approbation, notifications, rapports du matin, tableaux de bord, journal des décisions.

---

# 5. Correspondance avec Claude Code

| Brique | Mécanisme Claude Code |
|---|---|
| Instructions permanentes | CLAUDE.md (global, projet, sous-dossier) |
| Mémoire sémantique | Mémoire auto (dossier `memory/` + index MEMORY.md), mémoire par sous-agent |
| Mémoire procédurale | Skills (chargement progressif) |
| Délégation, isolation | Sous-agents (contexte propre, outils et modèle configurables) |
| Contrôles déterministes | Hooks : `SessionStart`, `PreToolUse`, `PostToolUse`, `Stop`, `PreCompact`… |
| Outils externes | Serveurs MCP |
| Permissions, sécurité | Modes de permission, listes allow/ask/deny, sandbox |
| Workflows réutilisables | Commandes slash, skills |
| Distribution | Plugins (regroupent skills, agents, hooks, commandes) |
| Isolation des écritures | Worktrees git |
| Tâches de fond | Tâches planifiées, routines |
| Longues tâches | Compaction, liste de tâches, fichiers de progression |
| Conception | Mode plan |

L'essentiel de ce dont tu as besoin existe déjà nativement. Les outils externes (claude-mem, Meterless, etc.) viennent combler des manques précis, pas remplacer cette base.

---

# 6. Économie de tokens

## Où partent les tokens
- **Coût fixe à chaque tour** : prompt système, définitions d'outils (chaque serveur MCP en ajoute), CLAUDE.md, mémoire injectée.
- **Coût variable** : lectures de fichiers, sorties d'outils, historique de la conversation.
- **Multiplicateurs** : sous-agents, tentatives multiples, boucles de correction, relectures inutiles.

## Les leviers, par ordre d'impact habituel
1. **Ne pas faire faire au modèle ce qu'un script fait** : une séquence connue devient un script.
2. **Réduire le coût fixe** : CLAUDE.md court, détails déplacés dans des skills, serveurs MCP inutiles désactivés.
3. **Tronquer les sorties d'outils** : c'est souvent la plus grosse source de gaspillage (logs, tests, `npm install`).
4. **Déléguer l'exploration** à des sous-agents qui renvoient une conclusion de quelques lignes.
5. **Router vers des modèles moins chers** pour la recherche, la classification, les résumés.
6. **Profiter du cache de prompt** : un préfixe de contexte stable est facturé beaucoup moins cher en relecture (environ 10 % du prix d'entrée sur l'API Anthropic). Donc on évite de modifier le début du contexte en cours de session.
7. **Sessions courtes et ciblées** : on vide le contexte entre deux tâches.
8. **Modèles locaux** pour les tâches de masse non critiques.

**Piège classique** : ajouter une mémoire riche injectée à chaque démarrage. Elle augmente le coût fixe de toutes les sessions. Une bonne mémoire injecte un index court et laisse l'agent chercher le reste à la demande.

---

# 7. Modes d'échec et anti-patterns

| Anti-pattern | Symptôme | Remède |
|---|---|---|
| **Sur-agentification** | Dix agents là où un seul suffisait ; coût énorme | Commencer avec un agent, mesurer |
| **Pollution de la mémoire** | Faits contradictoires, périmés, doublons | Politique d'écriture, provenance, consolidation |
| **Context rot** | La qualité baisse au fil de la session | Sessions courtes, compaction, délégation |
| **Surcharge d'outils** | Mauvais choix d'outil, coût fixe élevé | Moins d'outils, mieux décrits |
| **Auto-validation** | L'agent déclare « terminé » sans preuve | Vérificateur indépendant |
| **Erreurs composées** | Échec au bout d'une longue chaîne | Contrôles intermédiaires, points de reprise |
| **Règles en prompt** | L'agent oublie ou contourne une consigne critique | Hooks et permissions |
| **Écrivains concurrents** | Conflits, fichiers écrasés | Un seul écrivain, worktrees, verrous |
| **Injection par les outils** | L'agent obéit à du texte trouvé dans une page ou un fichier | Contenu externe = données, casser le trifecta |
| **Boucles infinies** | Coût qui explose | Limite d'itérations et de budget |
| **Pas d'évaluation** | Impossible de savoir si un changement aide | Jeu de cas fixe |
| **Dérive silencieuse** | Le comportement change après une mise à jour du modèle | Évaluations rejouées régulièrement |

---

# 8. Theorycraft : les arbitrages fondamentaux

## La fiabilité composée
Si chaque étape réussit avec une probabilité *p*, une chaîne de *n* étapes réussit avec *p<sup>n</sup>*. Avec 95 % de réussite par étape, 20 étapes donnent environ 36 % de réussite. D'où deux conséquences :
- **Raccourcir les chaînes** autonomes.
- **Insérer des vérifications** : une étape vérifiée et corrigée remonte *p* vers 1. C'est la raison d'être du harness.

## Génération + vérification
Si générer est bon marché et vérifier est fiable, il vaut mieux générer N candidats et filtrer que chercher la réponse parfaite en un essai. Ça ne marche que si le vérificateur est meilleur que le hasard. Un juge LLM non calibré peut sélectionner avec assurance la mauvaise réponse.

## Les axes d'arbitrage

| Axe | Un extrême | L'autre extrême |
|---|---|---|
| Autonomie ↔ contrôle | Agent libre, flexible, imprévisible | Workflow fixe, prévisible, rigide |
| Généraliste ↔ spécialiste | Un agent qui fait tout, contexte chargé | Agents spécialisés, coût de coordination |
| Contexte complet ↔ coût | Tout précharger, cher et bruité | Juste à temps, dépend de bons outils de recherche |
| Rappel ↔ précision de la mémoire | Tout retenir, beaucoup de bruit | Retenir peu, risque d'oublier l'important |
| Parallélisme ↔ cohérence | Rapide, résultats divergents | Séquentiel, lent, cohérent |
| Latence ↔ qualité | Réponse immédiate | Vérifications et itérations |
| Déterminisme ↔ flexibilité | Code, fiable mais limité | Modèle, adaptable mais faillible |

Une architecture, c'est une position assumée sur chacun de ces axes, tâche par tâche.

## Questions de conception à se poser pour chaque brique
1. Quel problème mesuré résout-elle ?
2. Combien coûte-t-elle en tokens, par tour et par tâche ?
3. Qui décide : le code ou le modèle ?
4. Qui écrit, qui lit ?
5. Comment sait-on qu'elle fonctionne ?
6. Que se passe-t-il quand elle échoue ?
7. Peut-on l'annuler ?

---

# 9. Méthode de construction

1. **Définir les tâches réelles** que le système doit faire, avec des exemples concrets.
2. **Mesurer la base** : faire ces tâches avec Claude Code nu et noter les tokens, le temps et les erreurs.
3. **Identifier les frictions** : ré-explications, oublis, sorties trop longues, erreurs répétées.
4. **Ajouter une brique par friction**, la plus simple possible.
5. **Réévaluer** sur les mêmes tâches. On garde la brique si elle améliore la mesure, on la retire sinon.
6. **Itérer.** L'architecture finale émerge des mesures, pas d'un schéma dessiné à l'avance.

---

# 10. Intégrer des outils tiers (mémoire, optimisation, orchestration…)

Un outil tiers n'est pas une brique gratuite : c'est une dépendance qui ajoute du code exécuté sur ta machine, du contexte, et parfois des appels de modèle cachés. Cette section dit quoi vérifier avant, pendant et après l'ajout.

## 10.1 Avant d'installer : la grille de décision

| Critère | Question à se poser | Signal d'alerte |
|---|---|---|
| **Problème mesuré** | Quelle friction précise, constatée à l'étape 2 de la méthode, cet outil résout-il ? | « Ça a l'air bien », « beaucoup d'étoiles » |
| **Recouvrement avec le natif** | Claude Code fait-il déjà ça (mémoire auto, skills, sous-agents, compaction, hooks) ? | L'outil remplace un mécanisme natif sans gain démontré |
| **Coût en tokens net** | Combien ajoute-t-il au coût fixe (contexte injecté, définitions d'outils MCP, descriptions de skills) ? Fait-il lui-même des appels de modèle ? | Économies annoncées sans compter son propre surcoût |
| **Gratuité réelle** | Licence (MIT, Apache, BSD = libre ; AGPL = libre en usage perso, contraintes si redistribué ; pas de LICENSE = pas de droit clair). Version payante ? Service hébergé ? Clé API tierce ? | Fonction clé derrière un abonnement ; binaires propriétaires |
| **Maturité** | Date du dernier commit, nombre de mainteneurs, issues ouvertes, statut beta | Projet d'une seule personne, abandonné, « replica » d'une fonction non publiée |
| **Sécurité** | Quels hooks et scripts exécute-t-il ? Quels appels réseau ? Télémétrie ? Accès aux transcripts et aux secrets ? | Script d'installation `curl | sh` non relu ; hooks opaques ; envoi de données vers un serveur |
| **Compatibilité** | Fonctionne-t-il sous Windows ? Exige-t-il Git Bash, WSL, une carte NVIDIA, Ollama ? | Support Windows « non testé » |
| **Emplacement des données** | Où écrit-il (cache, base, logs) ? Peut-on le pointer vers `D:` ? | Base ou cache imposé sur `C:` |
| **Format des données** | La mémoire est-elle en fichiers lisibles (markdown) ou dans une base propriétaire ? | Impossible d'exporter ou de relire sans l'outil |
| **Réversibilité** | Peut-on le désinstaller proprement ? Que reste-t-il (hooks, configs, fichiers) ? | Modifie `settings.json` ou `~/.claude` sans trace |

## 10.2 Pendant l'installation : les règles

1. **Un outil à la fois.** Sinon impossible de savoir lequel aide ou casse.
2. **Lire avant d'exécuter.** Scripts d'installation, hooks, `package.json` (scripts `postinstall`), code des serveurs MCP.
3. **Figer les versions.** Une mise à jour automatique d'un hook peut changer le comportement du système sans prévenir.
4. **Sauvegarder avant.** Snapshot de `~/.claude` (settings, skills, mémoire) et commit du projet.
5. **Installer dans le périmètre le plus étroit.** Projet plutôt que global, tant que l'outil n'a pas fait ses preuves.
6. **Noter l'installation** dans un fichier du projet (`DECISIONS.md` ou `STACK.md`) : quoi, pourquoi, version, comment le retirer.

## 10.3 Après l'installation : mesurer

- **Protocole A/B** : rejouer les mêmes tâches de référence avec et sans l'outil.
- **Mesures** : tokens par tâche (y compris ceux que l'outil consomme lui-même), temps, qualité du résultat, nombre de corrections.
- **Durée d'essai** : plusieurs sessions sur un vrai projet, pas une démo.
- **Verdict** : l'outil reste s'il améliore la mesure, sinon on le retire et on note pourquoi.

## 10.4 Les conflits entre outils

C'est le risque principal quand on empile des briques.

- **Deux systèmes de mémoire en parallèle** (par exemple mémoire auto + claude-mem + H-MEM) : souvenirs contradictoires, injection en double, coût fixe multiplié. **Règle : une seule mémoire maîtresse**, les autres sont désactivées ou en lecture seule.
- **Plusieurs hooks sur le même événement** : ordre d'exécution incertain, effets qui s'annulent ou se cumulent.
- **Double compaction** : un plugin de compaction plus la compaction native peuvent résumer un résumé et perdre de l'information.
- **Plusieurs orchestrateurs** : agents qui portent le même nom, règles contradictoires dans le contexte.
- **Écritures concurrentes** dans la mémoire quand plusieurs sessions tournent : aucun de ces outils ne gère bien les verrous.

## 10.5 Points spécifiques par catégorie

### Mémoire (claude-mem, memXT, Mem0 / OpenMemory, H-MEM)
- **La capture automatique pollue.** Un outil qui enregistre « tout ce que fait Claude » retient aussi les fausses pistes et les erreurs. Il faut une politique de tri ou une consolidation.
- **La compression coûte des tokens.** Un outil qui résume les sessions avec un modèle (claude-mem passe par l'Agent SDK de Claude) consomme ton quota. L'économie réelle = tokens économisés en contexte − tokens dépensés à résumer.
- **L'injection au démarrage alourdit chaque session.** Préférer un index court + recherche à la demande.
- **Confidentialité.** Capturer les sessions, c'est aussi capturer les secrets, chemins et données qui passent. Vérifier où c'est stocké et si quelque chose sort de la machine.
- **Portabilité.** Une mémoire en markdown survit à l'outil ; une mémoire dans une base propriétaire meurt avec lui.

### Consolidation (dream-skill, claude-dream)
- **Toujours une porte de validation humaine** au début : l'outil propose, tu approuves.
- **Snapshot avant chaque passe**, rollback possible.
- **Fréquence = coût.** Une passe quotidienne relit les transcripts : c'est un coût récurrent.
- **Une seule source de vérité** : la consolidation s'applique à la mémoire maîtresse, pas à plusieurs stores.

### Optimisation des tokens (squeez, Magic Compact, cctx, token-optimizer-mcp)
- **Compression avec perte = risque.** Tronquer une sortie de test ou un log peut masquer exactement l'erreur dont l'agent avait besoin. Vérifier que les erreurs restent visibles.
- **Mesurer le gain net.** Un serveur MCP d'optimisation ajoute ses propres définitions d'outils au coût fixe.
- **Dépendances matérielles.** cctx demande Ollama et un modèle local ; squeez demande Git Bash sous Windows.
- **Remplacement du natif.** Un plugin de compaction remplace un comportement de Claude Code : il faut comparer avec la compaction native sur des sessions longues.

### Orchestration et bundles (oh-my-claudecode, Claude Flow / Ruflo, collections de skills et d'agents)
- **Multiplication des tokens.** Plus d'agents = plus de contextes = plus de tokens (voir l'ordre de grandeur ×15 en section 3).
- **Coût fixe des descriptions.** Chaque skill et chaque agent installé ajoute sa description au contexte. Installer à la carte, pas le bundle entier.
- **Remplacement des comportements natifs** et règles contradictoires avec ton CLAUDE.md.
- **Surface d'attaque.** Un bundle communautaire non audité peut contenir des hooks qui exécutent n'importe quoi.

### Engines Meterless (H-MEM, Markovian, World Model, Scout, Swarm)
- **Maturité** : jugés « pilote, pas production » par la revue indépendante.
- **Stack** : TypeScript ; usage avec Claude Code via des prompts qui lisent le repo, pas une intégration native.
- **Licence mixte** : spécifications et implémentations de référence en Apache-2.0, binaires Gaia, Relay et Swarms propriétaires.
- **Chiffres non indépendants** : économies de tokens calculées sur une démo avec modèle factice.
- **À traiter comme un pilote** sur un seul projet, comparé à la base native.

### Modèles locaux et jobs de nuit (Ollama, LM Studio, Nightshift)
- **Qualité inférieure** aux modèles frontière : réserver aux tâches non critiques ou vérifiables.
- **Matériel** : Nightshift sous Windows demande une carte NVIDIA (CUDA) ou passe par Vulkan.
- **Deux « Nightshift » différents** : le produit de Meterless (runtime local + jobs) et la CLI Go `marcus/nightshift` (maintenance de code la nuit, MIT). Ne pas les confondre.
- **Les jobs de fond consomment ton quota** s'ils appellent Claude : budget plafonné obligatoire.

---

# 11. Catalogue des outils repérés (non testés)

| # | Brique | Rôle | Options gratuites | Ce que Meterless apporte |
|---|---|---|---|---|
| 1 | **Orchestration** (agent principal et sous-agents) | Découper le travail, déléguer | Sous-agents natifs de Claude Code, [oh-my-claudecode](https://www.sourcepulse.org/projects/22300495), Claude Flow | Swarm (peu documenté) |
| 2 | **Mémoire long terme** | Se souvenir entre sessions | CLAUDE.md et mémoire auto (natifs), [claude-mem](https://github.com/thedotmack/claude-mem), [memXT](https://github.com/yupcha/memxt), [Mem0 / OpenMemory](https://huggingface.co/blog/lynn-mikami/open-memory-mcp-server) | **H-MEM** : mémoire à trois niveaux, fichiers lisibles |
| 3 | **Consolidation de la mémoire** | Nettoyer, fusionner, corriger | [dream-skill (timoncool)](https://github.com/timoncool/dream-skill), [claude-dream](https://github.com/mengazaa/claude-dream) | Non couvert |
| 4 | **Skills et procédures** | Réutiliser les méthodes de travail | Skills natifs, bundles GitHub (à vérifier), [self-improving-skills](https://github.com/unisone/self-improving-skills) | Non couvert |
| 5 | **Optimisation des tokens** | Réduire le contexte et les sorties | [squeez](https://docs.rs/crate/squeez/1.18.0), [Magic Compact](https://github.com/aerovato/magic-compact), [cctx](https://glama.ai/mcp/servers/anil7948/cctx), /compact natif, sous-agents sur Haiku | **Markovian** : tâches longues découpées, contexte borné |
| 6 | **État partagé entre agents** | Éviter que les agents divergent | Fichiers partagés + verrous (à construire) | **World Model** |
| 7 | **Routage** (quel outil, quel modèle) | Choisir le bon agent et le bon modèle | Choix manuel, règles dans CLAUDE.md | **Scout** et les modes `meterless/auto`, `cheap`, `local` |
| 8 | **Modèles locaux** (travaux de fond gratuits) | Faire les tâches simples sans quota | [Ollama](https://ollama.com), LM Studio, édition gratuite de Nightshift | Runtime local + Nightshift |
| 9 | **Tâches planifiées** | Travailler la nuit | Planificateur Windows, tâches planifiées de Claude Code, Nightshift CLI (MIT) | Nightshift (jobs de nuit) |
| 10 | **Garde-fous et sécurité** | Bloquer l'injection, limiter les droits | Hooks et permissions natifs, skill de revue | **Scout** (filtre d'injection) |
| 11 | **Connecteurs** | Gmail, Drive, Notion, calendrier, dépôts | Serveurs MCP | Non couvert |
| 12 | **Suivi de consommation** | Savoir où partent les tokens | Explain-usage, outils de suivi d'usage | Non couvert (les démos parlent de consommation électrique) |
| 13 | **Qualité et évaluation** | Vérifier les résultats | Skills de revue, tests | Le « judge » des démos (peu détaillé) |

## Évaluation des engines Meterless

- **Ce qui est fort :** la mémoire (2) et les tâches longues (5). Ce sont les deux points les plus durs à faire soi-même, et H-MEM a une structure lisible sur disque, compatible avec l'approche `MEMORY.md`.
- **Ce qui est moyen :** l'état partagé (6) et le routage (7). Les idées sont là, mais la documentation est courte et l'usage avec Claude Code passe par des prompts, pas par une intégration native.
- **Ce qui manque :** orchestration, connecteurs, planification, suivi de consommation. Ce ne sont pas leurs cibles.
- **Points faibles :** la maturité (la revue dit « pilote, pas production »), une dépendance à leur stack TypeScript, des chiffres d'économie non indépendants, et des binaires propriétaires (Gaia, Relay, Swarms).

## Ordre d'intégration recommandé

1. **Base native, sans rien installer** : CLAUDE.md global, mémoire auto, sous-agents, skills, hooks, tâches planifiées.
2. **Ajouter les briques gratuites qui manquent** : claude-mem ou memXT pour la mémoire, squeez pour la sortie bash, dream-skill pour la consolidation. Une brique à la fois, en mesurant (section 10).
3. **Piloter Meterless sur un seul projet** : cloner le repo sur `D:\`, lancer la démo sans clé API (`npx tsx examples/memory-compounding-research/index.ts`), puis tester H-MEM et Markovian sur une tâche longue. Comparer le nombre de tokens et la qualité avec la base native.
4. **Décider après le pilote** : si H-MEM ou Markovian font nettement mieux que claude-mem sur la tâche, les intégrer. Sinon, rester sur la base native et garder Meterless pour les expérimentations.

**Critère de décision :** une brique reste si elle réduit les tokens ou le temps de correction sur un vrai projet, sinon elle part.

---

# 12. Lectures de référence

- **Anthropic**, *Building Effective Agents* : workflows vs agents, les patterns de base.
- **Anthropic**, *Effective Context Engineering for AI Agents* : gestion du contexte, compaction, notes, sous-agents.
- **Anthropic**, *How We Built Our Multi-Agent Research System* : orchestrateur-travailleurs en pratique, coûts.
- **Anthropic**, *Writing Effective Tools for Agents* : conception des outils.
- **Anthropic**, les bonnes pratiques Claude Code (documentation officielle).
- **Cognition**, *Don't Build Multi-Agents* : le contre-argument sur le partage de contexte.
- **HumanLayer**, *12-Factor Agents* : principes d'ingénierie pour des agents en production.
- **Lilian Weng**, *LLM Powered Autonomous Agents* : la taxonomie planification / mémoire / outils.
- **Article MemGPT** (devenu Letta) : la mémoire hiérarchique gérée par l'agent lui-même.
- **Simon Willison**, ses articles sur l'injection de prompt et le *lethal trifecta*.

## Sources des outils

- [Meterless — engines](https://meterless.ai/engines.html) · [Meterless — Nightshift](https://meterless.ai/) · [Repo Meterless](https://github.com/Meterless/Meterless)
- [Revue indépendante de Meterless (wavect.io, 22 juillet 2026)](https://wavect.io/de/blog/meterless-ai-agent-context-layer-review.md)
- [Papier académique H-MEM (arXiv 2507.22925)](https://arxiv.org/html/2507.22925v1) — distinct de l'implémentation Meterless
- [Nightshift CLI (marcus)](https://pkg.go.dev/github.com/marcus/nightshift)
- [Hindsight — mémoire partagée entre sous-agents](https://hindsight.vectorize.io/blog/2026/05/06/claude-code-subagents-shared-memory)
- [Awesome Claude Code — orchestrateurs](https://www.mintlify.com/hesreallyhim/awesome-claude-code/tooling/orchestrators)
