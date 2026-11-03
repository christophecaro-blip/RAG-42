# Tâches pas à pas — RAG against the machine

Parcours guidé : chaque étape te fait découvrir une notion **et** ajoute une brique au projet.
Les numéros `§` renvoient à [concepts.md](concepts.md).

Pour chaque tâche :
- 🎯 **Objectif** : ce que tu construis
- 📚 **À découvrir** : les notions à lire avant de coder
- 🛠️ **À faire** : les étapes concrètes
- ✅ **Validation** : comment savoir que c'est terminé
- 🎤 **Soutenance** : questions qu'on pourrait te poser

> Règle d'or : à la fin de chaque tâche, `make lint` doit passer.

---

## Phase 1 — Comprendre le terrain

### Tâche 1 — Explorer les datasets
🎯 Comprendre ce que la moulinette attend de toi.

📚 Format JSON des datasets, recall@k, IoU (§7).

🛠️
- [ ] Ouvrir `data/datasets/AnsweredQuestions/dataset_docs_public.json` et `dataset_code_public.json`.
- [ ] Compter les questions, regarder les champs (`question`, `sources`, `answer`, autres ?).
- [ ] Pour 3 ou 4 questions, aller lire dans le corpus la plage `first_character_index → last_character_index` indiquée.
- [ ] Relever : quels dossiers / extensions reviennent dans les sources ? Quelle taille font les plages ?
- [ ] Comparer avec la version `UnansweredQuestions` : qu'est-ce qui manque ?

✅ Tu sais dire quels types de fichiers il faut indexer en priorité, et à quoi ressemble une « bonne » source.

🎤 Pourquoi un IoU de 0.05 seulement ? Qu'est-ce que ça change pour la taille de tes chunks ?

---

### Tâche 2 — Tester la moulinette à la main
🎯 Savoir évaluer un résultat avant même d'avoir un système.

🛠️
- [ ] Lire `data+moulinette/moulinette_pkg/README.md`.
- [ ] Copier le binaire adapté à ta machine et le renommer `moulinette` (ne pas le commiter).
- [ ] Écrire **à la main** un petit fichier JSON de résultats pour 1 ou 2 questions (format `StudentSearchResults`).
- [ ] Le passer à `./moulinette evaluate_student_search_results ...` et observer le recall.
- [ ] Essayer volontairement une source > 2000 caractères ou un mauvais `file_path` : que se passe-t-il ?

✅ Tu comprends exactement ce qui est validé et ce qui est compté.

---

## Phase 2 — Les fondations

### Tâche 3 — Modèles pydantic
🎯 `src/models.py` contient les modèles du §6.4 du sujet.

📚 pydantic v2 : `BaseModel`, `Field(default_factory=...)`, héritage, unions `A | B` (§10).

🛠️
- [ ] Écrire les 8 modèles du sujet, avec docstrings.
- [ ] Tester dans un `uv run python` : charger un dataset JSON avec `RagDataset.model_validate_json(...)`.
- [ ] Tester un JSON malformé : quelle exception est levée ?
- [ ] Sérialiser un objet avec `model_dump_json(indent=2)`.

✅ Les deux datasets publics se chargent sans erreur.

🎤 Pourquoi `AnsweredQuestion | UnansweredQuestion` dans `RagDataset` ? Dans quel ordre pydantic essaie-t-il les types ?

---

### Tâche 4 — Squelette de la CLI
🎯 `uv run python -m src <commande>` fonctionne pour les 6 commandes du §6.6, même si elles ne font encore rien.

📚 Rôle de `__main__.py` et `python -m`, Python Fire (classe → sous-commandes) (§11).

🛠️
- [ ] Créer `src/__main__.py` avec une classe exposée via `fire.Fire(...)`.
- [ ] Déclarer `index`, `search`, `search_dataset`, `answer`, `answer_dataset`, `evaluate` avec leurs options.
- [ ] Vérifier `uv run python -m src --help` et `make run ARGS="search 'test' --k 3"`.
- [ ] Tester `make debug` : tu tombes bien dans pdb ?

✅ Chaque commande affiche ses arguments reçus.

🎤 Comment Fire transforme-t-il les paramètres d'une méthode en options CLI ? Que se passe-t-il si on passe `--k abc` ?

---

## Phase 3 — Indexation

### Tâche 5 — Ingestion du corpus
🎯 Une fonction qui liste et lit les fichiers utiles de `data/raw/`.

📚 `pathlib`, encodage, fins de ligne, chemins relatifs (§1).

🛠️
- [ ] Parcourir récursivement `data/raw/` et filtrer les extensions retenues à la tâche 1.
- [ ] Lire chaque fichier en gérant les erreurs (encodage, fichier illisible) sans planter.
- [ ] Construire le `file_path` exactement au format `data/raw/vllm-0.10.1/...`.
- [ ] **Vérifier les offsets** : pour quelques sources du dataset, `contenu[first:last]` doit afficher le bon passage.
- [ ] Ajouter une barre `tqdm`.

✅ Tu affiches le nombre de fichiers lus par extension, et les offsets du dataset tombent juste.

🎤 Pourquoi la façon d'ouvrir le fichier (`newline`, `encoding`) peut-elle décaler tous les offsets ?

---

### Tâche 6 — Chunking Markdown avec chonkie
🎯 Découper les `.md` en chunks ≤ `max_chunk_size` avec leurs positions.

📚 Découpage récursif, recettes markdown de chonkie, `start_index` / `end_index` (§2.2, §2.3).

🛠️
- [ ] Lire la doc de `chonkie.RecursiveChunker` (et sa recette markdown).
- [ ] Attention : chonkie compte par défaut en **tokens**, le sujet en **caractères** → trouver comment configurer le tokenizer en mode caractères.
- [ ] Découper un fichier, afficher les chunks et leurs positions.
- [ ] Vérifier pour **chaque** chunk : `contenu[start:end] == chunk.text` et `end - start <= max_chunk_size`.

✅ Assertion vérifiée sur tous les `.md` du corpus.

🎤 Pourquoi couper sur les titres plutôt que tous les N caractères ?

---

### Tâche 7 — Chunking Python avec chonkie
🎯 Découper les `.py` selon leur structure (fonctions, classes).

📚 Arbre syntaxique (AST), tree-sitter, `chonkie.CodeChunker` (§2.1). Comparer avec le module standard `ast`.

🛠️
- [ ] Lire la doc de `CodeChunker` (langage, taille, tokenizer en caractères).
- [ ] Découper un fichier connu (ex. `vllm/lora/request.py`) et vérifier que les fonctions ne sont pas coupées au hasard.
- [ ] Mêmes vérifications que la tâche 6 (offsets + taille).
- [ ] Que deviennent une très longue fonction et un fichier avec erreur de syntaxe ?

✅ Les deux stratégies tournent sur tout le corpus, toutes les assertions passent.

🎤 En quoi tes deux stratégies sont-elles « distinctes » au sens du sujet ?

---

### Tâche 8 — Tokenisation pour la recherche
🎯 Une fonction qui transforme un texte en liste de termes.

📚 Minuscules, stop words, stemming, découpage `snake_case` / `CamelCase` (§3).

🛠️
- [ ] Écrire la tokenisation, la tester sur `"How does LLMEngine handle enable_lora?"`.
- [ ] Décider : stemming oui/non ? stop words oui/non ? → noter pour comparer plus tard.

✅ Le même tokenizer sert aux chunks et aux questions.

🎤 Pourquoi garder à la fois `enable_lora` et `enable`, `lora` ?

---

### Tâche 9 — Index BM25 et persistance
🎯 La commande `index` construit et sauvegarde l'index dans `data/processed/`.

📚 Formule BM25, `k1`, `b`, index inversé, matrice creuse (§4, §6). Doc de `bm25s`.

🛠️
- [ ] Construire l'index BM25 à partir des chunks tokenisés.
- [ ] Sauvegarder l'index **et** les métadonnées des chunks (chemin, début, fin).
- [ ] Recharger l'index dans un autre processus et vérifier qu'il est identique.
- [ ] Mesurer le temps total d'indexation (limite : 5 min).

✅ `uv run python -m src index --max_chunk_size 2000` affiche un message de fin et le temps.

🎤 Explique BM25 avec tes mots. Qu'apporte-t-il par rapport à TF-IDF ?

---

## Phase 4 — Recherche et évaluation

### Tâche 10 — Commande `search`
🎯 Une question → top-k sources affichées.

🛠️
- [ ] Charger l'index, tokeniser la requête, récupérer les k meilleurs chunks.
- [ ] Afficher fichier, plage et score.
- [ ] Tester avec quelques questions du dataset : la bonne source apparaît-elle ?

✅ `search "What HTTP endpoint is used to dynamically load a LoRA adapter?" --k 5` renvoie `docs/features/lora.md`.

---

### Tâche 11 — Commande `search_dataset`
🎯 Produire le fichier `StudentSearchResults` pour un dataset complet.

🛠️
- [ ] Charger le dataset avec pydantic, chercher pour chaque question (avec `tqdm`).
- [ ] Écrire le JSON dans `--save_directory`, avec le même nom de fichier que le dataset.
- [ ] Passer le résultat à la moulinette.
- [ ] Mesurer le temps pour 200 questions (limite : 90 s).

✅ La moulinette affiche `Student data is valid: True` et un premier recall.

---

### Tâche 12 — Commande `evaluate`
🎯 Calculer toi-même le recall@k, sans la moulinette.

📚 IoU d'intervalles, recall@k (§7).

🛠️
- [ ] Implémenter l'IoU et le recall@1/3/5/10.
- [ ] Comparer tes chiffres à ceux de la moulinette : ils doivent coïncider.
- [ ] (Bonus) Lister les questions ratées pour les analyser.

✅ Même recall que la moulinette sur les deux datasets publics.

🎤 Ne jamais importer la moulinette : pourquoi refaire le calcul soi-même ?

---

### Tâche 13 — Itérer jusqu'aux seuils
🎯 recall@5 ≥ 80 % (docs) et ≥ 50 % (code).

📚 Pistes du §5 si nécessaire (enrichissement des chunks, hybride, reranking).

🛠️
- [ ] Tenir un **journal d'expériences** : un changement → un recall → une conclusion.
- [ ] Faire varier : `max_chunk_size`, extensions indexées, tokenisation, `k1`/`b`, overlap.
- [ ] Analyser les questions ratées : pourquoi la bonne source n'est-elle pas remontée ?

✅ Seuils atteints, journal prêt pour la section *Performance analysis* du README.

---

## Phase 5 — Robustesse

### Tâche 14 — Cas limites de la CLI
🎯 La CLI ne plante **jamais** avec une traceback.

🛠️ Tester et gérer :
- [ ] requête vide, requête absurde (`"zzzz"`), `k=0`, `k` négatif, `k` non entier
- [ ] index absent (commande `search` avant `index`)
- [ ] dataset manquant, JSON malformé, mauvais format pydantic
- [ ] dossier de sortie inexistant

✅ Chaque cas affiche un message clair et sort proprement.

---

## Phase 6 — Génération

### Tâche 15 — Prise en main de Qwen3-0.6B
🎯 Générer une réponse à une question simple, sans RAG.

📚 `transformers` (`AutoTokenizer`, `AutoModelForCausalLM`), chat template, mode thinking de Qwen3 (§9).

🛠️
- [ ] `uv add torch transformers` (vérifier la compatibilité avec ta version de Python, prévoir l'espace disque).
- [ ] Charger le modèle, générer une réponse, mesurer le temps.
- [ ] Désactiver le mode thinking et comparer.

✅ Le modèle répond en quelques secondes.

---

### Tâche 16 — Commandes `answer` et `answer_dataset`
🎯 Réponses ancrées dans les sources récupérées.

📚 Budget de tokens, construction du contexte, prompt engineering, hallucinations (§8, §9).

🛠️
- [ ] Construire le prompt : consignes + extraits (avec leur chemin) + question.
- [ ] Respecter le budget de tokens (compter avec le tokenizer de Qwen).
- [ ] `answer_dataset` : lire un `StudentSearchResults`, produire un `StudentSearchResultsAndAnswer`.
- [ ] Lire une dizaine de réponses : cohérentes ? ancrées ? dans le sujet ?
- [ ] Essayer 2 ou 3 prompts différents et noter les différences.

✅ Le fichier de sortie est valide et les réponses sont globalement correctes.

🎤 Comment limites-tu les hallucinations ? Comment as-tu choisi le nombre d'extraits ?

---

## Phase 7 — Finalisation

### Tâche 17 — Vérification complète
- [ ] Cloner le dépôt dans un dossier vide, `uv sync`, puis dérouler le §6.7.2 du sujet de bout en bout.
- [ ] `make lint` (et idéalement `make lint-strict`) passe.
- [ ] Rien de lourd n'est commité (`data/raw`, index, sorties, poids du modèle).
- [ ] Temps d'indexation et de recherche dans les limites.

### Tâche 18 — README (en anglais)
- [ ] Première ligne en italique imposée.
- [ ] Sections : Description, Instructions, Resources (+ usage de l'IA), System architecture,
      Chunking strategy, Retrieval method, Performance analysis, Design decisions,
      Challenges faced, Example usage.
- [ ] S'appuyer sur ton journal d'expériences de la tâche 13.
