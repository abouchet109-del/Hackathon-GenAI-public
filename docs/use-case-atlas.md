# Cas d'usage : Atlas

Use case retenu pour l'Open Agent Hackathon 2026 (décision du 26 octobre 2026, architecture à valider). Origine : proposition faite par une autre analyse (ChatGPT), complétée ici avec la différenciation de l'équipe : suivi de l'avancement de chaque membre, détection des travaux contradictoires et vue manager.

**Track visé : 01 — Solving Fragmented Intelligence.** Le cœur du cas est de rapprocher des sources dispersées qui ne concordent pas, ce qui est l'énoncé exact de ce track.

---

## 1. L'idée en une phrase

Format du guide, pour le deck :

> We are building an agent that keeps a product team's launch coordinated: it reconciles the team's fragmented sources (briefs, messages, tickets, decision register) served through Zetaris, tracks what each member is working on from whichever AI assistant they use, detects contradictions and stale deliverables before they ship, and produces a sourced project state and deliverable corrections, readable from every member's AI through MCP and summarized for the team manager.

En français : un agent qui garde une équipe alignée. Il rapproche les sources dispersées du projet, suit ce que fait chaque membre quelle que soit son IA, repère les contradictions et les livrables périmés avant qu'ils ne partent, et produit un état du projet sourcé et des corrections. Chaque membre récupère cet état depuis son IA, et le manager le suit de loin.

**Ce qui nous différencie** (le partage de mémoire entre IA existe déjà chez Mem0 ou Supermemory) :
1. La mémoire distingue ce qui fait foi (décision approuvée) de ce qui ne fait pas foi (proposition, message, information remplacée).
2. Elle suit l'avancement de chaque membre et détecte deux travaux contradictoires avant qu'ils ne produisent un livrable.
3. Elle agit : elle prépare la correction d'un livrable périmé, avec ses preuves.

---

## 2. Le scénario

**Entreprise fictive. Produit : Atlas, un portail client B2B en préparation de lancement.**

| Personne | Rôle | Outil IA dans la démo | Ce qu'elle fait |
|---|---|---|---|
| Léa | Responsable produit | Claude Desktop (client MCP) | Pilote le lancement, demande les vérifications |
| Hugo | Développeur | Cursor ou Claude Code (client MCP) | Travaille sur l'export CSV et le périmètre technique |
| Sarah | Commerciale | Brouillon commercial (source) | Rédige le brief commercial |
| Inès | QA | Tickets (source) | Signale les tests bloquants |
| Marc | Manager | Vue manager | Suit le projet de loin et arbitre |

**Ce que racontent les sources** (corpus du kit) :

| Source | Information |
|---|---|
| Ancien brief | Lancement le **3 novembre**, avec export CSV et connexion SSO |
| Registre de décisions | Report approuvé au **10 novembre** ; SSO déplacé en version 2 |
| Message récent | Quelqu'un recopie l'ancienne date du 3 novembre |
| Ticket QA | L'export CSV échoue encore à un test bloquant |
| Brouillon commercial | Reprend l'ancienne date, annonce le SSO et affirme que tout est prêt |

**La demande de Léa :**
> « Vérifie la date, le périmètre et les blocages du lancement, puis prépare la correction du brief commercial. »

**Le résultat attendu :**
> Date cible approuvée : 10 novembre (décision du registre).
> Périmètre : export CSV ; SSO prévu en version 2.
> Lancement encore bloqué par la recette CSV (ticket QA).
> Correction du brief commercial préparée, avec un diff et la source de chaque changement.

---

## 3. Ce qui fait foi : les types d'information

C'est la difficulté centrale, et ce qui rend le produit crédible.

| Type | Exemple | Fait foi ? |
|---|---|---|
| Proposition | « On pourrait décaler au 12 novembre. » | Non |
| Décision approuvée | « J'approuve le report », par une personne habilitée | Oui, sur son sujet |
| Observation | « Le test CSV a échoué. » | Oui, comme constat |
| Information historique | Une ancienne décision remplacée par une nouvelle | Non, conservée pour l'historique |
| Déclaration de travail en cours | « Je rédige le brief avec le SSO. » | Non, c'est un état à surveiller |

**Règles d'autorité :**
1. Une décision approuvée par une personne habilitée fait foi sur son sujet (date, périmètre).
2. Un message plus récent n'annule pas une décision approuvée.
3. Deux décisions applicables et incompatibles produisent un **conflit à arbitrer**. Le système ne choisit jamais la dernière arrivée.
4. Les habilitations sont vérifiées par le backend (table des rôles), jamais par le texte d'un message. « Je suis le responsable » dans un message ne donne aucun droit.
5. Une date validée ne signifie pas que le lancement est prêt : il faut aussi que les blocages soient levés.
6. Une information venant d'un autre projet est ignorée. Une source réingérée en double ne crée pas de doublon.

---

## 4. Ce que fait le système

1. **Retrouver** les informations pertinentes dans les quatre sources (via Zetaris).
2. **Identifier les contradictions** sur la date, le périmètre et l'état de préparation.
3. **Appliquer les règles d'autorité.**
4. **Vérifier les conditions restantes** (blocages ouverts).
5. **Préparer la correction** du livrable périmé, avec un diff et les sources.
6. **Publier une nouvelle version de l'état du projet**, récupérable par l'IA de n'importe quel membre.
7. **Suivre l'avancement de chaque membre** (ce sur quoi il travaille, déclaré depuis son IA via MCP) et **détecter les travaux contradictoires** avant qu'ils ne produisent un livrable. Exemple : Sarah ajoute le SSO au brief pendant que Hugo le retire du périmètre ; les deux sont prévenus, et le manager reçoit un arbitrage.
8. **Résumer pour le manager** : décisions validées, blocages, avancement par membre, conflits en attente.

---

## 5. Scénarios de test

Les cinq premiers viennent du kit ; le sixième porte notre différenciation.

| # | Scénario | Résultat attendu |
|---|---|---|
| S1 | État normal | Date 10 novembre, périmètre CSV, SSO en v2, blocage QA, correction du brief |
| S2 | Nouvelle décision autorisée : report au 12 novembre | Le second client MCP récupère la nouvelle date, la nouvelle version et ses sources |
| S3 | Deux décisions contradictoires applicables | Conflit escaladé, aucune des deux n'est appliquée seule |
| S4 | Information venant d'un autre projet | Ignorée |
| S5 | Réingestion d'un doublon | Pas de doublon dans l'état |
| S6 | Deux membres travaillent sur des choses contradictoires | Conflit détecté, les deux prévenus, arbitrage proposé au manager |

Le kit annonce 14 cas de test, dont : bonne date et bon périmètre, maintien du blocage QA, correction du brief, reprise par un second client, escalade d'un conflit, rejet d'une écriture non autorisée ou fondée sur une version périmée, conservation de l'historique et des preuves. **Les résultats attendus sont séparés des sources lues par les agents** : le résultat est calculé à partir des données, les attendus servent seulement à évaluer.

Contrôle anti-triche : changer une date juste avant une répétition. Les deux clients doivent retrouver la nouvelle valeur.

---

## 6. Les données et Zetaris

### Pourquoi des données synthétiques
Les messages, tickets et décisions internes d'une équipe ne sont jamais publics. Pour tester la cohérence d'un système, un petit corpus synthétique est même préférable : on connaît les réponses attendues et on provoque exactement les situations voulues. Les règles officielles l'autorisent (§11.1, « synthetic or simulated data, clearly identified »).

### Comment les données arrivent sur internet, puis dans Zetaris
Zetaris ne lit pas un fichier local : il lit une URL (API REST en GET) ou un fichier sur un stockage accessible (S3). D'où trois voies :

| Voie | Contenu | Rôle | Statut |
|---|---|---|---|
| **A. Corpus publié dans notre repo GitHub** | Les 40 enregistrements du kit (8 documents, 16 messages, 10 tickets, 6 décisions), en JSON de la forme `{"records": [...]}`, servis par jsDelivr à partir du repo | Source principale, stable et reproductible | À tester dans Zetaris (repo public requis) |
| **B. API locale du kit** | Les mêmes sources, servies par une petite API sur ta machine ; Zetaris (dans Docker) la joint via `host.docker.internal` | Démo en direct : on ajoute une décision, Zetaris la relit (une table REST relit sa source à chaque requête, sauf si on la met en cache) | À tester |
| **C. Mode réel (option)** | Un vrai projet open source via l'API publique de GitHub : issues (tickets), pull requests, milestones (dates) | Montrer que le système marche aussi sur des données réelles, sans contradictions contrôlées | Non testé ; l'API de recherche renvoie un objet contenant un tableau `items`, forme compatible avec Zetaris ; débit limité sans authentification |

**Contraintes Zetaris confirmées par le repo `D:\zetaris-platform\getting-started`** : une table REST correspond à une URL fixe en GET ; le JSON doit être un objet contenant un tableau (un tableau à la racine n'est pas confirmé) ; une table REST rappelle sa source à chaque requête sauf `CACHE TABLE` ; aucune écriture dans Zetaris n'est vérifiée.

**Conséquence :** Zetaris est le système de lecture des sources de l'entreprise. Ce que les membres déclarent via MCP (travail en cours, propositions) et l'état versionné du projet vivent dans le World Model, pas dans Zetaris.

---

## 7. Technologies sponsors

| Technologie | Rôle concret |
|---|---|
| **Zetaris** | Expose les quatre sources comme des tables ; l'analyste les interroge en SQL (par sujet, date, statut) |
| **Meterless World Model** | État partagé du projet, fondé sur des événements : observations, décisions, travail en cours de chaque membre, versions, historique. Il demande une implémentation et une suite de conformité (repli : H-MEM) |
| **Meterless Nightshift** | Fournisseur IA principal de tous les appels (provider déjà codé dans `agent/llm.py`) |
| **NVIDIA Nemotron** | Les agents analyste et contrôleur, via Nightshift ; le modèle est journalisé pour chaque requête |

---

## 8. Démo (cible : 3 min 45)

| Temps | Scène |
|---|---|
| 0:00–0:20 | Le problème : le brief commercial annonce une mauvaise date, un mauvais périmètre et un « tout est prêt » injustifié |
| 0:20–1:15 | Léa lance la vérification ; l'analyste interroge Zetaris ; le contrôleur vérifie les décisions et le blocage QA |
| 1:15–1:45 | Le diff du brief apparaît, avec la source de chaque changement |
| 1:45–2:30 | Le moment coordination : Hugo (Cursor) déclare retirer le SSO pendant que le brief le réintroduit ; le conflit est détecté, les deux sont prévenus, Marc voit l'arbitrage dans la vue manager |
| 2:30–3:10 | Une nouvelle décision autorisée reporte au 12 novembre ; dans un second client MCP, le contexte récupéré a la nouvelle date, la nouvelle version et ses sources |
| 3:10–3:45 | Les preuves : requêtes Zetaris, conformité du World Model, modèle Nemotron par requête, traces des agents ; les limites |

Il faut nommer les clients réellement utilisés. Deux panneaux de notre propre application ne sont pas une intégration entre deux IA.

---

## 9. Questions ouvertes pour l'architecture

À trancher dans le schéma d'architecture ([architecture.md](architecture.md)) :
1. Combien d'agents LLM, et lesquels ? Proposition de départ : un analyste, un contrôleur, et un orchestrateur classique (code) qui applique les droits et les versions.
2. Qui décide de l'enchaînement : le code (workflow) ou le modèle (agent) ? À quels endroits ?
3. Comment l'avancement de chaque membre est-il capté : déclaration explicite via un outil MCP, ou déduction à partir des sources ?
4. Comment détecter un conflit : clés structurées (sujet, attribut, valeur), jugement d'un LLM, ou les deux ?
5. Quel niveau d'autonomie : l'agent propose et l'humain valide, ou l'agent boucle sous contrôles ?
6. Qu'est-ce qui vit dans Zetaris, et qu'est-ce qui vit dans le World Model ?
7. Quels outils MCP exposer ? Proposition de départ : récupérer le contexte, consulter les preuves, proposer une mise à jour, déclarer son travail en cours.
8. World Model seul, ou repli sur H-MEM si son implémentation prend trop de temps ?
9. Vue manager : quelle forme minimale (page en lecture seule) ?

---

## 10. Hors périmètre

- Synchroniser automatiquement les mémoires natives des assistants : MCP expose des outils que les clients appellent, il ne synchronise rien tout seul.
- Une vraie intégration ChatGPT : elle exige un serveur MCP distant en HTTPS.
- Un système d'authentification complet : une table de rôles suffit.
- Écrire dans Zetaris.

---

## 11. Le kit de démonstration

Le kit (`kit-demo-atlas.zip`) a été produit par l'autre analyse : cadrage, script de démo, architecture proposée, données, attendus et une petite API locale. Selon elle, l'intégrité des données et l'API sont vérifiées ; l'agent, MCP et les sponsors restent à faire. **Il n'a pas encore été relu ici.** Le déposer dans `external/kit-demo-atlas/` (ignoré par git) ; il sera relu entièrement avant toute exécution, puis les données seront reprises dans `data/sample/`.
