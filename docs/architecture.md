# Architecture — brouillon

**État : brouillon de travail, encore loin de l'architecture finale.** Rédigé par l'équipe le 27 octobre 2026. Il a été complété le même jour avec les propositions A à G de la première revue, puis H à Q de la deuxième revue : briques 4 et 5, orchestrateur, placement des mémoires et des engines ; puis R à T de la troisième revue : brique 7, remontées et interface du manager (voir la fin du document). Notes manuscrites d'origine : [architecture-notes/](architecture-notes/) (page 1 : suivi des décisions ; page 2 : avancement par membre ; page 3 : remontées au manager).

Principes suivis : [reference/guide-architecture-agentique.md](reference/guide-architecture-agentique.md). Cas d'usage : [use-case-atlas.md](use-case-atlas.md). Critères du jury : [strategie/prompt-jury.md](strategie/prompt-jury.md).

**Track retenu : 03 — Reasoning Architecture** (proposition G) : l'utilisateur principal est le manager, et le système transforme données et mémoire en décisions et en actions (alertes, corrections, réunions).

---

## Vue d'ensemble fonctionnelle

Ce que fait le système, de bout en bout, et ce qui est déjà codé (état au 27/10, 11:00 UTC). Le détail des boucles et des branchements est dans la section 3.

```mermaid
flowchart TD
  subgraph IN["Entrées"]
    SRC["Sources de l'entreprise<br/>messages, réunions, briefs,<br/>tickets, registre, tâches"]
    COL["Collaborateurs et leur IA<br/>Claude, Cursor..."]
    MAN["Manager ou personne habilitée<br/>son IA avec le skill manager"]
  end

  ZET[("Zetaris<br/>sources en SQL, lecture seule")]

  subgraph SYS["Système, piloté par l'orchestrateur"]
    B1["Brique 1 — Contexte fiable<br/>extraire, qualifier, trancher, contrôler"]
    B2["Brique 2 — Avancement<br/>classer chaque tâche"]
    B4["Brique 4 — Livrables<br/>repérer et corriger les passages périmés"]
    B5["Brique 5 — Réunions<br/>trier, juger, apprendre des verdicts"]
    B7["Brique 7 — Remontées<br/>règles R1 à R7, point périodique"]
    AM["Agent manager<br/>rédaction"]
  end

  subgraph MEM["État et mémoires"]
    WM[("World Model<br/>état courant du projet")]
    HM[("H-MEM<br/>journée, projet, organisation")]
  end

  subgraph OUT["Sorties"]
    AL["Alertes par membre"]
    DIFF["Diff du livrable<br/>avec ses sources"]
    REC["Recommandation de réunion<br/>ou message ciblé"]
    REP["Point périodique, remontées P1 et P2,<br/>rapport à la demande"]
  end

  SRC --> ZET
  ZET --> B1
  ZET --> B4
  COL -->|"report_progress, MCP"| B1
  B1 -->|"seul écrivain"| WM
  B1 --> HM
  WM --> B2
  WM --> B4
  B2 -->|"signaux de coordination"| B5
  HM -->|"précédents, Orion"| B5
  B1 --> AL
  B2 --> AL
  B4 --> DIFF
  B5 --> REC
  AL -->|"get_alerts, MCP"| COL
  B1 -->|"escalades"| B7
  B2 -->|"constats"| B7
  B4 -->|"diff en attente"| B7
  B5 -->|"recommandation"| B7
  WM -->|"nouvelle version"| B7
  B7 --> AM
  MAN -->|"verdict"| B5
  MAN -->|"question, MCP ou POST /run"| AM
  WM --> AM
  HM --> AM
  AM --> REP
  B7 -->|"exceptions"| REP
  REP -->|"récupéré par MCP"| MAN
  REC --> REP

  classDef done fill:#c8e6c9,stroke:#2e7d32,color:#000
  classDef partial fill:#ffe0b2,stroke:#ef6c00,color:#000
  classDef todo fill:#eeeeee,stroke:#9e9e9e,color:#000
  class B1,B2,AL,ZET,HM partial
  class B4,B5,B7,AM,WM,DIFF,REC,REP todo
```

| Couleur | Signification | Composants |
|---|---|---|
| Orange | En partie fait | Brique 1 : règles d'autorité et conflits codés et testés, agents à faire. Brique 2 : classement codé, outil MCP et cas S6 à faire. Alertes : boîtes codées, outils MCP à faire. Zetaris : connexion vérifiée, sources à enregistrer. H-MEM : conformité au vert (13/13), intégration à faire |
| Gris | À construire | Briques 4, 5 et 7, agent manager, orchestrateur, World Model, serveur MCP, `POST /run` |

## 1. Objectif, décision, action
Quelle décision le système aide-t-il à prendre, et quelle action en découle ?
Le système aide à gérer la cohérence dans le travail entre différentes personnes utilisant plusieurs modèle d'IA différentes sur leur PC dans un projet d'entreprises. Il alerte si jamais une personne fait un travail qui a été rendu obsolète par une décision qui a été prise par un autre colaborateur ou une contrainte technique qui est survenu. Il gère aussi généralement l'ensemble des informations relative a un projet ( quelle est la répartition des tâches, quel est le projet en question, quelles sont les deadlines, quelles sont les postes de chacun, quelle est l'avancement de chaque tâches ) et peut en ressortir des informations pertinentes pour la personne en charge du projet ou le manager de l'équipe ( ce système s'adapte donc aussi bien à la gestion d'une équipe par un manager qu'a la réalisation d'un projet cadré, avec chef de projet etc... ). Les informations pertinentes qu'il ressort concerne aussi bien un transfert d'information horizontal ( d'un collaborateur à un autre collaborateur par exemple ), que vertical ( le harness constate une irrégularité ou un problème quelque part dans le projet, remonte l'information jusqu'au manager pour le prévenir ). C'est également lui qui, par le suivis qu'il fait de l'avancé du projet ou du travail de chacun, planifie les réunions lorsqu'il est pertinent et utile d'en faire une pour l'avancer du projet ( l'idée est de limiter le nombre de réunion et de n'avoir que des réunions qui soient utile ). Le système stock également à différentes échelles de mémoire les avancées du projet et garde toutes les données de base qu'il peut récolter ( compte rendu de réunion par exemple, historique des informations d'un projet une fois le projet terminé etc... avec donc des mémoires à plusieurs échelles : mémoire sur le projet en cours, la journée de travail etc... et mémoire de l'ensemble des projets qui ont été fait )
- Utilisateur principal : le manager 
- Entrée (exemple de requête) : Fais moi un compte rendu de l'avancé du projet "X", de ce que chacun a fait, et de savoir si oui ou non nous allons suivre les deadlines que nous avons fixé. Si ce n'est pas le cas explique moi pourquoi. 
- Sortie (format, contenu) : Rapport détaillé qui répond à la question qui a été formulé par le manager. Peut aussi bien prendre la forme d'un rapport écrit que d'un rapport avec une analyse de donnée ou autre ainsi que des recommandations sur ce qui doit être fait si besoin. 

**Point d'entrée** (proposition F) : cette requête du manager est l'entrée principale du système, exposée par `POST /run` (entrée et sortie structurées). C'est ce que les juges appelleront.

**Fonctionnement sans N+1** (proposition O) : le système doit aussi marcher sur une équipe horizontale. La « personne habilitée » (arbitrage, escalade, validation d'une réunion) est lue dans la table des rôles, sujet par sujet. Sans manager ni chef de projet, les recommandations et les escalades vont dans les boîtes d'alertes des membres concernés. Pour la démo, le manager reste l'utilisateur principal (D7).

## 2. Composants
Pour chaque composant : agent LLM ou code déterministe ? Le jury pénalise « un agent avec plusieurs étiquettes ».

L'architecture est découpée en **briques**, une par capacité du cas d'usage (numérotées comme les capacités de [use-case-atlas.md](use-case-atlas.md)). La capacité 3, la coordination, n'a pas de brique à elle : elle est portée par les alertes de la brique 1 et par les cas « obsolète » et « contradiction entre membres » de la brique 2.

| Brique | Capacité | Agents LLM | Code déterministe |
|---|---|---|---|
| 1 — Contexte fiable | Suivi des décisions et de l'état du projet | Extracteur, agent de mise à jour, contrôleur (partie LLM) | Règles d'autorité, contrôles du contrôleur, notification |
| 2 — Avancement par membre | Suivi de chacun, coordination | Aucun | Validation du rapport MCP, classement |
| 4 — Correction des livrables | Action sur les livrables | Rédacteur (l'extraction réutilise l'extracteur de la brique 1) | Comparaison, validateur du diff |
| 5 — Recommandation de réunion | Réunions utiles | Analyste de réunion | Signaux, score, choix du canal, calibration |
| 7 — Remontées et vue manager | Vue manager, remontées automatiques | Aucun (la rédaction revient à l'agent manager) | Règles R1 à R7, routage, dédoublonnage, boîte de remontées, point périodique, contrôle du rapport |
| Agent manager | Rédaction pour le manager | Agent manager | — |
| Orchestrateur | Exécution d'un run | Aucun | Enchaînement, déclenchements, limites, traces |

Au total : **six agents LLM**, chacun avec une seule mission. Le reste est en code.

### Brique 1 — Contexte fiable (suivi des décisions)
Bilan de la brique : 1 capacité, l'état du projet (World Model), la mémoire des décisions (H-MEM), 3 agents, 1 algorithme.

**Principe (proposition H) : le LLM qualifie, le code tranche.** L'agent de mise à jour reste le point d'entrée unique de toute information qui peut modifier l'état du projet. Il compare l'entrée avec ce qui a déjà été décidé, fait et prévu, et propose la mise à jour. Mais la question « est-ce que ça fait foi ? » n'est pas laissée à son jugement. Elle se déduit, par des règles en code ([agent/decisions.py](../agent/decisions.py)), du type d'information, de l'habilitation de l'auteur (table des rôles) et des conflits. Sinon, les règles d'autorité vivraient à deux endroits (le prompt et le code), qui finiraient par diverger. Un LLM aurait par exemple tendance à préférer le message le plus récent, ce que la règle 2 du cas d'usage interdit.

| Composant | Type (LLM / code) | Rôle | Entrées | Sorties | Modèle |
|---|---|---|---|---|---|
| Extracteur | LLM | Extrait les informations d'un texte, selon le type de source. Pour une réunion, il rédige aussi le compte rendu ; pour le canal commun (Slack ou autre), il ne garde que les décisions (deadlines, etc.), en tenant compte du contexte déjà connu ; pour un livrable (brique 4), il relève ses affirmations. Fusion des deux agents du brouillon manuscrit (proposition A) | Texte de la source (lu dans Zetaris), type de source, état du projet | Compte rendu (réunion), informations candidates au format ci-dessous | Nemotron via Nightshift (à préciser) |
| Agent de mise à jour | LLM | Point d'entrée unique de ce qui peut changer l'état : sorties de l'extracteur, rapports d'avancement remontés par MCP (brique 2), tickets. ① rattache chaque information au bon sujet et au bon attribut, et à la décision qu'elle remplacerait (rapprochement) ; ② la qualifie selon les **types d'information** du cas d'usage (proposition, décision, constat, déclaration de travail, avancement…) ; ③ propose la mise à jour de l'état, avec ses preuves | Informations candidates, état du projet (World Model), historique des décisions (H-MEM) | Proposition de mise à jour structurée, avec ses preuves | Nemotron via Nightshift (à préciser) |
| Contrôleur (proposition B) | Règles déterministes, puis LLM | **D'abord en code** : schéma, habilitation de l'auteur (table des rôles, jamais le texte d'un message), conflit avec une décision en vigueur, appartenance au projet (S4), doublon par référence de source (S5). **Puis le LLM** : les preuves citées soutiennent-elles la proposition ? Accepte, demande **une révision au plus** à l'agent de mise à jour, ou **escalade vers la personne habilitée** | Proposition, état du projet, rôles | Mise à jour validée, demande de révision, ou escalade | Nemotron via Nightshift (à préciser) |
| Écriture de l'état | Code | **Seul écrivain** de l'état du projet (principe 6 du guide) : applique la mise à jour validée dans World Model et l'enregistre dans H-MEM | Mise à jour validée | Nouvelle version de l'état | — |
| Algorithme de notification | Code déterministe | ④ détermine les personnes affectées par la modification et dépose une alerte dans leur **boîte d'alertes** (proposition D) | Mise à jour validée, rôles et tâches de chacun | Alertes par collaborateur | — |

**Classification des décisions** (utile aussi à la brique 2) :
- deadline sur un livrable ;
- tâche donnée à X personnes, avec deadline.

### Brique 2 — Avancement par membre
Elle s'appuie sur l'état du projet tenu par la brique 1 (décisions en vigueur, tâches, rôles).

**Principe (proposition I) : le rapport arrive déjà structuré, donc la brique 2 n'a pas d'agent LLM.** Le contrat, c'est le **schéma de l'outil MCP** `report_progress`. Tout client MCP le reçoit (Claude, Cursor…), et le serveur rejette un rapport invalide avec un message qui dit quoi corriger : l'IA du collaborateur se corrige seule. Le **skill** dit seulement à l'IA quand et comment faire son rapport (en fin de session de travail, en déclarant les valeurs sur lesquelles le travail repose). C'est donc l'IA du collaborateur qui fait la structuration, et la comparaison avec ce qui aurait dû être fait est un algorithme ([agent/progress.py](../agent/progress.py)).

**Le rapport est aussi une source pour la brique 1** (proposition J). L'avancement et le travail déclaré modifient l'état du projet : ils passent par l'agent de mise à jour et le contrôleur, comme toute autre source, pour qu'il n'y ait qu'un seul écrivain. Les champs structurés (avancement d'une tâche par son propre responsable) passent les contrôles en code sans appel LLM ; seul le commentaire libre passe par l'agent de mise à jour.

| Composant | Type (LLM / code) | Rôle | Entrées | Sorties | Modèle |
|---|---|---|---|---|---|
| Skill de rapport d'avancement | Skill installé sur l'IA de chaque collaborateur, sur son PC | Dit à l'IA quand faire son rapport et quoi déclarer ; à chaque rapport, affiche les alertes qui l'attendent (proposition D) | Travail du collaborateur | Appel à `report_progress` ; affichage des alertes | IA du collaborateur |
| Outil MCP `report_progress` | Code | Valide le rapport contre le schéma, le transmet à la brique 1, rend les alertes en attente | Rapport structuré (section 7) | Accusé de réception, ou erreur explicite ; alertes | — |
| Algorithme de classement | Code déterministe | Classe la situation de chaque tâche (voir ci-dessous) à partir de l'état du projet | Tâches, derniers rapports, décisions en vigueur, tickets | Constats par membre ; **signaux de coordination** pour la brique 5 | — |

**Les cas de l'algorithme de classement :**
1. **Pas de problème** : une note datée (date, heure) indique que tout est en ordre pour cette personne, qui suit sa deadline.
2. **Retard** : même chose, plus un rapport, et l'information remonte.
3. **Travail obsolète** par rapport à une décision prise : une alerte est déposée dans la boîte du collaborateur pour le lui signaler.
4. **Signal de coordination** (propositions C, puis K) : une même décision rend obsolète le travail de deux personnes ou plus, ou une tâche en retard bloque celle d'un autre membre. Ce cas ne rédige plus de réunion lui-même : il émet un **signal** que la brique 5 note. Une seule brique recommande des réunions (un seul écrivain).
5. **Contradiction entre membres** (proposition L, scénario S6) : deux membres déclarent des valeurs incompatibles sur un même sujet (Hugo retire le SSO, Sarah l'annonce). S'il existe une décision en vigueur, celui qui s'en écarte est en cas 3. Sinon, c'est un conflit à arbitrer : les deux sont prévenus et l'escalade part vers la personne habilitée. **À coder** : aujourd'hui, `progress.py` compare chaque membre à une décision, jamais deux membres entre eux.

**Blocages** (proposition L, règle 5 du cas d'usage : une date validée ne veut pas dire que le lancement est prêt). Un ticket ouvert et bloquant, comme la recette CSV, est relié à la tâche ou au jalon qu'il bloque. Il compte comme un constat dans l'état du projet, et le classement le prend en compte. **À modéliser.**

### Brique 4 — Correction des livrables
Elle traite un livrable comme un rapport d'avancement écrit en texte libre : le même contrôle « obsolète », appliqué à un document (proposition M). C'est la scène 1:10–1:35 de la démo et la demande de Léa.

| Composant | Type (LLM / code) | Rôle | Entrées | Sorties | Modèle |
|---|---|---|---|---|---|
| Extraction des affirmations | LLM (l'extracteur de la brique 1, type de source « livrable ») | Relève les affirmations du livrable au même format que les rapports : sujet, attribut, valeur (par exemple `atlas-launch / launch_date = 3 novembre`, `état = prêt`) | Livrable lu dans Zetaris | Affirmations, avec leur passage dans le texte | Nemotron via Nightshift (à préciser) |
| Comparaison | Code déterministe | Compare chaque affirmation aux décisions en vigueur et aux constats (blocages ouverts) | Affirmations, état du projet | Passages périmés, chacun avec la décision ou le constat qui le contredit | — |
| Rédacteur | LLM | Réécrit **uniquement** les passages périmés | Livrable, passages périmés et leurs sources | Version corrigée | Nemotron via Nightshift (à préciser) |
| Validateur | Code déterministe | Vérifie que chaque changement cite une décision ou un constat, que rien n'est modifié hors des passages signalés et qu'aucune affirmation nouvelle n'apparaît. Demande **une révision au plus** au rédacteur, puis escalade | Livrable, version corrigée, passages signalés | Diff validé avec ses sources, ou escalade | — |

Le diff est déposé chez l'auteur du livrable et visible dans la vue manager. La source n'est jamais modifiée (Zetaris est en lecture, D4) : le système prépare, l'humain applique.

### Brique 5 — Recommandation de réunion
Notes manuscrites et tableau des déclencheurs de l'équipe (27/10), précisés par les propositions N et P. Trois étapes : un tri déterministe, un agent qui juge, et l'évaluation par l'humain.

**Étape 1 — Tri déterministe (code).** Les signaux viennent des briques 1 et 2 et des sources Zetaris ; la brique 5 ne redétecte pas les incohérences, déjà notifiées par les autres briques (conclusion des notes manuscrites). Les signaux sont regroupés en **réunions candidates** : un sujet et les personnes concernées. Le score se calcule par réunion candidate, pas pour le projet entier, sinon un simple mi-parcours déclencherait une réunion avec tout le monde.

| Déclencheur | Condition | Référence | Données | Démo |
|---|---|---|---|---|
| Temporel | Lancement de projet ou de phase ; mi-parcours de chaque phase ; jalon à J-x ; fin de livrable | Gersick | Échéances des tâches et jalons | Oui |
| Interdépendance | Dépendance réciproque entre 2 personnes ou plus, avec une modification récente d'un côté | Thompson, Van de Ven et al. | Dépendances des tâches, décisions récentes (cas 4 de la brique 2) | Oui |
| Blocage | Tâche bloquée par celle d'un autre depuis plus de N jours | Coordination | Dépendances et retards (cas 4 de la brique 2) | Oui |
| Dérive | Glissement du chemin critique au-delà d'un seuil ; changement de périmètre | Gestion de projet | Avancement attendu et réel ; décisions sur le périmètre | Version simple |
| Décision en attente | Décision impliquant plusieurs parties prenantes, non tranchée depuis N jours | Vroom & Yetton | Conflits ouverts (`conflicts()`) et leur date | Oui |
| Changement d'équipe | Arrivée d'un membre, changement de responsable | Socialisation | Historique de la table des rôles | Feuille de route |

Les **coûts** sont soustraits du score, comme dans la littérature sur la charge de réunions (Rogelberg, Perlow) : la charge de réunions de chaque participant cette semaine, l'atteinte aux plages de concentration et le nombre de participants requis. Les deux premiers demandent un agenda : soit une petite table d'agenda synthétique dans Zetaris, soit seulement le nombre de participants pour la démo.

**Choix du canal (proposition N).** L'équivocité (Daft & Lengel, synchronicité des médias) n'est pas un terme du score. Elle choisit le canal : les déclencheurs disent qu'il y a un problème de coordination, l'équivocité dit s'il faut un échange synchrone ou si un message suffit. Indicateur : un fil asynchrone qui dépasse N allers-retours sans décision enregistrée. C'est la règle du cas d'usage : une réunion seulement si l'échange synchrone est plus efficace qu'un message, sinon le système prévient directement les personnes.

**Déclenchement.** Le tri tourne à chaque changement de l'état du projet (une nouvelle version dans World Model) et dans chaque run. Il est en code, donc peu coûteux. L'agent de l'étape 2 n'est appelé que pour une réunion candidate au-dessus du seuil, nouvelle ou dont les signaux ont changé.

**Étape 2 — Analyste de réunion (LLM, lecture seule).** Il est appelé après le tri, sur une réunion candidate. Il n'a que des outils de lecture, avec un nombre d'appels limité.
- **Besoin évident** : il rédige la recommandation (participants, durée, raison, preuves, ordre du jour) et la soumet à la personne habilitée.
- **Doute** : il creuse les données du projet (qui a fait ou fini quoi, ce qu'une réunion apporterait) et consulte les **précédents** dans H-MEM : verdicts sur des réunions semblables, enseignements des projets passés (le projet Orion, scénario S9).
- Sortie, une parmi trois : `réunion`, `message ciblé` (déposé dans les boîtes d'alertes) ou `rien`, toujours avec ses raisons.

**Étape 3 — Évaluation et calibration (proposition P).** La personne habilitée accepte ou refuse, et dit si la réunion a été utile. Ce verdict est enregistré dans H-MEM (retour `helpful` ou `not_helpful`, qui modifie la confiance des précédents) et sert à l'étape 2 des fois suivantes : c'est la mémoire des décisions passées qui change le résultat, le signal fort du track 03. Les poids du tri ne sont **jamais modifiés par un agent** : un ajustement est calculé en code à partir de l'historique des verdicts, présenté à l'humain sous forme de diff, appliqué seulement après validation, et versionné pour pouvoir revenir en arrière. Pour la démo : un verdict enregistré et un ajustement montré ; le reste en feuille de route.

### Brique 7 — Remontées au manager et vue manager
Document de l'équipe et notes manuscrites du 27/10 ([page 3](architecture-notes/page-3-remontees.jpg)), complétés par les propositions S et T de la troisième revue. Capacités 6 et 7 de [use-case-atlas.md](use-case-atlas.md) : donner au manager une vue d'ensemble, et le prévenir de ce qui compte sans qu'il ait à demander. Scénarios couverts : S3, S6, S7, S8.

Bilan de la brique : 2 capacités, **0 nouvel agent LLM** (on reste à six : la rédaction revient à l'agent manager), 1 algorithme de règles, 1 boîte de remontées, 1 skill manager, 1 contrôle en code sur le rapport.

#### Trois modes de remontée (proposition S)
| Mode | Quand | Contenu | Déclenché par | Démo |
|---|---|---|---|---|
| **A — Point périodique** | Chaque jour ouvré (ou tous les 2 à 3 jours) et un point hebdomadaire ; fréquence réglée par la personne habilitée | Tenue du planning, changements depuis le dernier point, remontées ouvertes, avancement par membre, pistes (voir ci-dessous) | Orchestrateur, run planifié | Oui, lancé par une commande ; la planification automatique est en feuille de route |
| **B — Exception** | Dès qu'une règle R1 à R7 se déclenche | Une remontée (format ci-dessous) | Règles en code, à chaque nouvelle version de l'état | Oui : R1, R2, R4, R7 |
| **C — À la demande** | Quand le manager pose une question | Rapport qui répond à sa question (section 1) | Skill manager, puis outil MCP, puis agent manager (même logique que `POST /run`) | Oui |

**Le point périodique part toujours, même quand tout va bien** : c'est le suivi récurrent du projet. Il reste court quand rien ne dépasse les tolérances. **Les exceptions n'attendent pas le point** : elles entrent dans la boîte de remontées dès que la règle se déclenche, puis figurent en tête du point suivant et de chaque rapport.

#### Interface du manager : son IA, via MCP (proposition S)
Le manager est un utilisateur comme les autres, avec le rôle « manager » (ou « personne habilitée ») dans la table des rôles (proposition O). Il n'a pas d'application à part : il passe par son IA (Claude Desktop dans la démo), avec un **skill manager** qui appelle le serveur MCP.
- **Le skill** : à la première conversation de la journée, il récupère le dernier point périodique et les remontées ouvertes ; quand le manager pose une question, il appelle l'outil de rapport ; il présente toujours les remontées P1 en premier, et propose de les marquer (`traitée`, et un retour).
- **Récupéré, pas poussé** : un serveur MCP ne contacte pas le client (proposition D). Le point périodique est donc **produit** par un run planifié et **récupéré** par le skill. L'envoi par mail ou Slack d'un point bref est en feuille de route : la démo n'envoie aucun mail ([use-case-atlas.md](use-case-atlas.md), section 9).
- **Rôles** : les outils du manager sont réservés au rôle manager ou à la personne habilitée sur le sujet. Pour la démo, le rôle est déclaré dans la configuration du client MCP, sans authentification (une table de rôles suffit, section 9 du cas d'usage).
- **Option si le temps le permet** : le même point rendu en une page HTML statique, pour la vidéo.

#### Contenu du point périodique
| Partie | Contenu | Produit par |
|---|---|---|
| En-tête | « Dernière vérification : <date>, <n> tâches dans les tolérances, <m> remontées ouvertes » | Code |
| Remontées P1 ouvertes | Toutes, avec constat, écart, preuves et action attendue | Code (sélection) ; agent manager (formulation) |
| Tenue du planning | Pour chaque jalon : échéance, fin projetée (calcul de R1), écart, tâches qui le retardent | Code |
| Depuis le dernier point | Remontées P2 : décisions validées, livrables corrigés, réunions recommandées | Code |
| Avancement par membre | Une ligne par membre : tâches, avancement déclaré, cas du classement (brique 2) | Code |
| Pistes à envisager | Si un jalon dérive : options de replanification ou de répartition (décaler le jalon, réaffecter une tâche, sortir un élément du périmètre), chacune avec ses preuves | Agent manager, **présentées comme des pistes** : la décision reste au manager |

Les chiffres (dates projetées, écarts, avancement) sont calculés en code ; l'agent manager rédige et propose des pistes, il ne calcule rien (D13). Une optimisation automatique de la répartition des tâches (charge, compétences) est en feuille de route.

#### Principe : on n'interrompt le manager que pour l'exception, et c'est le code qui en décide
**Ce qui est prévu ne déclenche pas de remontée d'exception** : il est résumé dans le point périodique. La hiérarchie traite les exceptions ; le routinier est réglé par les plans et les règles (Galbraith, 1974). En gestion de projet, c'est le « management par exception » de PRINCE2 : le manager fixe des **tolérances**, et on ne lui remonte une situation que lorsqu'une tolérance est dépassée **en prévision**, pas une fois le dépassement constaté. L'attention du manager est la ressource rare (Simon ; Ocasio, 1997) : une alerte « tout va bien » la consomme pour rien.

**La décision de remonter est prise par des règles en code, jamais par un LLM** (prolongement de D13, « le LLM qualifie, le code tranche »). Trois raisons :
- **Les mauvaises nouvelles se perdent en remontant.** Les membres d'un projet hésitent à signaler un projet qui dérape (effet MUM, Smith, Keil & Depledge, 2001 ; silence organisationnel, Morrison & Milliken, 2000). Un agent qui « juge si c'est pertinent » reproduirait ce filtre de façon automatisée et invisible.
- **Le jugement qualitatif est déjà fait en amont.** Le contrôleur (brique 1) a qualifié les conflits et les escalades, le classement (brique 2) les retards et les contradictions, l'analyste (brique 5) les réunions. La brique 7 consomme des événements déjà qualifiés : elle n'a besoin que de seuils et d'une table de routage.
- **Le jury vérifie le code.** Une règle s'audite et se teste ; un prompt ne s'audite pas.

Le LLM n'intervient qu'en aval, pour la **forme** : l'agent manager existant rédige le point et les rapports à partir des remontées que le code a sélectionnées, et un contrôle en code vérifie qu'il n'en a omis aucune.

#### Composants
| Composant | Type (LLM / code) | Rôle | Entrées | Sorties | Modèle |
|---|---|---|---|---|---|
| Règles de remontée | Code déterministe | Évalue les règles R1 à R7 à chaque nouvelle version de l'état et à chaque run ; attribue un niveau P1, P2 ou P3 | Nouvelle version de l'état, constats de la brique 2, escalades du contrôleur, diffs de la brique 4, recommandations de la brique 5, tolérances du projet | Remontées candidates | — |
| Routage | Code déterministe | Désigne le destinataire : la **personne habilitée sur le sujet** (table des rôles), à défaut le manager ; sans N+1, les membres concernés (proposition O) | Remontée, table des rôles | Remontée adressée | — |
| Dédoublonnage et agrégation | Code déterministe | Une remontée par couple (règle, sujet) ; elle n'est réémise que si la situation **s'aggrave** (niveau supérieur, écart plus grand) ou après le délai de relance | Remontées candidates, remontées ouvertes | Remontées nouvelles ou mises à jour | — |
| Boîte de remontées | Code (seul écrivain) | Stocke les remontées ouvertes du manager ; même mécanique que les boîtes d'alertes ([agent/alerts.py](../agent/alerts.py)) : récupérées, pas poussées | Remontées adressées | Remontées ouvertes, vues, traitées | — |
| Point périodique | Code, puis agent manager | Assemble en code les parties du point (tableau ci-dessus), puis l'agent manager le rédige | Boîte de remontées, état, constats de la brique 2, date du dernier point | Point périodique, gardé pour être récupéré par le skill | Nemotron via Nightshift (à préciser) |
| Skill manager | Skill installé sur l'IA du manager | Récupère le point et les remontées, transmet les questions du manager, présente les P1 en premier, enregistre ses retours | Questions et retours du manager | Appels aux outils MCP du manager (section 7) | IA du manager |
| Agent manager | LLM (existant) | Rédige le point périodique et les rapports à la demande ; les remontées P1 ouvertes sont toujours en tête | Remontées, état, mémoires | Point, rapport | Nemotron via Nightshift (à préciser) |
| Contrôle du rapport | Code déterministe | Vérifie que chaque remontée P1 ouverte est citée (par son identifiant) dans le point ou le rapport ; sinon une révision au plus, puis ajout en code d'un bloc « Remontées non traitées » | Point ou rapport, remontées P1 ouvertes | Point ou rapport validé | — |
| Retour du manager | Code | Le manager marque une remontée : `utile`, `inutile`, ou **`trop tard`** (il l'a apprise ailleurs) ; enregistré dans H-MEM (mémoire du projet) | Verdict | Retour dans H-MEM ; proposition d'ajustement des tolérances | — |

#### Les règles de remontée
Chaque règle porte une référence, pour que le choix soit justifié devant le jury.

| # | Règle | Condition calculable | Niveau | Référence | Scénario |
|---|---|---|---|---|---|
| R1 | **Tolérance de délai dépassée en prévision** | Une tâche dont dépend un jalon ou un livrable a une date de fin projetée au-delà de l'échéance du jalon (voir le calcul ci-dessous) | P1 si le jalon est à moins de H jours, sinon P2 | PRINCE2 (tolérances, rapport d'exception), Galbraith | S7 (recette CSV) |
| R2 | **Décision hors délégation** | Escalade du contrôleur (brique 1) : conflit entre deux décisions approuvées (S3), contradiction entre membres sans décision en vigueur (S6), auteur non habilité | P1 | Galbraith (l'exception est ce que les règles ne couvrent pas) | S3, S6 |
| R3 | **Coordination latérale échouée** | Un signal de coordination (cas 4 de la brique 2) ou une alerte « obsolète » reste sans résolution après T jours : pas de nouvelle décision, pas de rapport corrigé | P2, P1 si R1 est aussi vrai sur le même sujet | Galbraith : d'abord les relations latérales, la hiérarchie ensuite | S7 |
| R4 | **Changement d'un engagement du manager** | Une décision validée modifie une date de jalon, le périmètre ou un responsable | P2 (P1 si le jalon est à moins de H jours) | Ocasio : pertinent = ce qui change les décisions du destinataire | S2, S8 |
| R5 | **Nouveau blocage sur le chemin critique** | Un ticket ouvert et bloquant est relié à une tâche dont dépend un jalon | P1 si le jalon est à moins de H jours, sinon P2 | Weick & Sutcliffe : sensibilité aux opérations, ne pas expliquer les anomalies ; règle 5 du cas d'usage | S1, S7 |
| R6 | **Silence** | Un membre avec une tâche active n'a envoyé aucun rapport depuis N jours ouvrés | P2 | Weick & Sutcliffe ; effet MUM : « pas de nouvelles » n'est pas « pas de problème » | Feuille de route |
| R7 | **Action préparée en attente de l'humain** | Un diff de livrable validé (brique 4) ou une réunion recommandée (brique 5) attend une décision | P2 | Le système prépare, l'humain décide (principe 7 du guide) | S1, S7 |

**Ce qui ne remonte pas en exception** (reste latéral, dans la boîte du membre, et apparaît seulement dans le point périodique) : un retard sans tâche dépendante et sans jalon touché ; un travail obsolète tant que la règle R3 ne s'est pas déclenchée ; une décision qui ne change ni date, ni périmètre, ni responsable.

**Calcul de la prévision (R1).** Simple et déterministe, pour la démo :
- avancement attendu d'une tâche = part du temps écoulé entre son début et son échéance ;
- date de fin projetée = aujourd'hui + (1 − avancement déclaré) × durée prévue de la tâche ;
- une tâche est en dépassement si sa date de fin projetée dépasse son échéance de plus de la **tolérance de délai** ;
- un jalon est en dépassement si une tâche dont il dépend (directement ou par transitivité) l'est. Les dépendances viennent de la vue graphe de World Model, ou du champ `depends_on` des tâches dans le repli JSON ; il faut ajouter une date de début aux tâches (`agent/progress.py`).

Une tâche bloquée par un ticket ouvert (R5) est projetée au-delà de son échéance tant que le ticket est ouvert.

**Tolérances.** Fixées par la personne habilitée, stockées dans l'état du projet, versionnées. Valeurs de départ proposées :

| Paramètre | Défaut | Sens |
|---|---|---|
| Tolérance de délai, jalon | 0 jour | Tout glissement projeté d'un jalon remonte |
| Tolérance de délai, tâche | 2 jours | En dessous, le retard reste latéral |
| H (horizon d'urgence) | 5 jours ouvrés | Passe une remontée de P2 à P1 |
| T (délai de résolution latérale) | 2 jours ouvrés | Au-delà, R3 se déclenche |
| N (silence) | 3 jours ouvrés | Au-delà, R6 se déclenche |
| Délai de relance d'une P1 non traitée | 1 jour ouvré | La P1 est réémise une seule fois, puis reste en tête du point |
| Fréquence du point périodique | 1 jour ouvré, plus un point hebdomadaire | Mode A |

#### Niveaux de priorité et canaux
| Niveau | Quand | Canal |
|---|---|---|
| **P1 — Exception** | Le manager (ou la personne habilitée) doit agir, et le temps ou l'irréversibilité presse | Boîte de remontées dès le déclenchement ; en tête du point périodique et de chaque rapport ; feuille de route : notification immédiate (mail, Slack) |
| **P2 — À connaître** | Changement qui touche ses engagements, ou action préparée qui attend sa validation, sans urgence | Partie « Depuis le dernier point » du point périodique |
| **P3 — Trace** | Tout le reste, dont les « tout va bien » | Résumé dans l'en-tête du point ; détail consultable dans H-MEM (mémoire de la journée) |

**Le « tout va bien » n'est pas une remontée d'exception, mais il figure dans le point périodique.** Les classements « ok » de la brique 2 sont des traces P3 : elles servent au système (une absence de rapport déclenche R6) et à la preuve. Pour le manager, elles se résument à **la ligne d'en-tête** du point. Cette ligne a de la valeur : le manager sait que l'absence d'alerte est vérifiée, pas un oubli.

#### Format d'une remontée
Dans le code, les noms de champs sont en anglais sans accent (`rule`, `level`, `subject`…), comme dans `agent/decisions.py`.

| Champ | Contenu |
|---|---|
| `id` | Identifiant stable, dérivé de (règle, sujet) pour le dédoublonnage |
| `règle` | R1 à R7 |
| `niveau` | P1, P2, P3 |
| `sujet` | Jalon, tâche, décision ou livrable concerné |
| `destinataire` | Personne habilitée sur le sujet (table des rôles) |
| `constat` | Phrase factuelle générée en code (pas de LLM), par exemple « Jalon lancement Atlas (10/11) : fin projetée de la recette CSV au 13/11, tolérance 0 jour » |
| `écart` | Valeur mesurée et tolérance, quand la règle en a une |
| `action_attendue` | `décider`, `valider` ou `information` |
| `preuves` | Identifiants des décisions, tâches, tickets, rapports et sources Zetaris |
| `statut` | `ouverte`, `vue`, `traitée` |
| `créée_le`, `mise_à_jour_le` | Dates |
| `retour` | `utile`, `inutile`, `trop tard`, ou vide |

Les preuves restent attachées : chaque résumé perd de l'incertitude en remontant (March & Simon parlent d'absorption d'incertitude), le manager doit pouvoir redescendre aux données brutes.

#### Flux de contrôle de la brique 7
```mermaid
flowchart TD
  WM[("État du projet<br/>nouvelle version")] --> R{"Règles R1 à R7<br/>code"}
  B1["Escalades du contrôleur<br/>brique 1"] --> R
  B2["Constats et signaux<br/>brique 2"] --> R
  B4["Diff validé<br/>brique 4"] --> R
  B5["Réunion recommandée<br/>brique 5"] --> R
  TOL[("Tolérances<br/>versionnées")] --> R
  R -->|"aucune règle"| P3["Trace P3<br/>H-MEM journée"]
  R -->|"règle déclenchée"| ROUT["Routage<br/>personne habilitée"]
  ROUT --> DED{"Dédoublonnage<br/>nouvelle ou aggravée ?"}
  DED -->|"non"| SKIP["Rien"]
  DED -->|"oui"| BOX[("Boîte de remontées<br/>seul écrivain")]
  CRON["Run planifié<br/>mode A"] --> PT["Point périodique<br/>assemblé en code"]
  BOX --> PT
  P3 -->|"ligne d'en-tête"| PT
  PT --> AM["Agent manager<br/>rédaction"]
  ASK["Question du manager<br/>mode C"] --> AM
  AM --> CHK{"Contrôle : toutes les P1<br/>ouvertes sont citées ?"}
  CHK -->|"non, 1 révision au plus"| AM
  CHK -->|"oui"| OUTM["Point ou rapport"]
  OUTM -->|"récupéré par MCP"| SKM["Skill manager<br/>IA du manager"]
  BOX -->|"mode B, récupéré par MCP"| SKM
  SKM --> FB["Retour : utile, inutile, trop tard"]
  FB --> HM[("H-MEM projet")]
  HM -->|"proposition d'ajustement,<br/>validée par l'humain"| TOL
```

#### Garde-fous
- Aucun agent ne peut supprimer, rétrograder ou masquer une remontée : seul le manager la marque `traitée`.
- Le point et les rapports de l'agent manager sont contrôlés en code : toute P1 ouverte y figure.
- Le niveau d'une remontée ne peut que monter tant qu'elle est ouverte.
- Les tolérances ne sont modifiées qu'après validation humaine, comme les poids de la brique 5 (proposition P) : un ajustement est calculé en code à partir des retours, présenté sous forme de diff, versionné.
- La surcharge se traite par agrégation, jamais par suppression : au-delà de 3 P1 ouvertes, elles sont regroupées par jalon dans un seul bloc, mais toutes restent listées.
- Les pistes de replanification sont des propositions : aucune tâche n'est réaffectée et aucun jalon n'est déplacé sans décision enregistrée de la personne habilitée.

#### Évaluation
- **Métrique principale : les remontées `trop tard`** (le manager l'a appris par un autre canal). Ce sont les faux négatifs, plus graves qu'une remontée inutile.
- Métrique secondaire : la part de remontées `inutile`, pour ajuster les tolérances.
- Tests unitaires (même style que `tests/test_progress.py`) :
  - S1, état normal : aucune P1 de R1 hors recette CSV, une ligne d'en-tête « dernière vérification » ;
  - S7 : la recette CSV en retard donne une P1 R1 sur le jalon de lancement, avec les preuves ;
  - S3 : deux décisions approuvées incompatibles donnent une P1 R2, adressée à la personne habilitée ;
  - S8 : une décision qui change la date donne une P2 R4, présente dans le point suivant ;
  - point périodique : il est produit même sans aucune remontée, avec la ligne d'en-tête et la tenue du planning ;
  - dédoublonnage : deux runs sur le même état ne créent qu'une remontée ; une aggravation la met à jour ;
  - contrôle du rapport : un rapport qui omet une P1 est rejeté.

#### Faisabilité avant la clôture (proposition T)
Estimations du 27/10 à 17:00, avec Claude qui code ; à confirmer en construisant.

| Élément | Estimation | Dépend de | Verdict |
|---|---|---|---|
| Règles R2 et R4, routage, dédoublonnage, boîte de remontées (réutilise `agent/alerts.py`), ligne d'en-tête, tests | ~1 h | `agent/decisions.py`, `agent/alerts.py` (existants) | Démo |
| R1 (prévision) et tenue du planning | ~45 min | Date de début des tâches, corpus | Démo |
| Point périodique (mode A), lancé par une commande | ~30 min en plus de l'agent manager | Agent manager | Démo |
| Skill manager et outils MCP du manager | ~30 min en plus du serveur MCP | Serveur MCP | Démo |
| Contrôle du rapport | ~20 min | Agent manager | Démo |
| R7 | ~15 min | Sorties des briques 4 et 5 | Démo si ces briques sont livrées |
| R5 (blocage) | ~30 min | Tickets bloquants modélisés (nécessaires de toute façon pour S1) | Démo si les tickets sont modélisés |
| R3, R6 | ~45 min | Historique daté des alertes et des rapports | Si le temps le permet |
| Retour `utile`, `inutile`, `trop tard` dans H-MEM | ~20 min | D11 | Enregistrement seulement |
| Ajustement des tolérances, planification automatique, mail et Slack, optimisation de la répartition, page HTML | — | — | Feuille de route (la page HTML si le temps le permet) |

Le cœur de la brique 7 (R1, R2, R4, routage, dédoublonnage, boîte, point périodique, skill) représente environ 3 h de construction. Il ne tient dans le temps restant que si la brique 5 est réduite au minimum : c'est l'objet du périmètre minimal, à trancher juste après.

#### Lien avec les autres briques
- La brique 7 ne décide pas des réunions : une recommandation de la brique 5 est une remontée R7 parmi d'autres.
- Elle ne redétecte rien : elle lit les sorties des briques 1, 2, 4 et 5 et l'état du projet.
- Les règles R1 et R5 utilisent les dépendances des tâches, déjà prévues pour la brique 5.

#### Ce qu'on coupe si le temps manque
1. R6 (silence), R3 et le délai de relance.
2. La boucle de retour et l'ajustement des tolérances (on garde l'enregistrement du retour).
3. Le contrôle du rapport de l'agent manager (on garde les P1 ajoutées en code en tête du rapport).
4. Les pistes de replanification dans le point périodique (on garde la tenue du planning calculée en code).

On garde toujours : R1, R2, R4, le routage, le dédoublonnage, la ligne d'en-tête, le point périodique et le skill manager.

#### Références (vérifiées le 27/10/2026)
- Galbraith, J. R. (1974). Organization design: An information processing view. *Interfaces*, 4(3), 28-36.
- AXELOS, PRINCE2 : principe « manage by exception », tolérances par dimension, rapport d'exception.
- Simon, H. A. (1971). Designing organizations for an information-rich world (l'information consomme l'attention).
- Ocasio, W. (1997). Towards an attention-based view of the firm. *Strategic Management Journal*, 18(S1), 187-206.
- Smith, H. J., Keil, M., & Depledge, G. (2001). Keeping mum as the project goes under. *Journal of Management Information Systems*, 18(2), 189-227.
- Morrison, E. W., & Milliken, F. J. (2000). Organizational silence. *Academy of Management Review*, 25(4), 706-725.
- Weick, K. E., & Sutcliffe, K. M. *Managing the Unexpected* (cinq principes des organisations à haute fiabilité).
- March, J. G., & Simon, H. A. (1958). *Organizations* (absorption d'incertitude).

### Agent manager (proposition F, recentré par les propositions K et S)
| Composant | Type (LLM / code) | Rôle | Entrées | Sorties | Modèle |
|---|---|---|---|---|---|
| Agent manager | LLM | Une seule mission : rédiger pour le manager. Il répond à sa requête (section 1, mode C) : avancement du projet, travail de chacun, tenue des deadlines et pourquoi ; il rédige aussi le point périodique (mode A). Les chiffres, les remontées et les recommandations de réunion lui sont fournis par le code et par la brique 5 ; ce qui remonte est décidé par la brique 7 | État du projet, mémoires, remontées, recommandations | Rapport ou point périodique, contrôlé en code | Nemotron via Nightshift (à préciser) |

### Orchestrateur (proposition K)
Code déterministe. Il enchaîne un run : lecture des sources dans Zetaris, brique 1, puis briques 2 et 4, puis brique 5, règles de remontée (brique 7), rédaction par l'agent manager. Il porte aussi les déclenchements (à chaque changement d'état, à chaque `POST /run`), les limites (itérations, budget, timeouts), les replis et `SAMPLE_MODE`, et écrit les traces. Sans lui, un juge ne peut pas lancer le système de bout en bout.

## 3. Flux de contrôle
Qui décide de l'étape suivante : le code (workflow) ou le modèle (agent) ? Où sont les boucles (critique, révision, retry), les branchements (confiance, conflit) et les escalades vers un humain ? Quelles limites (nombre d'itérations, budget, timeout) ?

```mermaid
flowchart TD
  ZET[("Zetaris : sources en lecture<br/>messages, documents, tickets, registre, tâches")]
  subgraph B1["Brique 1 — Contexte fiable"]
    EX["Extracteur"] --> MAJ["Agent de mise à jour<br/>rapprocher, qualifier, proposer"]
    MAJ --> CTL{"Contrôleur<br/>code puis LLM"}
    CTL -->|"révision, 1 fois au plus"| MAJ
    CTL -->|"doute ou conflit"| ESC["Escalade"]
    CTL -->|"validé"| WR["Écriture de l'état<br/>seul écrivain"]
    WR --> NOTIF["Algorithme de notification"]
  end
  subgraph B2["Brique 2 — Avancement par membre"]
    SK["Skill sur l'IA de chaque collaborateur"] -->|"report_progress, schéma MCP"| RP["Validation du rapport"]
    CL{"Algorithme de classement"}
  end
  subgraph B4["Brique 4 — Correction des livrables"]
    CMP["Comparaison"] --> RED["Rédacteur"]
    RED --> VAL{"Validateur"}
    VAL -->|"révision, 1 fois au plus"| RED
  end
  subgraph B5["Brique 5 — Réunions"]
    TRI{"Tri : signaux, score, canal"} -->|"au-dessus du seuil"| AR["Analyste de réunion<br/>lecture seule"]
    AR --> VERD["Verdict humain"]
  end
  ZET --> EX
  ZET --> CMP
  ZET --> TRI
  RP --> MAJ
  WR --> WM[("World Model : état du projet")]
  WR --> HM[("H-MEM : mémoires")]
  NOTIF --> BOX[("Boîtes d'alertes")]
  BOX -->|"rendues à chaque appel MCP"| SK
  WM --> CL
  WM --> CMP
  CL -->|"obsolète, contradiction"| BOX
  CL -->|"signaux de coordination"| TRI
  WM -->|"nouvelle version"| TRI
  HM -->|"précédents, projets passés"| AR
  VAL -->|"diff et sources"| BOX
  AR -->|"message ciblé"| BOX
  VERD -->|"retour utile ou non"| HM
  subgraph B7["Brique 7 — Remontées"]
    RR{"Règles R1 à R7"} --> RBOX[("Boîte de remontées")]
    RBOX --> PT["Point périodique"]
  end
  WM -->|"nouvelle version"| RR
  CL -->|"constats"| RR
  ESC --> RR
  VAL -->|"diff en attente"| RR
  AR -->|"recommandation"| RR
  RUN["Question du manager<br/>skill manager ou POST /run"] --> MGR["Agent manager"]
  PT --> MGR
  WM --> MGR
  HM --> MGR
  MGR --> CHK{"Contrôle : P1 citées ?"}
  CHK -->|"révision, 1 fois au plus"| MGR
  CHK --> OUT["Point ou rapport"]
  OUT -->|"récupéré par MCP"| SKM["Skill manager"]
  RBOX -->|"récupérée par MCP"| SKM
```

Boucles de critique : contrôleur et agent de mise à jour (brique 1), validateur et rédacteur (brique 4), contrôle du rapport et agent manager (brique 7) ; une révision au plus, puis escalade ou ajout en code. Branchements : sortie du contrôleur, seuil du tri, choix du canal, issue de l'analyste, niveau des remontées. Restent à chiffrer : seuils, nombre d'appels d'outils de l'analyste, budgets et timeouts.

## 4. Flux de données
Qu'est-ce qui passe d'un composant à l'autre ? (Le guide : des artefacts et des résumés, pas des transcripts complets.)

- Entre agents : des enregistrements structurés (informations candidates, propositions de mise à jour, affirmations, réunions candidates), jamais le texte complet des sources, sauf pour l'extracteur et le rédacteur, qui travaillent sur le texte.
- Chaque enregistrement porte sa source (table Zetaris et identifiant, rapport MCP, réunion), pour que chaque sortie cite ses preuves.

À compléter.

## 5. Zetaris
Quelles sources, comment elles sont enregistrées (table REST ou fichier), quelles requêtes SQL les agents exécutent, que se passe-t-il si Zetaris ne répond pas ?

L'équipe définira les sources plus tard (décision du 27/10). Proposition de départ, pour que Zetaris porte la charge et que le jury le voie :

| Source dans Zetaris | Lue par |
|---|---|
| Messages du canal commun, transcriptions de réunion | Extracteur (brique 1) ; indicateur d'équivocité (brique 5) |
| Documents et livrables (briefs) | Extracteur, type « livrable » (brique 4) |
| Tickets | Agent de mise à jour (constats, blocages) ; classement (brique 2) |
| Registre des décisions | Agent de mise à jour (brique 1) |
| Tâches, objectifs, dépendances | Classement (brique 2) ; tri de la brique 5 |
| Agenda (option) | Coûts de la brique 5 |
| Archives des projets passés | Import dans la mémoire de l'organisation (H-MEM, long terme) |

Les déclencheurs de la brique 5 qui portent sur les sources (échéances, dépendances, fils de messages) peuvent être des requêtes SQL sur Zetaris.

## 6. État et mémoires
Proposition Q de la deuxième revue : **trois couches, chacune avec un rôle distinct.** Elle remplace D9 (voir [DECISIONS.md](DECISIONS.md), D12).

| Couche | Ce qu'elle contient | Pourquoi elle |
|---|---|---|
| **Zetaris** | Les sources brutes de l'entreprise, en lecture seule | Couche de données imposée ; aucune écriture vérifiée (D4) |
| **World Model** | **L'état courant du projet** : membres et rôles, tâches et dépendances, jalons, livrables, décisions en vigueur, blocages, avancement déclaré | Journal d'événements en ajout seul, d'où des versions de l'état (S2) ; ingestion idempotente et identifiants stables, d'où pas de doublon (S5) ; relations datées (`validFrom`, `validTo`) ; vues graphe (dépendances, utiles à la brique 5) et chronologie (échéances) ; file d'écriture à un seul écrivain ; résolution des conflits réglable sur « manuel », ce qui respecte la règle 3 |
| **H-MEM, court terme** | La journée et la session : rapports bruts, alertes rendues | La mémoire « journée de travail » du brouillon |
| **H-MEM, travail** | Le projet en cours : historique des décisions avec leur provenance, comptes rendus de réunion, verdicts sur les réunions | Provenance et confiance obligatoires ; journal de confiance qui trace chaque changement (« pourquoi le système dit-il 10 novembre ? ») ; retours `helpful` ou `wrong` qui modifient la confiance |
| **H-MEM, long terme** | L'organisation : enseignements des projets passés (Orion), précédents de réunions | Le « dreaming » propose des enseignements en fin de projet, un humain les approuve, et chacun garde le lien vers ses sources : c'est la capitalisation de la capacité 9 |

Les deux engines se complètent : World Model répond à « quel est l'état maintenant ? », H-MEM à « que s'est-il passé, que sait l'organisation, et pourquoi ? ». Le passage de World Model vers H-MEM (« world facts sync into memory ») est l'un des flux prévus par Meterless entre ses engines.

**Points d'attention :**
- La détection de conflits de H-MEM tourne une fois par jour et peut trancher seule au-dessus d'une confiance de 0,70. Pour les décisions, cette résolution automatique est désactivée : les conflits sont détectés par le contrôleur à chaque mise à jour et arbitrés par un humain (règle 3).
- Si le temps manque, World Model peut être remplacé par un état en JSON côté Python, derrière la même interface ; H-MEM, dont la conformité est déjà au vert, reste l'engine obligatoire.

**Engines non retenus pour le MVP :**
- **Scout Intent** : utile pour aiguiller la requête du manager et filtrer les injections dans les messages. Mais il n'existe qu'en spécification, sans implémentation de référence ni suite de conformité : feuille de route.
- **Markovian** : fait pour les longues chaînes de raisonnement ; le corpus Atlas est petit, il n'apporterait rien.

Format d'un enregistrement de décision, **un enregistrement par décision** :

| Champ | Contenu |
|---|---|
| `sujet` | Ce sur quoi porte la décision (par exemple « lancement Atlas ») |
| `attribut` | Date, périmètre, responsable, deadline d'un livrable, tâche assignée |
| `valeur` | La valeur décidée (par exemple « 10 novembre ») |
| `statut` | Proposition, approuvée, remplacée |
| `auteur` | Qui l'a prise (vérifié contre la table des rôles) |
| `source` | D'où elle vient (réunion, message, registre), avec sa référence |
| `date` | Quand elle a été prise |
| `confiance` | Niveau de confiance de l'extraction (H-MEM l'exige) |
| `remplace` | La décision qu'elle remplace, le cas échéant |

Avec ce format, le contrôleur et les algorithmes comparent des champs, pas du texte libre.

Restent à décider : l'emplacement de la table des rôles (proposition : une entité de World Model, alimentée depuis Zetaris), le mode d'intégration des engines (D11).

## 6 bis. Réunions et remontées au manager
- **Réunions** : portées par la brique 5 (tri, analyste, verdict). Le système recommande, la personne habilitée décide : aucune invitation n'est envoyée automatiquement.
- **Remontées et vue manager** : portées par la brique 7 (section 2) : trois modes (point périodique, exception, à la demande), règles R1 à R7 en code, interface par l'IA du manager avec un skill et le serveur MCP. Sur un gros projet, le point reste le même, mais la tenue du planning est agrégée par jalon et les P1 regroupées par jalon au-delà de trois (garde-fous de la brique 7) ; un portefeuille de projets est en feuille de route.

## 7. MCP
Quels outils, avec quels paramètres et quelles sorties ? Quels clients réels pour la démo ? Quelles écritures sont contrôlées avant d'entrer dans l'état ?

**Principe (proposition D)** : un serveur MCP répond quand le client l'appelle ; il ne peut pas contacter de lui-même l'IA d'un collaborateur. Les alertes sont donc **récupérées, pas poussées** : chaque membre a une boîte d'alertes, rendue quand son IA appelle le serveur (par exemple à chaque rapport du skill), et visible dans la vue manager.

| Outil | Paramètres | Sortie | Contrôles |
|---|---|---|---|
| `report_progress` (appelé par le skill) | Membre, tâche, avancement (0 à 1), valeurs sur lesquelles le travail repose (liste de sujet, attribut, valeur), blocages, commentaire libre | Accusé de réception + alertes en attente, ou erreur qui dit quoi corriger | Schéma validé par le serveur ; le membre est connu ; l'écriture passe par la brique 1 |
| `get_alerts` | Membre | Alertes en attente | Lecture seule |
| `get_project_context` | Membre ou projet | Décisions en vigueur, tâches, alertes, version de l'état | Lecture seule |
| `get_manager_brief` (skill manager) | Projet, depuis (date, facultatif) | Dernier point périodique et remontées ouvertes, P1 en tête | Lecture seule ; rôle manager ou personne habilitée |
| `ask_project` (skill manager) | Projet, question en texte libre | Rapport de l'agent manager, contrôlé en code (même logique que `POST /run`) | Rôle manager ou personne habilitée ; aucune écriture dans l'état |
| `mark_escalation` (skill manager) | Identifiant de la remontée, statut (`vue`, `traitée`), retour (`utile`, `inutile`, `trop tard`) | Accusé de réception | Rôle manager ou personne habilitée ; écrit seulement dans la boîte de remontées et dans H-MEM |

Pour la démo, le rôle de l'appelant est déclaré dans la configuration du client MCP, sans authentification (brique 7).

À compléter : clients réels de la démo.

## 8. Garde-fous
Habilitations (table des rôles côté backend), contenu externe traité comme des données, budgets, timeouts et fallbacks sur chaque appel sponsor, `SAMPLE_MODE`.

Déjà prévu :
- aucun agent n'écrit directement dans l'état : un seul écrivain, après le contrôleur ;
- l'autorité d'une information est décidée par des règles en code, jamais par un prompt ;
- l'analyste de réunion n'a que des outils de lecture ;
- les poids du tri de la brique 5 ne changent qu'après validation humaine ;
- le contrôleur vérifie les habilitations contre la table des rôles avant toute écriture.

## 9. Traces
Format JSONL : agent, action, résumé d'entrée et de sortie, agent cible, modèle, confiance, nombre de retries, statut. Écrites dans `logs/` et sur la sortie standard.

## 10. Tests et évaluation
Suites de conformité des engines, les cas de test du kit, les scénarios du cas d'usage, le contrôle anti-triche (changer une date avant une répétition), les tests et la métrique `trop tard` de la brique 7.

## 11. Ce qu'on coupe si le temps manque
Par ordre de priorité. Et ce qu'on ne coupe jamais.

Proposition, de ce qu'on coupe en premier à ce qu'on garde toujours :
1. Calibration des poids de la brique 5 (on garde l'enregistrement du verdict).
2. Coûts liés à l'agenda dans la brique 5 (on garde le nombre de participants).
3. Mémoire de l'organisation au-delà d'un enseignement rappelé (Orion).
4. World Model, remplacé par un état en JSON derrière la même interface.
5. Dans la brique 7 : R3, R6, la boucle de retour et les pistes de replanification (détail dans la brique 7).

On ne coupe jamais : la brique 1 avec le contrôleur, la brique 2, la brique 4 sur le brief, H-MEM avec son test, Zetaris interrogé en SQL, Nightshift, les traces, et le cœur de la brique 7 (R1, R2, R4, point périodique, skill manager) avec le rapport au manager.

---

## Historique des propositions intégrées
### Première revue (27/10)
| # | Proposition | Intégrée dans |
|---|---|---|
| A | Fusion des agents compte rendu et lecteur des discussions en un extracteur de décisions | Brique 1 |
| B | Contrôleur avec une révision au plus, puis escalade | Brique 1, flux de contrôle |
| C | 4e cas « réunion nécessaire » dans l'algorithme de classement | Brique 2, puis remplacé par K |
| D | Alertes récupérées via MCP (boîtes d'alertes), pas poussées | Briques 1 et 2, section 7 |
| E | Sources servies par Zetaris | Proposition de départ en section 5 |
| F | Agent manager comme point d'entrée `POST /run` | Sections 1 et 2 |
| G | Track 03 — Reasoning Architecture | En-tête, `DECISIONS.md` |

### Deuxième revue (27/10)
| # | Proposition | Intégrée dans |
|---|---|---|
| H | L'agent de mise à jour qualifie et propose ; l'autorité est décidée par des règles en code | Brique 1 |
| I | Rapports d'avancement structurés par le schéma de l'outil MCP ; pas d'agent LLM dans la brique 2 | Brique 2, section 7 |
| J | Les rapports d'avancement sont une source de la brique 1 (un seul écrivain de l'état) | Briques 1 et 2 |
| K | Le cas 4 émet des signaux pour la brique 5 ; l'agent manager ne fait que la synthèse ; orchestrateur en code | Briques 2 et 5, agent manager, orchestrateur |
| L | Contradiction entre membres (S6) et blocages par tickets (règle 5) | Brique 2 |
| M | Brique 4 : extraction, comparaison en code, rédacteur, validateur | Brique 4 |
| N | Brique 5 : réunions candidates, équivocité pour choisir le canal, déclenchement à chaque changement d'état | Brique 5 |
| O | Fonctionnement sans N+1 : personne habilitée lue dans la table des rôles | Section 1 |
| P | Calibration de la brique 5 par les verdicts humains dans H-MEM ; poids modifiés seulement après validation humaine | Brique 5, garde-fous |
| Q | Trois couches : Zetaris (sources), World Model (état courant), H-MEM (mémoires à trois échelles) | Section 6, `DECISIONS.md` (D12) |

### Troisième revue (27/10)
| # | Proposition | Intégrée dans |
|---|---|---|
| R | Brique 7 de l'équipe : management par exception, règles R1 à R7 en code, tolérances, niveaux P1 à P3, format d'une remontée, contrôle du rapport, retour `trop tard` | Brique 7 |
| S | Trois modes de remontée (point périodique même quand tout va bien, exception, à la demande) ; interface du manager par son IA avec un skill et le serveur MCP ; point produit par un run planifié et récupéré, pas poussé ; pistes de replanification proposées par l'agent manager, chiffres calculés en code | Brique 7, agent manager, sections 6 bis et 7, `DECISIONS.md` (D14) |
| T | Faisabilité de la brique 7 avant la clôture et ordre des coupes | Brique 7, section 11 |
