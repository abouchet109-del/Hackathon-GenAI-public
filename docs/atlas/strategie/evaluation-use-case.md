# Évaluation du use case — Open Agent Hackathon 2026

> **Historique.** Ce document a servi à comparer les use cases. Le 26 octobre 2026, l'équipe a précisé sa différenciation (mémoire autonome qui suit l'avancement de chaque membre, évite les travaux contradictoires, vue manager) et a retenu le cas Atlas : voir [../use-case-atlas.md](../use-case-atlas.md). Les analyses ci-dessous restent utiles, en particulier le recadrage de l'idée (section 2) et les limites de Zetaris.

Rédigé le 26 octobre 2026. Clôture des soumissions : 27 octobre 2026, 23:45 UTC.

**Méthode.** Un sous-agent indépendant a refait l'évaluation de zéro, sans connaître le choix précédent (le #10, validation des allégations d'un lancement alimentaire). Il a appliqué le prompt jury de [prompt-jury.md](prompt-jury.md) : trois juges, portes éliminatoires, grille sur 100, médiane. Il a vérifié les sources de données par des requêtes GET publiques et dans le repo Zetaris local. Ensuite, il a noté le #10 avec la même grille pour un face-à-face.

**Légende.** [V] vérifié le 26/10/2026 ; [S] supposé, non vérifié.

---

## 1. Verdict

| | Use case | Note |
|---|---|---|
| **Recommandé** | **UC1 — Remédiation des vulnérabilités activement exploitées (CISA KEV) par une équipe sécurité multi-IA**, nom de travail « Precedent » | **82/100** |
| Plan B | #10 — Allégations alimentaires, dans sa variante « revalidation après reformulation d'un produit existant » | 79/100, environ 80 pour la variante |
| Référence | L'idée brute « plateforme de contexte multi-IA », sans use case | environ 59/100 |

L'écart entre UC1 et le #10 (3 points) est dans le bruit de notation : confiance de 55 à 60 %. Ce qui départage :
- **Le multi-IA via MCP est naturel chez des ingénieurs.** Claude Code et Cursor sont leurs vrais outils, et un serveur MCP local (stdio) ne coûte presque rien. Pour une équipe marketing ou réglementaire, les vrais outils sont plutôt Microsoft 365 Copilot ou ChatGPT Enterprise [S]. Il faudrait alors un serveur MCP distant en HTTPS, le mode développeur de ChatGPT et une authentification : plus de plomberie, plus de risque, démo moins crédible.
- **Zetaris porte davantage la charge.** UC1 joint trois sources en SQL (KEV, EPSS, inventaire d'actifs). Le #10 lit surtout une ligne produit par décision. Or le CTO de Zetaris fait partie du jury.
- **Le #10 a deux défauts.** Un produit en lancement n'existe pas encore dans Open Food Facts (d'où la variante « reformulation »), et une donnée d'allergène absente n'est pas une absence d'allergène.

Ce que le #10 fait mieux : chemin de données déjà vérifié dans Zetaris (lecture produit par produit), règles réglementaires très explicites, démo sans jargon.

---

## 2. Le recadrage indispensable de l'idée

Telle quelle, une plateforme qui centralise le contexte et le distribue par MCP plafonne autour de 59/100 :
- **Cadrage « plateforme »** : c'est l'exemple faible cité par le guide.
- **Ni décision ni action**, alors que le track 03 note des décisions et des actions.
- **La concurrence couvre déjà le partage multi-IA** : Mem0 OpenMemory, Supermemory (espaces partagés par coéquipier), Zep, ByteRover (descriptions tirées des pages des éditeurs).
- **MCP ne rapporte aucun point sponsor.**

**Le recadrage : une mémoire de décision gouvernée.** Le produit n'est pas un magasin de mémoire mais un gardien. Une décision proposée depuis l'IA d'un membre (Claude, Cursor…) n'entre dans la mémoire projet qu'après vérification contre les données de l'entreprise (Zetaris), la politique et les précédents. Les contradictions entre IA sont détectées et escaladées vers un humain. La mémoire appartient à l'entreprise et reste lisible depuis n'importe quelle IA. C'est cette version que le use case doit démontrer.

---

## 3. Classement (extrait)

Notes médianes des trois juges. Statut des données : (a) vérifiée dans le repo Zetaris local, (b) publique sans clé, vérifiée en GET mais pas dans Zetaris.

| Rang | Use case | Impact /30 | Tech /20 | Innov /15 | Démo /15 | UX /10 | Sponsor /10 | **Total** | Données |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Vulnérabilités KEV (UC1) | 25 | 15 | 12 | 13 | 9 | 8 | **82** | (b) KEV, EPSS ; inventaire synthétique |
| 2 | Allégations alimentaires (#10) | 23 | 15 | 11 | 13 | 9 | 8 | **79** | (a) Open Food Facts par produit |
| 3 | Conditions de crédit B2B | 23 | 16 | 9 | 11 | 8 | 9 | 76 | (a) SEC EDGAR, company_dns |
| 4 | Rappels alimentaires | 23 | 13 | 10 | 12 | 8 | 8 | 74 | (b) RappelConso, openFDA |
| 5 | Logistique et alertes météo | 22 | 13 | 10 | 13 | 8 | 8 | 74 | (b) NWS, USGS ; (a) NOAA |
| 5 | Incidents de fournisseurs SaaS | 22 | 14 | 11 | 11 | 8 | 8 | 74 | (b) Statuspage |
| 7 | Référencement fournisseurs | 24 | 12 | 10 | 11 | 8 | 8 | 73 | (b) GLEIF, BODACC |
| 8 | Mise à jour de dépendances OSS | 22 | 12 | 11 | 12 | 8 | 6 | 71 | (b) deps.dev, OSV |

Écartés : sources « known to fail » dans le repo Zetaris (PUDL, Foursquare, Overture, Ookla, GBIF, NASA DONKI, Singapore PM2.5), domaines médicaux, licences non résolues.

---

## 4. Le use case recommandé : UC1 « Precedent »

### Énoncé (format du guide, pour le deck)

> We are building an agent that helps the security operations lead of a mid-size company decide which actively exploited vulnerabilities to patch now, schedule or formally risk-accept, by matching new CISA KEV entries and their EPSS scores against the company's asset inventory and checking each proposal against the patching policy and the team's past decisions — whichever AI assistant each engineer used to record them — producing a policy-checked decision register with owners, deadlines and the precedent behind each decision, readable from every engineer's AI through MCP.

En français : un agent qui aide le responsable sécurité d'une ETI à décider, pour chaque vulnérabilité activement exploitée qui touche ses actifs, s'il faut patcher maintenant, planifier, accepter le risque avec une échéance ou escalader. Il s'appuie sur les données de l'entreprise dans Zetaris, la politique de patch et les décisions passées de l'équipe, quelle que soit l'IA utilisée par chaque ingénieur.

### Agents

| Composant | Type | Rôle | Interactions |
|---|---|---|---|
| TriagePlanner | Agent (Nemotron) | Interprète le déclencheur (nouvelles entrées KEV, liste de CVE, proposition venue d'une IA). Plan de 5 étapes au plus, avec un budget. Choisit la branche : normale, conflit ou données manquantes. | Délègue à l'Analyst et au Keeper ; reçoit les escalades du Critic |
| ExposureAnalyst | Agent (Nemotron) | Exécute le SQL sur Zetaris (KEV joint aux actifs, jointure externe sur EPSS). Rapproche produits et actifs avec un score de confiance. | Retry avec une requête plus étroite (2 essais au plus), puis repli sur le cache |
| DecisionDrafter | Agent (Nemotron) | Propose une décision par couple (CVE, actif), en citant les lignes Zetaris et les précédents H-MEM. | Échange avec le Critic |
| PolicyCritic | Agent (Nemotron + règles) | Applique la politique et une rubrique de 0 à 3 sur trois axes (exactitude, pertinence, actionnabilité). Sous 7/9 : une correction, une révision, puis escalade. Valide aussi les propositions venues des IA externes. | Renvoie des demandes de révision au Drafter |
| PrecedentKeeper | Service déterministe | Cherche les précédents dans H-MEM, contrôle les conflits, fournit la provenance, écrit les décisions approuvées. | Un conflit ouvert déclenche une branche vers l'escalade humaine |
| Reporter | Service déterministe | Produit le registre des décisions (JSON et Markdown) et la trace JSONL. | — |

Présenter PrecedentKeeper et Reporter comme des services, pas comme des agents : le jury pénalise « un agent avec plusieurs étiquettes ». Un humain approuve les escalades et toute acceptation de risque.

### Engine Meterless : H-MEM

**Fonctionnalité rendue possible : la mémoire de décision partagée et gouvernée.**
- Chaque décision devient un enregistrement H-MEM, qu'elle vienne d'un agent ou d'une IA via MCP. `source` et `confidence` sont obligatoires, et la provenance (`origin`, label) dit qui l'a écrite et depuis quel client [V, doc H-MEM].
- Les précédents retrouvés changent la décision du Drafter.
- Les conflits (même fait, valeurs ou dates différentes) bloquent les écrasements silencieux. H-MEM ne résout seul qu'à partir d'une confiance de 0,70, sinon la revue est humaine, et chaque résolution entre au journal de confiance avec l'état avant et après [V, doc H-MEM].
- Une acceptation de risque qui expire refait surface pour un nouveau tri.

**Attention :** la détection de conflits de H-MEM tourne en scan quotidien [V, doc H-MEM]. Pour la démo, il faut déclencher le contrôle au moment de l'écriture, ou ajouter dans le PrecedentKeeper un contrôle structuré (même CVE et même actif, décision ou échéance différente).

**Tests qui prouveront qu'il marche :**
1. La suite de conformité H-MEM du repo Meterless passe (code de sortie 0).
2. Précédent : sans mémoire, la décision est PATCH_NOW ; avec une acceptation de risque écrite dans une session précédente, elle devient ACCEPT_RISK et cite l'identifiant de la mémoire.
3. Inter-clients : écrire depuis Claude Code, relire depuis Cursor dans un nouveau processus.
4. Conflit : deux échéances contradictoires écrites par deux membres produisent un conflit, une escalade et deux entrées au journal.
5. Écriture gouvernée : une proposition contraire à la politique est rejetée avec sa raison, et rien n'est écrit.

### Données dans Zetaris

| Objet | Enregistrement | Source | Statut |
|---|---|---|---|
| Catalogue KEV | Table REST + `CACHE TABLE`, vue avec `explode(vulnerabilities)` | Flux JSON de la CISA | GET [V] : HTTP 200, 1,8 Mo, 1 756 entrées, version du 23/10/2026. Zetaris : à tester |
| Scores EPSS | Table REST sur une URL fixe `?cve=` contenant les CVE récentes du KEV, générée par le script d'enregistrement | API FIRST EPSS | GET [V, sous-agent]. Zetaris : à tester |
| Inventaire d'actifs | Table REST sur un JSON `{"assets":[…]}` servi par jsDelivr, épinglé sur un commit | Inventaire synthétique, étiqueté comme tel | Zetaris : à tester. Plan B : CSV sur un bucket S3 public (motif vérifié avec NOAA) |
| Politique de patch (option) | Même chemin que l'inventaire | Règles de l'équipe | Zetaris : à tester |

Le flux KEV fait environ quatre fois la plus grosse réponse REST validée dans le repo Zetaris (environ 420 Ko) : c'est le premier test à faire. Plan B si l'enregistrement échoue : publier un sous-ensemble du KEV via jsDelivr (licence CC0 [S, sous-agent]).

### Nemotron via Nightshift

Tous les appels passent par l'endpoint compatible OpenAI de Nightshift (par défaut `http://127.0.0.1:8088/v1`). Modèles prévus : `nvidia/nemotron-3-super-120b-a12b` pour le Planner, le Drafter et le Critic, `nvidia/nemotron-3.5-lightning-30b-a3b` pour l'Analyst. La trace JSONL enregistre pour chaque requête l'agent, le modèle renvoyé et la latence. Non vérifié : que Nightshift permette d'imposer un modèle Nemotron et renvoie le modèle réellement utilisé (`meterless/auto` peut router ailleurs).

### Passerelle MCP (l'idée de l'équipe, rendue concrète)

Quatre outils, configurés dans Claude Code et Cursor (stdio, local) :
- `get_project_context` : contexte du projet au format BRIEF | CITES[] | RISKS | OPEN_QS ;
- `get_decision` : une décision et son précédent ;
- `propose_decision` : passe par le Critic et le Keeper avant toute écriture ;
- `resolve_escalation` : l'humain tranche.

ChatGPT est optionnel : il exige un serveur distant en HTTPS. À couper en premier.

### Scénario de la vidéo (3 min 50)

| Temps | Scène |
|---|---|
| 0:00–0:20 | Le problème : la CISA ajoute des vulnérabilités activement exploitées ; Alice trie dans Claude, Bob dans Cursor ; Alice a déjà accepté un risque, Bob ne le sait pas |
| 0:20–0:40 | Un seul schéma : Zetaris, agents Nemotron, H-MEM, MCP |
| 0:40–1:50 | Run réel via `POST /run` : SQL Zetaris et ses lignes, précédent d'Alice retrouvé, conflit avec Bob escaladé, le Critic rejette une acceptation de risque sur un actif exposé à internet puis révision, registre final |
| 1:50–2:45 | Le moment multi-IA : dans Cursor, Bob demande s'il peut reporter un patch et reçoit la décision avec son précédent ; il propose une acceptation contraire à la politique, rejetée avec sa raison ; dans Claude Code, Alice tranche l'escalade. « Changez d'IA, ne perdez rien. » |
| 2:45–3:25 | Preuves sponsors : requêtes et comptages Zetaris, conformité H-MEM au vert, modèle Nemotron par requête. Aucune clé à l'écran |
| 3:25–3:50 | Valeur, limites (inventaire synthétique, validation humaine obligatoire), SAMPLE_MODE pour les juges |

### Ce qu'on coupe, dans l'ordre

1. Le client ChatGPT.
2. Le filtrage des écritures par un modèle de sécurité Nemotron.
3. NVD.
4. EPSS.
5. L'interface web (garder la ligne de commande, le Markdown et le JSONL).
6. L'export vers un vrai gestionnaire de tickets.
7. Tout second engine.

**À ne jamais couper :** la requête Zetaris dans le chemin live, H-MEM et ses tests, la boucle de critique, Nemotron journalisé, le SAMPLE_MODE (vraie logique sur données en cache, pas un rejeu de sorties), la vidéo.

---

## 5. Plan B : revalidation des allégations après reformulation

Si l'enregistrement du KEV échoue au test des deux premières heures sans plan B qui tienne, ou si l'équipe préfère un domaine sans jargon de sécurité.
- **Scénario.** Un produit existant est reformulé. Son étiquette actuelle vient d'Open Food Facts. La note de reformulation de la R&D et les nouvelles allégations du marketing arrivent comme contributions de deux IA différentes. Les agents revalident chaque allégation contre les règles (14 allergènes du Règlement 1169/2011 ; seuils du Règlement 1924/2006) et les décisions passées.
- **Données.** Tables REST par produit, motif vérifié dans le repo Zetaris. Les endpoints de recherche à URL fixe répondent (`/cgi/search.pl?…&json=1` en HTTP 200) mais ne sont pas testés dans Zetaris ; `/api/v2/search` renvoyait HTTP 503 pendant le test [V, sous-agent].
- **Pièges.** Champ d'allergènes absent ne veut pas dire « sans allergène » : la règle est d'escalader. Les seuils ont des variantes (solide ou liquide, pour 100 g ou pour 100 kcal). Ne pas recalculer le Nutri-Score : utiliser la note fournie. Licence ODbL : attribution et partage à l'identique pour le cache.

---

## 6. Tests bloquants des deux premières heures (go / no-go)

| # | Test | Qui |
|---|---|---|
| 1 | Nightshift installé et lancé (le port 8088 ne répondait pas le 26/10), clé NVIDIA ajoutée dans l'onglet Providers, une requête qui impose un modèle Nemotron renvoie bien ce modèle | Toi pour l'installation et la clé, puis test |
| 2 | Clé API Zetaris disponible ; flux KEV enregistré dans Zetaris, mis en cache, comptage égal à 1 756 | Toi pour la clé, puis test |
| 3 | JSON servi par jsDelivr enregistré comme table REST (inventaire d'actifs) | Test |
| 4 | Implémentation de référence H-MEM installée, suite de conformité au vert | Test |
| 5 | Claude Code se connecte au serveur MCP local | Test |

Si le test 2 échoue et qu'aucun plan B ne tient en deux heures : basculer sur le plan B.

**Machine (relevé du 26/10).** Zetaris semble lancé (port 8888 en écoute). GPU : NVIDIA GeForce GTX 1060 et Intel HD 630. RAM : 16 Go, soit le minimum demandé par Zetaris ; éviter de faire tourner des modèles locaux dans Nightshift, utiliser les modèles NVIDIA hébergés.

---

## 7. Vérifié / non vérifié

**Vérifié par la session principale le 26/10/2026 :**
- Flux CISA KEV : HTTP 200, `application/json`, 1,8 Mo, 1 756 entrées, version 2026.10.23, champs `cveID`, `vendorProject`, `product`, `dateAdded`, `requiredAction`, `dueDate`, `knownRansomwareCampaignUse`, `notes`, `cwes`.
- Doc H-MEM : `source` et `confidence` obligatoires, provenance obligatoire pour les nouvelles écritures, pas de champ `actor` (la provenance passe par `origin`) ; types de conflits ; résolution automatique à partir de 0,70, sinon revue humaine ; journal de confiance avec état avant et après pour chaque résolution ; scan des conflits quotidien.
- Jury (page de l'événement) : Michael Hay (CTO, Zetaris), Michael Armentano (Head of Technical Partnerships, SpaceXAI), Sam Cummings (VP of AI Engineering, GenAI Works), Shestakov Vladyslav (Head of Engineering, GenAI Works).
- Machine : voir section 6.

**Vérifié par le sous-agent seulement :** API EPSS, réponses Open Food Facts, type de contenu servi par jsDelivr, identifiants des modèles Nemotron dans le catalogue NVIDIA, descriptions des concurrents, template `templates/agentathon-starter` du repo Meterless (H-MEM persistant ; son mode LLM utilise le SDK Anthropic, à remplacer par Nightshift), incohérences du guide hackathon du repo Meterless.

**Non vérifié :** enregistrement dans Zetaris du KEV, d'EPSS et des JSON jsDelivr ; choix du modèle et retour du modèle réel par Nightshift ; conformité de la référence H-MEM ; configuration MCP sous Windows ; licence exacte d'EPSS ; taille de l'équipe et temps réellement disponible.

**Écart signalé par le sous-agent :** lors de sa première passe, il a écrit trois fichiers temporaires dans le scratchpad de la session (script de sondage d'API, arborescence du repo Meterless, catalogue de modèles NVIDIA). Aucun fichier de projet n'a été touché.
