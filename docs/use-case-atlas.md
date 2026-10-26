# Cas d'usage : Atlas

Use case retenu pour l'Open Agent Hackathon 2026 (décision du 26 octobre 2026, architecture à valider). Origine : proposition d'une autre analyse (ChatGPT), complétée avec la vision de l'équipe : une mémoire projet autonome qui suit l'avancement de chacun, coordonne l'équipe, recommande les réunions utiles, remonte automatiquement l'information au manager et capitalise d'un projet à l'autre.

**Track : à trancher dans l'architecture** (voir section 10).
- **01 — Solving Fragmented Intelligence** si la démo est centrée sur le rapprochement de sources qui se contredisent.
- **03 — Reasoning Architecture** si elle est centrée sur les décisions que la mémoire déclenche (arbitrage, réunion, correction, alerte au manager). Les ajouts du 26 octobre rapprochent le cas de ce track.

---

## 1. Le produit en une phrase

Format du guide, pour le deck :

> We are building an agent that keeps a team's project coordinated: it reconciles the project's fragmented sources (briefs, messages, tickets, tasks, decision register) served through Zetaris, remembers each member's progress against their tasks and objectives whichever AI assistant they use, detects contradictions and stale deliverables, recommends when a meeting is needed and with whom, and pushes the relevant updates to the manager automatically — while keeping a memory of past projects to reuse what the organisation learned.

En français : un agent qui garde un projet d'équipe coordonné. Il rapproche les sources dispersées, mémorise l'avancement de chaque membre par rapport à ses tâches et objectifs, quelle que soit son IA, repère les contradictions et les livrables périmés, dit quand une réunion est nécessaire et avec qui, remonte automatiquement l'essentiel au manager, et garde la mémoire des projets passés.

### Les capacités du produit

| # | Capacité | Ce que ça veut dire |
|---|---|---|
| 1 | Contexte fiable | Distinguer ce qui fait foi (décision approuvée) de ce qui ne fait pas foi (proposition, message, information remplacée) |
| 2 | Avancement par membre | Suivre ce que chacun fait par rapport à ses tâches, échéances et objectifs |
| 3 | Coordination | Détecter deux travaux contradictoires avant qu'ils ne produisent un livrable |
| 4 | Action sur les livrables | Préparer la correction d'un livrable périmé, avec ses preuves |
| 5 | Recommandation de réunion | Dire quand une réunion est nécessaire, avec qui, pourquoi, et proposer un ordre du jour |
| 6 | Vue manager | Une vue d'ensemble du projet, qu'il soit petit ou gros |
| 7 | Remontées automatiques | Prévenir le manager de ce qui compte (risque, conflit, retard, décision) sans qu'il ait à demander |
| 8 | Mémoire du projet | L'état et l'historique du projet, versionnés |
| 9 | Mémoire de l'organisation | Les enseignements des projets passés, réutilisés sur les nouveaux |
| 10 | Accès multi-IA | Chaque membre récupère le contexte depuis son IA via MCP |

**Ce qui nous différencie.** Le partage de mémoire entre IA existe déjà (Mem0 / OpenMemory, Supermemory). Notre mémoire est **autonome et active** : elle sait ce qui fait foi, elle surveille l'avancement et la cohérence du travail de chacun, et elle déclenche des actions (correction, réunion, alerte au manager).

### Démo et feuille de route
Tout ne peut pas être construit avant la clôture. Proposition de répartition, à confirmer dans l'architecture :

| Capacité | Démo du hackathon | Feuille de route (slide « future enhancements ») |
|---|---|---|
| 1, 2, 3, 4, 10 | Oui : c'est le cœur | — |
| 5 Réunion | Oui, version simple : règles explicites et ordre du jour | Planification dans les agendas |
| 6 Vue manager | Oui, une page en lecture seule | Portefeuille de projets, filtres, droits |
| 7 Remontées | Oui, déclenchées par les changements d'état pendant le run | Envoi par mail ou Slack, fréquence réglable |
| 8 Mémoire projet | Oui | — |
| 9 Mémoire organisation | Si le temps le permet : un enseignement d'un projet passé rappelé dans la démo | Mémoire de tous les projets, recherche transverse |

---

## 2. Le scénario

**Entreprise fictive. Projet : le lancement d'Atlas, un portail client B2B.**

| Personne | Rôle | Outil IA dans la démo | Tâches et objectifs |
|---|---|---|---|
| Léa | Responsable produit | Claude Desktop (client MCP) | Piloter le lancement ; valider le brief commercial |
| Hugo | Développeur | Cursor ou Claude Code (client MCP) | Terminer l'export CSV ; préparer le SSO pour la v2 |
| Sarah | Commerciale | Brouillon commercial (source) | Rédiger le brief commercial |
| Inès | QA | Tickets (source) | Valider la recette de l'export CSV |
| Marc | Manager | Vue manager | Suivre le projet de loin, arbitrer |

**Ce que racontent les sources :**

| Source | Information |
|---|---|
| Ancien brief | Lancement le **3 novembre**, avec export CSV et connexion SSO |
| Registre de décisions | Report approuvé au **10 novembre** ; SSO déplacé en version 2 |
| Message récent | Quelqu'un recopie l'ancienne date du 3 novembre |
| Ticket QA | L'export CSV échoue encore à un test bloquant |
| Brouillon commercial | Reprend l'ancienne date, annonce le SSO et affirme que tout est prêt |
| Tâches et objectifs | Chaque membre, ses tâches, échéances et avancement ; la tâche CSV de Hugo est en retard sur son échéance, et le brief de Sarah dépend de la date de lancement |
| Projets passés | Un projet précédent (« Orion ») a raté son lancement parce que le brief commercial avait été envoyé avant la fin de la recette |

**La demande de Léa :**
> « Vérifie la date, le périmètre et les blocages du lancement, puis prépare la correction du brief commercial. »

**Le résultat attendu :**
> Date cible approuvée : 10 novembre (décision du registre).
> Périmètre : export CSV ; SSO prévu en version 2.
> Lancement encore bloqué par la recette CSV (ticket QA) ; la tâche de Hugo est en retard.
> Correction du brief commercial préparée, avec un diff et la source de chaque changement.
> Réunion recommandée : Hugo, Inès et Sarah, 15 minutes, pour caler la fin de la recette CSV avant l'envoi du brief. Précédent : le projet Orion.
> Remontée au manager : lancement à risque (recette CSV), brief corrigé, réunion proposée.

---

## 3. Ce qui fait foi : les types d'information

| Type | Exemple | Fait foi ? |
|---|---|---|
| Proposition | « On pourrait décaler au 12 novembre. » | Non |
| Décision approuvée | « J'approuve le report », par une personne habilitée | Oui, sur son sujet |
| Observation | « Le test CSV a échoué. » | Oui, comme constat |
| Information historique | Une ancienne décision remplacée | Non, conservée pour l'historique |
| Déclaration de travail en cours | « Je rédige le brief avec le SSO. » | Non, c'est un état à surveiller |
| Avancement de tâche | « Export CSV : 70 %, échéance hier » | Oui, comme constat daté |
| Enseignement d'un projet passé | « Ne pas envoyer le brief avant la fin de la recette » | Non, c'est une recommandation |

**Règles d'autorité :**
1. Une décision approuvée par une personne habilitée fait foi sur son sujet (date, périmètre).
2. Un message plus récent n'annule pas une décision approuvée.
3. Deux décisions applicables et incompatibles produisent un **conflit à arbitrer**. Le système ne choisit jamais la dernière arrivée.
4. Les habilitations sont vérifiées par le backend (table des rôles), jamais par le texte d'un message.
5. Une date validée ne signifie pas que le lancement est prêt : il faut aussi que les blocages soient levés.
6. Une information venant d'un autre projet est ignorée pour l'état du projet ; seule la mémoire de l'organisation peut s'en servir, comme recommandation.
7. Une source réingérée en double ne crée pas de doublon.

---

## 4. Ce que fait le système

1. **Retrouver** les informations pertinentes dans les sources (via Zetaris).
2. **Identifier les contradictions** sur la date, le périmètre et l'état de préparation.
3. **Appliquer les règles d'autorité.**
4. **Vérifier les conditions restantes** (blocages ouverts, tâches en retard).
5. **Préparer la correction** du livrable périmé, avec un diff et les sources.
6. **Publier une nouvelle version de l'état du projet**, récupérable par l'IA de n'importe quel membre.
7. **Suivre l'avancement de chaque membre** (tâches, échéances, objectifs, travail déclaré depuis son IA via MCP) et **détecter les travaux contradictoires**.
8. **Recommander une réunion** quand une règle se déclenche (voir ci-dessous), avec les participants, la raison, les preuves et un ordre du jour.
9. **Remonter automatiquement au manager** les changements qui comptent : risque sur une échéance, conflit ouvert, décision prise, livrable corrigé, réunion proposée.
10. **Tenir la vue manager** : décisions validées, blocages, avancement par membre, conflits et réunions en attente.
11. **Capitaliser** : en fin de projet ou d'étape, enregistrer les enseignements dans la mémoire de l'organisation, et les rappeler quand une situation semblable se présente.

### Quand recommander une réunion
Règles de départ, à affiner dans l'architecture :
- deux membres ou plus ont des travaux contradictoires en cours ;
- une tâche dont dépend le travail d'un autre membre est en retard ou bloquée ;
- un jalon est à risque : l'avancement est en dessous de ce qu'il devrait être à cette date ;
- un conflit reste sans arbitrage au-delà d'un délai fixé.

Une réunion n'est recommandée que si un échange synchrone est plus efficace qu'un message : sinon, le système prévient directement les personnes concernées. La recommandation est une proposition au manager, jamais un envoi d'invitations automatique.

---

## 5. Scénarios de test

| # | Scénario | Résultat attendu |
|---|---|---|
| S1 | État normal | Date 10 novembre, périmètre CSV, SSO en v2, blocage QA, correction du brief |
| S2 | Nouvelle décision autorisée : report au 12 novembre | Le second client MCP récupère la nouvelle date, la nouvelle version et ses sources |
| S3 | Deux décisions contradictoires applicables | Conflit escaladé, aucune des deux n'est appliquée seule |
| S4 | Information venant d'un autre projet | Ignorée pour l'état du projet |
| S5 | Réingestion d'un doublon | Pas de doublon dans l'état |
| S6 | Deux membres travaillent sur des choses contradictoires | Conflit détecté, les deux prévenus, arbitrage proposé au manager |
| S7 | Une tâche bloquante est en retard et d'autres en dépendent | Réunion recommandée avec les bonnes personnes, la raison et un ordre du jour |
| S8 | Un changement d'état important pendant le run | Remontée automatique au manager, visible dans sa vue |
| S9 | Une situation déjà vécue sur un projet passé | L'enseignement du projet Orion est rappelé, comme recommandation |

Les cinq premiers et 14 cas de test viennent du kit de l'autre analyse. **Les résultats attendus sont séparés des sources lues par les agents** : le résultat est calculé à partir des données, les attendus servent seulement à évaluer.

Contrôle anti-triche : changer une date ou un avancement juste avant une répétition. Les clients et la vue manager doivent refléter la nouvelle valeur.

---

## 6. Les données et Zetaris

### Pourquoi des données synthétiques
Les messages, tickets, tâches et décisions internes d'une équipe ne sont jamais publics. Un petit corpus synthétique est même préférable pour tester la cohérence : on connaît les réponses attendues et on provoque exactement les situations voulues. Les règles officielles l'autorisent (§11.1, « synthetic or simulated data, clearly identified »).

### Le corpus
| Source | Contenu | Origine |
|---|---|---|
| Documents | Briefs, spécifications | Kit (8 enregistrements) |
| Messages | Échanges de l'équipe | Kit (16) |
| Tickets | Tickets QA et techniques | Kit (10) |
| Décisions | Registre des décisions approuvées | Kit (6) |
| Tâches et objectifs | Membre, tâche, échéance, avancement, dépendances | **À créer** |
| Projets passés | Résumés et enseignements de projets précédents | **À créer** |

Le kit n'est pas encore sur le PC : soit on le récupère, soit Claude génère l'ensemble du corpus dans `data/sample/`.

### Comment les données arrivent dans Zetaris
Zetaris ne lit pas un fichier local : il lit une URL (API REST en GET) ou un fichier sur un stockage accessible (S3). Les agents, eux, n'appellent pas les fichiers : ils envoient des requêtes SQL à Zetaris, qui va lire les sources.

| Voie | Contenu | Rôle | Statut |
|---|---|---|---|
| **A. Corpus publié dans le repo GitHub public** | Un JSON par source, de la forme `{"records": [...]}`, servi par jsDelivr | Source principale, stable et reproductible | À tester dans Zetaris |
| **B. API locale** | Les mêmes sources servies par une petite API sur la machine ; Zetaris (dans Docker) la joint via `host.docker.internal` | Démo en direct : une décision ou un avancement modifié apparaît aussitôt (une table REST relit sa source à chaque requête, sauf si on la met en cache) | À tester |
| **C. Mode réel (option)** | Un vrai projet open source via l'API publique de GitHub : issues, pull requests, jalons | Montrer que ça marche aussi sur des données réelles | Non testé |

**Contraintes Zetaris confirmées** (repo `D:\zetaris-platform\getting-started`) : une table REST correspond à une URL fixe en GET ; le JSON doit être un objet contenant un tableau ; une table REST rappelle sa source à chaque requête sauf `CACHE TABLE` ; aucune écriture dans Zetaris n'est vérifiée.

**Conséquence :** Zetaris sert les sources de l'entreprise, en lecture. L'état versionné du projet, l'avancement déclaré via MCP et la mémoire de l'organisation vivent dans les engines Meterless, pas dans Zetaris.

---

## 7. Technologies sponsors

| Technologie | Rôle concret |
|---|---|
| **Zetaris** | Expose les sources comme des tables ; les agents les interrogent en SQL (sujet, date, statut, membre, échéance) |
| **Meterless World Model** | État partagé du projet, fondé sur des événements : décisions, observations, avancement et travail en cours de chaque membre, versions. Demande une implémentation et une suite de conformité |
| **Meterless H-MEM** | Mémoire de l'organisation : les enseignements des projets passés, avec leur source et leur niveau de confiance. Second engine, à n'ajouter que si le premier marche |
| **Meterless Nightshift** | Fournisseur IA principal de tous les appels (provider déjà codé dans `agent/llm.py`) |
| **NVIDIA Nemotron** | Les agents (analyse, contrôle, synthèse pour le manager), via Nightshift ; le modèle est journalisé pour chaque requête |

---

## 8. Démo (cible : 3 min 50)

| Temps | Scène |
|---|---|
| 0:00–0:20 | Le problème : le brief commercial annonce une mauvaise date, un mauvais périmètre et un « tout est prêt » injustifié ; une tâche bloquante est en retard |
| 0:20–1:10 | Léa lance la vérification ; l'analyste interroge Zetaris ; le contrôleur vérifie les décisions, le blocage QA et l'avancement |
| 1:10–1:35 | Le diff du brief apparaît, avec la source de chaque changement |
| 1:35–2:15 | La coordination : Hugo (Cursor) déclare retirer le SSO pendant que le brief le réintroduit ; conflit détecté, les deux prévenus |
| 2:15–2:50 | La vue manager : Marc voit l'état du projet, la remontée automatique (lancement à risque) et la réunion recommandée (Hugo, Inès, Sarah), avec le précédent du projet Orion |
| 2:50–3:20 | Une nouvelle décision autorisée reporte au 12 novembre ; un second client MCP récupère la nouvelle date et ses sources |
| 3:20–3:50 | Les preuves : requêtes Zetaris, conformité des engines, modèle Nemotron par requête, traces des agents ; les limites |

Il faut nommer les clients réellement utilisés. Deux panneaux de notre propre application ne sont pas une intégration entre deux IA.

---

## 9. Hors périmètre

- Synchroniser automatiquement les mémoires natives des assistants : MCP expose des outils que les clients appellent, il ne synchronise rien tout seul.
- Une vraie intégration ChatGPT : elle exige un serveur MCP distant en HTTPS.
- Envoyer des invitations de réunion ou des mails : le système recommande, l'humain décide.
- Un système d'authentification complet : une table de rôles suffit.
- Écrire dans Zetaris.

---

## 10. Questions ouvertes pour l'architecture

À trancher dans [architecture.md](architecture.md) :
1. **Track 01 ou 03 ?** Le récit de la démo en dépend.
2. Combien d'agents LLM, et lesquels ? Départ proposé : un analyste, un contrôleur, et un orchestrateur en code qui applique les droits et les versions. Faut-il un agent de synthèse pour le manager, ou est-ce le rôle du contrôleur ?
3. Qui décide de l'enchaînement : le code ou le modèle ? À quels endroits ?
4. Comment l'avancement est-il capté : tâches dans Zetaris, déclarations via MCP, ou les deux ?
5. Comment détecter un conflit ou décider d'une réunion : règles structurées, jugement d'un LLM, ou les deux (règles qui déclenchent, LLM qui rédige) ?
6. Quel niveau d'autonomie : l'agent propose et l'humain valide, ou l'agent boucle sous contrôles ?
7. Qu'est-ce qui vit dans Zetaris, dans le World Model, dans H-MEM ?
8. Un ou deux engines ? Le guide conseille un seul engine dans une fonctionnalité qui marche, avant d'en ajouter un second.
9. Quels outils MCP ? Départ proposé : récupérer le contexte, consulter les preuves, proposer une mise à jour, déclarer son avancement.
10. Les remontées au manager : déclenchées par quels événements, et sous quelle forme ?
11. Vue manager : quelle forme minimale ?
12. Qu'est-ce qui reste dans la démo, qu'est-ce qui passe en feuille de route ?

---

## 11. Le kit de démonstration

Le kit (`kit-demo-atlas.zip`) a été produit par l'autre analyse : cadrage, script de démo, architecture proposée, données, attendus et une petite API locale. **Il n'est pas sur le PC et n'a pas été relu.** S'il est récupéré, le déposer dans `external/kit-demo-atlas/` (ignoré par git) : il sera relu entièrement avant toute exécution, puis ses données seront reprises dans `data/sample/`.
