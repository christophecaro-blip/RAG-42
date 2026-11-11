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
- [x] Ouvrir `data/datasets/AnsweredQuestions/dataset_docs_public.json` et `dataset_code_public.json`.
- [x] Compter les questions, regarder les champs (`question`, `sources`, `answer`, autres ?).
- [x] Pour 3 ou 4 questions, aller lire dans le corpus la plage `first_character_index → last_character_index` indiquée.
- [x] Relever : quels dossiers / extensions reviennent dans les sources ? Quelle taille font les plages ?
- [x] Comparer avec la version `UnansweredQuestions` : qu'est-ce qui manque ?

✅ Tu sais dire quels types de fichiers il faut indexer en priorité, et à quoi ressemble une « bonne » source.

🎤 Pourquoi un IoU de 0.05 seulement ? Qu'est-ce que ça change pour la taille de tes chunks ?

---

### Tâche 2 — Tester la moulinette à la main
🎯 Savoir évaluer un résultat avant même d'avoir un système.

🛠️
- [x] Lire `data+moulinette/moulinette_pkg/README.md`.
- [x] Copier le binaire adapté à ta machine et le renommer `moulinette` (ne pas le commiter).
- [x] Écrire **à la main** un petit fichier JSON de résultats pour 1 ou 2 questions (format `StudentSearchResults`).
- [x] Le passer à `./moulinette evaluate_student_search_results ...` et observer le recall.
- [x] Essayer volontairement une source > 2000 caractères ou un mauvais `file_path` : que se passe-t-il ?

✅ Tu comprends exactement ce qui est validé et ce qui est compté.

---

## Phase 2 — Les fondations

### Tâche 3 — Modèles pydantic
🎯 `src/models.py` contient les modèles du §6.4 du sujet.

📚 pydantic v2 : `BaseModel`, `Field(default_factory=...)`, héritage, unions `A | B` (§10).

🛠️
- [x] Écrire les 8 modèles du sujet, avec docstrings.
- [x] Tester dans un `uv run python` : charger un dataset JSON avec `RagDataset.model_validate_json(...)`.
- [x] Tester un JSON malformé : quelle exception est levée ?
- [x] Sérialiser un objet avec `model_dump_json(indent=2)`.

✅ Les deux datasets publics se chargent sans erreur.

🎤 Pourquoi `AnsweredQuestion | UnansweredQuestion` dans `RagDataset` ? Dans quel ordre pydantic essaie-t-il les types ?

---

### Tâche 4 — Squelette de la CLI
🎯 `uv run python -m src <commande>` fonctionne pour les 6 commandes du §6.6, même si elles ne font encore rien.

📚 Rôle de `__main__.py` et `python -m`, Python Fire (classe → sous-commandes) (§11).

🛠️
- [x] Créer `src/__main__.py` avec une classe exposée via `fire.Fire(...)`.
- [x] Déclarer `index`, `search`, `search_dataset`, `answer`, `answer_dataset`, `evaluate` avec leurs options.
- [x] Vérifier `uv run python -m src --help` et `make run ARGS="search 'test' --k 3"`.
- [x] Tester `make debug` : tu tombes bien dans pdb ?

✅ Chaque commande affiche ses arguments reçus.

🎤 Comment Fire transforme-t-il les paramètres d'une méthode en options CLI ? Que se passe-t-il si on passe `--k abc` ?

---

## Phase 3 — Indexation

### Tâche 5 — Ingestion du corpus
🎯 Une fonction qui liste et lit les fichiers utiles de `data/raw/`.

📚 `pathlib`, encodage, fins de ligne, chemins relatifs (§1).

🛠️
- [x] Parcourir récursivement `data/raw/` et filtrer les extensions retenues à la tâche 1.
- [x] Lire chaque fichier en gérant les erreurs (encodage, fichier illisible) sans planter.
- [x] Construire le `file_path` exactement au format `data/raw/vllm-0.10.1/...`.
- [x] **Vérifier les offsets** : pour quelques sources du dataset, `contenu[first:last]` doit afficher le bon passage.
- [x] Ajouter une barre `tqdm`.

✅ Tu affiches le nombre de fichiers lus par extension, et les offsets du dataset tombent juste.

🎤 Pourquoi la façon d'ouvrir le fichier (`newline`, `encoding`) peut-elle décaler tous les offsets ?

---

### Tâche 6 — Chunking Markdown avec chonkie
🎯 Découper les `.md` en chunks ≤ `max_chunk_size` avec leurs positions.

📚 Découpage récursif, recettes markdown de chonkie, `start_index` / `end_index` (§2.2, §2.3).

🛠️
- [x] Lire la doc de `chonkie.RecursiveChunker` (et sa recette markdown).
- [x] Attention : chonkie compte par défaut en **tokens**, le sujet en **caractères** → trouver comment configurer le tokenizer en mode caractères.
- [x] Découper un fichier, afficher les chunks et leurs positions.
- [x] Vérifier pour **chaque** chunk : `contenu[start:end] == chunk.text` et `end - start <= max_chunk_size`.

✅ Assertion vérifiée sur tous les `.md` du corpus.

🎤 Pourquoi couper sur les titres plutôt que tous les N caractères ?

---

### Tâche 7 — Chunking Python avec chonkie
🎯 Découper les `.py` selon leur structure (fonctions, classes).

📚 Arbre syntaxique (AST), tree-sitter, `chonkie.CodeChunker` (§2.1). Comparer avec le module standard `ast`.

🛠️
- [x] Lire la doc de `CodeChunker` (langage, taille, tokenizer en caractères).
- [x] Découper un fichier connu (ex. `vllm/lora/request.py`) et vérifier que les fonctions ne sont pas coupées au hasard.
- [x] Mêmes vérifications que la tâche 6 (offsets + taille).
- [x] Que deviennent une très longue fonction et un fichier avec erreur de syntaxe ?

✅ Les deux stratégies tournent sur tout le corpus, toutes les assertions passent.

🎤 En quoi tes deux stratégies sont-elles « distinctes » au sens du sujet ?

---

### Tâche 8 — Tokenisation pour la recherche
🎯 Une fonction qui transforme un texte en liste de termes.

📚 Minuscules, stop words, stemming, découpage `snake_case` / `CamelCase` (§3).

**Pourquoi pas `bm25s.tokenize` ?** Il garde `enable_lora` entier et ne découpe pas
`LLMEngine` (→ `llmengine`). Or presque toutes les questions contiennent des identifiants
(`trust_remote_code`, `FP8_MIN`, `LLM`…) et le corpus est surtout du code. On écrit donc
notre propre tokenizer ; bm25s accepte directement des listes de termes (`list[list[str]]`).

**Où** : `src/tokenizer.py` (pas `tokenize.py`, nom d'un module de la bibliothèque standard),
fonction publique `tokenize(text: str) -> list[str]`.

🛠️

**Étape 1 — Extraire les mots bruts**
- [x] `re.findall` avec une regex qui **garde le `_`** : `[A-Za-z0-9_]+`.
- [x] Vérifier : `"How does LLMEngine handle enable_lora?"` →
      `['How', 'does', 'LLMEngine', 'handle', 'enable_lora']` (ponctuation et espaces disparus).
- [x] Compiler la regex une seule fois, en constante de module (`re.compile`) : elle servira
      sur ~15 000 chunks.

**Étape 2 — Découper le snake_case**
- [x] Retirer les `_` du début et de la fin (`__init__` → `init`), puis `split("_")`.
- [x] `enable_lora` → `enable`, `lora` ; `trust_remote_code` → `trust`, `remote`, `code`.
- [x] Les chaînes vides produites par `__` doivent disparaître.

**Étape 3 — Découper le CamelCase** (sur chaque morceau de l'étape 2, **avant** les minuscules)
- [x] Regex proposée : `[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+[0-9]*|[A-Z]+[0-9]*|[0-9]+`
    - `[A-Z]+(?=[A-Z][a-z])` : une suite de majuscules suivie d'un mot (`LLM` dans `LLMEngine`) ;
    - `[A-Z]?[a-z]+[0-9]*` : un mot, avec ses chiffres collés (`Engine`, `Qwen3`, `fp16`) ;
    - `[A-Z]+[0-9]*` : un sigle (`HTTP`, `FP8`, `MIN`) ;
    - `[0-9]+` : un nombre seul (`2048`).
- [x] Vérifier sur ces cas :

    | Entrée | Morceaux attendus |
    |---|---|
    | `LLMEngine` | `LLM`, `Engine` |
    | `getHTTPResponse` | `get`, `HTTP`, `Response` |
    | `Llama2Model` | `Llama2`, `Model` |
    | `vLLM` | `v`, `LLM` |
    | `FP8`, `fp16`, `Qwen3` | inchangés |
    | `MoE` | `Mo`, `E` (imparfait, mais le mot entier `moe` est gardé) |

**Étape 4 — Assembler les termes d'un mot**
- [x] Toujours garder **le mot entier** en minuscules (`enable_lora`, `llmengine`).
- [x] Ajouter les morceaux en minuscules **seulement s'il y en a plus d'un** (sinon
      `handle` donnerait `handle`, `handle`).

**Étape 5 — Filtrer**
- [x] Stop words : `from bm25s.stopwords import STOPWORDS_EN` (33 mots courants : `a`, `the`,
      `in`, `is`…). Attention : `how`, `what`, `does` **n'y sont pas**.
- [x] Termes d'un seul caractère (`v`, `e`, `x`, `i`) : du bruit, à retirer.

**Étape 6 — Rendre les choix réglables**
- [x] Paramètres avec valeur par défaut, par exemple `remove_stopwords: bool = True`, ou
      constantes dans `config.py`. Objectif : comparer les variantes à la tâche 13 sans
      réécrire le code.

**Étape 7 — Tester** (dans un `if __name__ == "__main__":`)
- [x] Les sorties attendues :

    | Entrée | Sortie attendue |
    |---|---|
    | `"How does LLMEngine handle enable_lora?"` | `how, does, llmengine, llm, engine, handle, enable_lora, enable, lora` |
    | `"What's the default value of trust_remote_code in vLLM's LLM class?"` | `what, default, value, trust_remote_code, trust, remote, code, vllm, llm, llm, class` |
    | `"FP8_MIN"` | `fp8_min, fp8, min` |
    | `"__init__"` | `__init__, init`… ou seulement `__init__` : à toi de choisir |
    | `""` | `[]`, sans erreur |

- [x] Tokeniser tous les chunks de `chunk_documents` : mesurer le temps (doit rester de
      l'ordre de quelques secondes) et le nombre de termes distincts.

**Étape 8 — Décider et noter** (dans `notes.md`)
- [x] Stop words : oui/non, et pourquoi.
- [x] Stemming (`handles` → `handl`) : demande `PyStemmer` (non installé, `uv add PyStemmer`),
      peut abîmer les identifiants. Proposition : **non pour l'instant**, à tester à la tâche 13.
- [x] Mot entier + morceaux : oui (voir 🎤).

✅ Le même tokenizer sert aux chunks et aux questions.

🎤 Pourquoi garder à la fois `enable_lora` et `enable`, `lora` ?

---

### Tâche 9 — Index BM25 et persistance
🎯 La commande `index` construit et sauvegarde l'index dans `data/processed/`.

📚 Formule BM25, `k1`, `b`, index inversé, matrice creuse (§4, §6). Doc de `bm25s`.

🛠️
- [x] Construire l'index BM25 à partir des chunks tokenisés.
- [x] Sauvegarder l'index **et** les métadonnées des chunks (chemin, début, fin).
- [x] Recharger l'index dans un autre processus et vérifier qu'il est identique.
- [x] Mesurer le temps total d'indexation (limite : 5 min).

✅ `uv run python -m src index --max_chunk_size 2000` affiche un message de fin et le temps.

🎤 Explique BM25 avec tes mots. Qu'apporte-t-il par rapport à TF-IDF ?

---

## Phase 4 — Recherche et évaluation

### Tâche 10 — Commande `search`
🎯 Une question → top-k sources affichées.

📚 Le chemin inverse de l'indexation, appliqué à une question :
```
question (texte)
   │ 0. load_index()            → retriever bm25s + metadata
   │ 1. tokenize                → le même tokenizer, le même réglage que les chunks
   ▼
termes de la question
   │ 2. retriever.retrieve      → numéros des k meilleurs chunks + scores
   ▼
numéros de chunks
   │ 3. metadata.chunks[i]      → fichier + plage
   ▼
   │ 4. print                   → affichage
```
Où écrire : méthode `search` de `src/__main__.py`, à la place du `pass`. `query` et `k`
sont **déjà validés** par pydantic (`Query` : non vide, espaces retirés ; `K` : 1 à 10).

🛠️
- [x] Charger l'index, tokeniser la requête, récupérer les k meilleurs chunks.
    - [x] **0. Charger l'index** : importer `load_index`, découper le tuple en deux variables.
        - Index absent → rien à faire dans `search` : la `FileNotFoundError` levée par
          `load_index` **remonte toute seule**. L'afficher sans traceback = tâche 14,
          dans le bloc `__main__` (à côté de `except ValidationError`).
        - Nommage : la variable bm25s s'appelle `retriever` ailleurs (et `index` est
          aussi le nom d'une commande) → à renommer pour la cohérence.
    - [x] **1. Tokeniser la question** : `tokenize(query, remove_stopwords=...)`.
        - Le réglage à passer est celui **enregistré avec l'index** (`metadata`), pas la
          valeur par défaut de `config.py` : la question doit être tokenisée exactement
          comme les chunks, même si `config.py` a changé depuis le dernier `index`.
    - [x] **2. Chercher** avec `retriever.retrieve(...)`.
        - Lire la signature :
          `uv run python -c "import bm25s, inspect; print(inspect.signature(bm25s.BM25.retrieve))"`
        - Paramètres utiles : `query_tokens` (1er), `k`, `show_progress` (à couper,
          sinon une barre à chaque recherche ; le passer **par son nom**).
        - **Piège du format** : `retrieve` cherche **plusieurs questions d'un coup**. Elle
          attend une **liste de questions**, chacune une liste de termes :
          `[["enable", "lora"]]` pour une seule question. `tokens` est **une** liste de
          termes → que faut-il ajouter autour ?
        - Elle renvoie **deux** tableaux numpy à 2 dimensions (une ligne par question,
          k colonnes) : les numéros des chunks et leurs scores.
        - Explorer dans un terminal Python avant d'écrire :
          ```python
          from src.indexing import load_index
          from src.tokenizer import tokenize
          r, m = load_index()
          res, sc = r.retrieve([tokenize("How to enable LoRA?")], k=3, show_progress=False)
          print(res, sc, res.shape, res[0])
          ```
          Questions : que représentent les deux nombres de `res.shape` ? Pourquoi `[0]` ?
          Les scores sont-ils triés, et dans quel ordre ?
        - Ce que l'exemple affiche (question LoRA, `k=3`) :
          ```
          >>> print(res)
          [[ 926 1693  932]]               ← numéros des 3 meilleurs chunks
          >>> print(sc)
          [[9.614735 9.440198 8.748764]]   ← leurs scores, du meilleur au moins bon
          >>> print(res.shape)
          (1, 3)                            ← 1 question, 3 résultats
          >>> print(res[0])
          [ 926 1693  932]                  ← les résultats de LA question n° 0
          ```
          -> `retrieve` renvoie **deux choses** (numéros et scores) → **deux variables**,
             comme `build_index` et `load_index`.
          -> Ce qui en sort, ce sont des **résultats**, pas un « retriever » : le
             retriever, c'est l'objet qui cherche (celui chargé par `load_index`).
          -> `[[...]]` = tableau **à 2 dimensions**, une ligne par question. Une seule
             question posée → une seule ligne, la ligne `[0]`.
          -> Les scores sont déjà **triés**, du meilleur au moins bon.
        - Erreur fréquente : `retriever = index.retrieve()`.
          -> Parenthèses **vides** : bm25s ne sait pas quoi chercher → erreur
             « missing required argument ».
          -> Mauvais nom : `retrieve` ne renvoie pas un retriever, mais deux tableaux.
        - Ce qu'il faut mettre dans les parenthèses, dans cet ordre :

          | Quoi | Comment | Pourquoi |
          |---|---|---|
          | la question tokenisée | `tokens` **entourée de crochets** | `retrieve` attend une **liste de questions** ; `[tokens]` = une liste qui contient une question |
          | le nombre de résultats | `k=k` | à gauche le nom du paramètre de bm25s, à droite la variable `k` reçue par la commande |
          | pas de barre de progression | `show_progress=False` | sinon une barre à chaque recherche |

        - Forme de la ligne à écrire :
          ```python
          results, scores = <objet_bm25s>.retrieve(<question au bon format>, k=k, show_progress=False)
          ```
          Si elle dépasse 79 caractères (flake8 E501), la couper après une virgule, comme
          dans `build_index` (appel à `IndexMetadata(...)`).
        - Nommage : renommer la variable bm25s `index` → `retriever` (aux deux endroits
          où elle apparaît). La ligne se lit alors « le chercheur cherche » :
          `retriever.retrieve(...)`.
        - Vérifier avec deux `print` **temporaires** sous la ligne :
          ```python
          print(results)
          print(scores)
          ```
          `uv run python -m src search "How to enable LoRA?" --k 3` doit afficher deux
          tableaux de 3 nombres, comme dans l'exemple. Retirer ces `print` à l'étape 4.
- [x] Afficher fichier, plage et score.
    - [x] **3. Retrouver chaque chunk** : le numéro `i` renvoyé par bm25s correspond à
          `metadata.chunks[i]` (même ordre qu'à l'indexation, cf. tâche 9).
        - Ne garder que la ligne de la seule question posée (`results[0]`, `scores[0]`).
        - Parcourir numéros et scores **ensemble** : regarder `zip(...)`.
        - Chaque `Chunk` a `file_path`, `first_char_i`, `last_char_i` (voir `src/models.py`).
    - [x] **4. Afficher** avec `print` et une f-string, une ligne par résultat.
        - Contenu : rang (1, 2, 3…), score, fichier, plage `[début:fin]`.
          Pour le rang, regarder `enumerate(..., start=1)`.
        - Lisibilité : score arrondi (`:.2f`), colonnes alignées (`:6.2f` réserve
          6 caractères, comme dans l'ancien bloc de test de `indexing.py`).
        - Bonus : rappeler la question en en-tête ; afficher le `max_chunk_size` de
          l'index (`metadata`), utile quand on teste plusieurs tailles à la tâche 13.
        - ⚠️ **Piège Fire** : comme pour `index`, ne rien `return` (Fire afficherait
          l'objet). La méthode reste `-> None`.
        - Le `float` des scores est un `numpy.float32` : vérifier que `:.2f` l'accepte.
- [x] Tester avec quelques questions du dataset : la bonne source apparaît-elle ?
    - [x] La validation ci-dessous (question LoRA, `--k 5`).
    - [x] 3 ou 4 questions de `data/datasets/AnsweredQuestions/` (docs **et** code) :
          comparer le `file_path` attendu aux résultats. À quel rang arrive la bonne
          source ? La plage se recoupe-t-elle avec `first_character_index` /
          `last_character_index` attendus ?
    - [x] Cas limites rapides : `--k 1`, `--k 10`, `--k 0` et `--k 11` (refusés par
          pydantic), question absurde `"zzzz"` (que renvoie bm25s quand aucun terme ne
          correspond ? scores à 0 ?), question vide `""`.
    - [x] Index absent : renommer `data/processed/index.json`, lancer `search`, vérifier
          que **ton** message apparaît en dernière ligne, remettre le fichier.
    - [x] `make lint` passe (le F841 sur `tokens` disparaît à l'étape 2).

✅ `search "What HTTP endpoint is used to dynamically load a LoRA adapter?" --k 5` renvoie `docs/features/lora.md`.

🎤 Pourquoi tokeniser la question avec `metadata.remove_stopwords` et pas avec `config.py` ?
Pourquoi `retrieve` attend-elle une liste de listes alors qu'on n'a qu'une question ?
Que se passe-t-il si `search` est lancée avant `index` ?

---

### Tâche 11 — Commande `search_dataset`
🎯 Produire le fichier `StudentSearchResults` pour un dataset complet.

📚 Même chemin que `search`, mais pour **toutes** les questions d'un fichier, et un JSON
en sortie au lieu d'un affichage :
```
dataset JSON ─ 1. RagDataset (pydantic) ─ liste de questions (id + texte)
             ─ 2. recherche (le code de search, factorisé)  → chunks + scores par question
             ─ 3. MinimalSource / MinimalSearchResults / StudentSearchResults (pydantic)
             ─ 4. écriture : <save_directory>/<même nom que le dataset>.json
             ─ 5. moulinette → valide le format + recall@k
```
Où écrire : méthode `search_dataset` de `src/__main__.py` (+ un module partagé, étape 0).
Les modèles sont dans `src/models.py` (écrits à la tâche 3).

🛠️
- [ ] **0. Conception : ne pas copier-coller `search`.**
    - Le cœur de `search` (tokeniser → `retrieve` → `metadata.chunks[i]`) va servir à
      **4 commandes** : `search`, `search_dataset`, `answer`, `answer_dataset`. Copié 4 fois,
      un bug corrigé à un endroit resterait aux trois autres.
    - Idée : une **fonction** qui fait la recherche et **renvoie** les résultats sans rien
      afficher. Chaque commande l'appelle, puis fait sa propre sortie (`print` ou JSON).
      Principe déjà vu : « calculer » d'un côté, « afficher » de l'autre.
    - Questions à trancher avant de coder :
        - **Où** la mettre ? Pas dans `__main__.py` (c'est la CLI). Un nouveau module
          `src/search.py`, à côté de `indexing.py` et `tokenizer.py` ?
        - **Quels paramètres ?** Le retriever et les métadonnées (chargés **une seule fois**
          par la commande, pas à chaque question : pourquoi ?), la ou les questions, `k`.
        - **Une question ou plusieurs ?** `retrieve` est fait pour les paquets (tâche 10) :
          une fonction qui prend une **liste** de questions sert les deux cas (`search` lui
          passe une liste d'un élément).
        - **Que renvoyer ?** Pour chaque question, ses k résultats : chacun un `Chunk` et
          son score. Écrire le type de retour pour mypy, par ex.
          `list[list[tuple[Chunk, float]]]` (une liste par question, une paire par résultat).
    - Puis **réécrire `search`** pour qu'elle utilise cette fonction, et vérifier que son
      affichage est **identique** à avant (question LoRA `--k 5`) : on change la structure,
      pas le comportement. C'est un *refactoring*.
- [ ] **1. Charger le dataset avec pydantic.**
    - Même schéma que `load_index` : `read_text` (fichier → texte) puis
      `RagDataset.model_validate_json` (texte → objet validé).
    - `dataset_path` est déjà un `Path` (type `FilePath` : pydantic a vérifié que le fichier
      existe) ; `save_directory` est un simple `str`.
    - Regarder `RagDataset` dans `src/models.py` : `rag_questions` est une liste de
      `AnsweredQuestion | UnansweredQuestion`. Les deux ont `question_id` et `question` :
      c'est tout ce dont on a besoin. La commande marche donc avec les **deux** dossiers.
    - Tester : `len(dataset.rag_questions)` doit donner 100 (docs) et 99 (code).
- [ ] **2. Chercher toutes les questions (avec `tqdm`).**
    - Appeler la fonction de l'étape 0 avec la liste des textes des questions.
      Construire cette liste avec une compréhension : `[q.question for q in ...]`.
    - **`tqdm`** (barre de progression, déjà utilisé dans `ingest.py` et `chunking.py`) :
      l'envelopper autour de la boucle qui parcourt les questions, par ex. celle de
      l'étape 3, ou la tokenisation dans la fonction de l'étape 0.
      `for x in tqdm(liste, desc="Searching"):`
    - Index chargé **une fois** avant, pas dans la boucle : `load_index` prend ~0,2 s,
      × 200 questions = 40 s perdues sur 90.
- [ ] **3. Construire le résultat pydantic.** Trois modèles imbriqués, de l'intérieur
      vers l'extérieur :
    - `MinimalSource` : **un** résultat. ⚠️ Les noms diffèrent de `Chunk` :
      `first_char_i` → `first_character_index`, `last_char_i` → `last_character_index`
      (le format imposé par le sujet). `file_path` est identique.
    - `MinimalSearchResults` : **une** question. `question_id` et `question` **recopiés
      du dataset** (la moulinette relie tes résultats aux bonnes réponses par l'id : un
      id inventé = question introuvable). `retrieved_sources` = la liste de ses
      `MinimalSource`, dans l'ordre (le 1er = le meilleur, compte pour recall@1).
    - `StudentSearchResults` : le fichier entier. `search_results` = la liste des
      `MinimalSearchResults`, et `k`.
    - Parcourir questions et résultats **ensemble** : `zip` (comme à la tâche 10).
    - Les scores ne vont **pas** dans le fichier (aucun champ prévu).
- [ ] Écrire le JSON dans `--save_directory`, avec le même nom de fichier que le dataset.
    - **4. Le chemin de sortie** : le dossier `save_directory` + le **nom** du fichier du
      dataset. `Path` a un attribut qui donne juste le nom (`dataset_docs_public.json`
      sans les dossiers) : chercher dans `dir(Path)` / la doc de `pathlib`. Assembler
      avec `/`, comme `_BM25_DIR`.
    - Le dossier peut ne pas exister (`data/output/` n'existe pas encore) : le créer,
      comme `_BM25_DIR.mkdir(...)` dans `build_index`.
    - Écrire avec `write_text(objet.model_dump_json(...), encoding="utf-8")`.
      Option `indent=2` pour un fichier lisible (plus gros, mais pratique pour vérifier).
    - Afficher à la fin : nombre de questions, chemin du fichier, temps (comme `index`).
    - ⚠️ Piège Fire : ne rien `return`.
- [ ] Passer le résultat à la moulinette.
    - **5.** Lancer la commande puis la moulinette sur les **deux** datasets :
      ```bash
      uv run python -m src search_dataset \
          --dataset_path data/datasets/UnansweredQuestions/dataset_docs_public.json \
          --save_directory data/output/search_results --k 10
      ./moulinette evaluate_student_search_results \
          data/output/search_results/dataset_docs_public.json \
          data/datasets/AnsweredQuestions/dataset_docs_public.json \
          --k 10 --max_context_length 2000 --threshold 0.80
      ```
      (puis la même chose avec `code` et `--threshold 0.50`)
    - On cherche avec `UnansweredQuestions` (les questions seules, comme le jour de
      l'évaluation) et on compare à `AnsweredQuestions` (les bonnes réponses).
    - `Student data is valid: False` → lire le message : un nom de champ, un type, un id ?
    - `--max_context_length 2000` : la moulinette refuse une source de plus de 2000
      caractères. Nos chunks font au plus 2000 : vérifier qu'ils passent.
    - Noter recall@1/3/5/10 dans `notes.md` : c'est le **point de départ** de la tâche 13.
- [ ] Mesurer le temps pour 200 questions (limite : 90 s).
    - Le temps affiché par la commande, ou `time uv run python -m src search_dataset ...`.
    - Question : le temps est-il dominé par la recherche ou par le chargement de l'index ?

✅ La moulinette affiche `Student data is valid: True` et un premier recall.

🎤 Pourquoi factoriser la recherche dans une fonction plutôt que la copier dans chaque commande ?
Pourquoi charger l'index une seule fois ? Pourquoi recopier `question_id` du dataset ?
À quoi sert `FilePath` dans la signature de `search_dataset` ?

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
