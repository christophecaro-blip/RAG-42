# Concepts à explorer — RAG against the machine

Feuille de route des notions à comprendre avant / pendant le projet.
Pour chaque concept : **ce que c'est**, **pourquoi ça compte ici**, **questions à te poser**, **pistes**.

---

## 0. Vue d'ensemble : qu'est-ce qu'un RAG ?

**Retrieval-Augmented Generation** : au lieu de réentraîner un modèle pour lui apprendre
de nouvelles connaissances, on lui donne au moment de répondre des extraits pertinents
tirés d'une source externe.

Les 4 étapes du sujet, chacune alimente la suivante :

```
corpus (data/raw/) ──► INDEXING ──► index (data/processed/)
                                        │
question ─────────────► RETRIEVING ◄────┘
                            │ top-k sources
                            ▼
                       AUGMENTING  (filtrer + construire le prompt)
                            │
                            ▼
                       GENERATING  (Qwen3-0.6B) ──► réponse JSON
```

**À retenir** : la note dépend surtout du **retrieval** (recall@k). La génération est
jugée avec indulgence (petit modèle).

---

## 1. Ingestion du corpus

**Quoi** : lire les fichiers de `data/raw/vllm-0.10.1/` (~1760 `.py`, ~180 `.md`, plus du
C++/CUDA, YAML, JSON…).

**Pourquoi ça compte**
- Choisir *quels fichiers indexer* : tout indexer ajoute du bruit, trop filtrer fait rater des sources.
- Le `file_path` renvoyé doit être **exactement** celui du corpus (`data/raw/vllm-0.10.1/...`).
- Les positions de caractères doivent correspondre à la façon dont le grader lit le fichier.

**Questions**
- Quelles extensions garder ? (`.py`, `.md`, `.txt`, `.rst`… et le reste ?)
- Encodage (UTF-8 ? erreurs ?), fins de ligne (`newline=""` vs défaut) : un décalage casse les offsets.
- Fichiers vides, binaires, énormes, illisibles → comment les ignorer proprement ?

**Pistes** : `pathlib.Path.rglob`, `open(..., encoding="utf-8")`, regarder le format des
datasets `AnsweredQuestions` pour voir quels fichiers sont attendus.

---

## 2. Chunking (découpage)

**Quoi** : couper chaque document en morceaux (chunks) ≤ `--max_chunk_size` (défaut et max 2000 caractères).

**Pourquoi ça compte**
- Une seule source > 2000 caractères **invalide toute la sortie**.
- Le sujet impose **deux stratégies distinctes** : code Python et Markdown/texte.
- La qualité des chunks conditionne directement le recall.

### 2.1 Chunking de code Python
- Découper selon la **structure** : fonctions, classes, méthodes, bloc d'imports / module.
- Outils : module standard `ast` (`lineno`, `end_lineno`, `col_offset`, `end_col_offset`),
  ou tree-sitter / `chonkie.CodeChunker`.
- Gérer les fonctions/classes trop longues → redécoupage (par méthode, puis par lignes).
- Garder du contexte ? (nom de la classe parente, signature, docstring)

### 2.2 Chunking Markdown / texte
- Découper par **titres** (`#`, `##`, `###`), puis par paragraphes, puis par phrases si nécessaire.
- Attention aux blocs de code ``` ``` à ne pas couper au milieu.
- Le titre de la section est souvent très informatif pour la recherche.

### 2.3 Notions transversales
- **Découpage récursif** : essayer un séparateur fort, sinon un plus faible.
- **Chevauchement (overlap)** : répéter un peu de texte entre chunks voisins → aide ou non ?
- **Taille vs recall** : petits chunks = précis mais contexte pauvre ; gros chunks = plus de
  chances de chevaucher la bonne zone. À mesurer et à documenter (demandé dans le README).
- **Offsets** : chaque chunk stocke `(file_path, start, end)` avec `text == contenu[start:end]`.

**Pistes** : `chonkie`, `langchain-text-splitters`, ou implémentation maison (facile à justifier).

---

## 3. Tokenisation pour la recherche lexicale

**Quoi** : transformer un texte (chunk ou question) en liste de termes comparables.

**Pourquoi ça compte** : « une question peut paraphraser une idée ou citer un identifiant
tel quel ». Ce que tu gardes à l'indexation décide de ce que tu pourras retrouver.

**Notions**
- Minuscules, ponctuation, stop words (*the*, *is*, *how*…).
- **Découpage des identifiants** : `enable_lora` → `enable_lora`, `enable`, `lora` ;
  `LLMEngine` → `llmengine`, `llm`, `engine`.
- **Stemming / lemmatisation** : `running` → `run` (ex. `PyStemmer`, `nltk`).
- Même tokenizer pour l'index **et** pour la requête.

---

## 4. Recherche lexicale : TF-IDF et BM25 (obligatoire : au moins un des deux)

### 4.1 TF-IDF
- **TF** (term frequency) : fréquence du terme dans le chunk.
- **IDF** (inverse document frequency) : un terme rare dans le corpus pèse plus lourd.
- Score = similarité (souvent cosinus) entre vecteur requête et vecteur chunk.

### 4.2 BM25 (recommandé)
- Amélioration de TF-IDF : **saturation** de la fréquence (paramètre `k1`) et
  **normalisation par la longueur** du document (paramètre `b`).
- Comprendre la formule et le rôle de `k1` (≈1.2–2.0) et `b` (≈0.75).

**Questions** : quel impact de `k1` / `b` sur le recall ? Faut-il des index séparés docs / code ?

**Pistes** : `bm25s` (rapide, sparse, sauvegarde sur disque), `rank_bm25`, `scikit-learn`
(`TfidfVectorizer`). Comprendre la notion d'**index inversé** et de **matrice creuse**.

---

## 5. Pistes d'amélioration (optionnel, « on top »)

- **Recherche dense / embeddings** : encoder chunks et questions en vecteurs
  (`sentence-transformers`), similarité cosinus. Capte les paraphrases.
- **Recherche hybride** : combiner BM25 + dense, par ex. avec **Reciprocal Rank Fusion (RRF)**.
- **Reranking** : un cross-encoder réordonne les top-N candidats.
- **Enrichissement des chunks** : ajouter le chemin du fichier, le nom de la fonction/classe,
  le titre de section dans le texte indexé (pas dans les offsets !).
- **Query expansion / reformulation**.
- **Index vectoriel** : `faiss`, `numpy` brut suffit souvent à cette échelle.

⚠️ Toujours vérifier le coût en temps (indexation ≤ 5 min, 200 questions ≤ 90 s).

---

## 6. Persistance de l'index

**Quoi** : sauvegarder l'index dans `data/processed/` pour que `search` le recharge vite.

**Questions**
- Quel format ? (`json` pour les métadonnées, `pickle`, `numpy .npy`, format natif de `bm25s`…)
- Qu'est-ce qui doit être sauvé : chunks + offsets + structures BM25 + paramètres (chunk size, tokenizer).
- Que faire si l'index est absent ou corrompu → message clair, pas de traceback.

---

## 7. Évaluation : recall@k et IoU

**recall@k** : pour chaque question, part des sources correctes retrouvées dans tes k premiers
résultats, moyennée sur toutes les questions.

**Une source compte comme trouvée si** : même fichier **et** chevauchement de plage
avec un **IoU ≥ 0.05**.

**IoU (Intersection over Union)** de deux intervalles `[a1, b1]` et `[a2, b2]` :
```
intersection = max(0, min(b1, b2) - max(a1, a2))
union        = max(b1, b2) - min(a1, a2)
IoU          = intersection / union
```

**Objectifs** : recall@5 ≥ **80 %** (docs) et ≥ **50 %** (code).

**À faire** : coder ta propre commande `evaluate` (sans jamais importer la moulinette),
puis itérer : changer un paramètre → mesurer → noter le résultat (pour le README).

---

## 8. Augmentation : construire le contexte

**Quoi** : choisir et formater les chunks récupérés pour les donner au modèle.

**Notions**
- **Fenêtre de contexte / budget de tokens** : compter en tokens (tokenizer de Qwen), pas en caractères.
- Combien de chunks inclure ? Dans quel ordre ? Avec quel en-tête (chemin du fichier) ?
- Déduplication de chunks qui se recouvrent.

---

## 9. Génération avec Qwen/Qwen3-0.6B

**Notions**
- **Hugging Face `transformers`** : `AutoTokenizer`, `AutoModelForCausalLM`, `generate()`.
- **Chat template** (`tokenizer.apply_chat_template`), rôles *system* / *user*.
- **Mode « thinking » de Qwen3** (`enable_thinking=False`, balises `<think>`) : à maîtriser
  pour obtenir une réponse propre.
- Paramètres de génération : `max_new_tokens`, température, greedy vs sampling.
- CPU vs GPU, `torch_dtype`, temps de génération par question.

**Prompt engineering** (évalué en soutenance)
- Consignes : répondre **uniquement** à partir du contexte, dire « je ne sais pas » sinon.
- Réponse concise, en lien direct avec la question.
- Réduire les **hallucinations** = rester **ancré (grounded)** dans les sources.

---

## 10. Modèles de données avec pydantic

**Quoi** : `MinimalSource`, `UnansweredQuestion`, `AnsweredQuestion`, `RagDataset`,
`MinimalSearchResults`, `MinimalAnswer`, `StudentSearchResults`, `StudentSearchResultsAndAnswer`.

**Notions**
- `BaseModel`, `Field(default_factory=...)`, héritage de modèles, `List[A | B]` (unions).
- Validation à la lecture : `Model.model_validate_json(...)` → gère le JSON malformé.
- Sérialisation : `model.model_dump_json(indent=...)`.
- Pydantic v2 vs v1 (méthodes différentes).

---

## 11. CLI avec Python Fire + tqdm

**Commandes** : `index`, `search`, `search_dataset`, `answer`, `answer_dataset`, `evaluate`,
lancées via `uv run python -m src <commande>`.

**Notions**
- `fire.Fire(Classe)` : chaque méthode devient une sous-commande, chaque paramètre une option.
- `src/__main__.py` pour que `python -m src` fonctionne.
- `tqdm` pour les barres de progression (indexation, datasets).
- **Robustesse** : requête vide, absurde, `k=0`, fichier manquant, JSON malformé →
  message d'erreur propre, **jamais de traceback**.
- Aucun chemin codé en dur : tout passe par des arguments.

---

## 12. Outillage et qualité du code

- **uv** : `uv init`, `uv add`, `pyproject.toml`, `uv.lock`, `uv sync`, `uv run`.
- **flake8** et **mypy** (`--disallow-untyped-defs`, idéalement `--strict`) : type hints partout.
- **Docstrings PEP 257** (style Google ou NumPy).
- **Gestion d'erreurs** : `try/except`, context managers (`with`).
- **Makefile** : `install`, `run`, `debug` (pdb), `clean`, `lint`, `lint-strict`.
- **Tests** : `pytest` (non rendus, mais utiles : offsets, taille des chunks, IoU…).
- `.gitignore` : ne pas commiter `data/processed/`, sorties, poids du modèle.

---

## 13. Performance

| Contrainte | Limite |
|---|---|
| Indexation du corpus complet | ≤ 5 min |
| Retrieval de 200 questions | ≤ 90 s |
| Taille d'une source | ≤ 2000 caractères |

**Notions** : profiling (`time`, `cProfile`), vectorisation `numpy`, matrices creuses
`scipy.sparse`, éviter de recharger l'index ou le modèle à chaque question.

---

## 14. README (en anglais)

Sections obligatoires à préparer au fil du projet : Description, Instructions, Resources
(+ usage de l'IA), **System architecture**, **Chunking strategy**, **Retrieval method**,
**Performance analysis** (recall@k, effet de la taille des chunks), **Design decisions**,
**Challenges faced**, **Example usage**.

👉 Tiens un petit journal de tes expériences (paramètre → recall) dès le début.

---

## Ordre de travail suggéré

1. Lire les datasets (questions + réponses attendues) pour comprendre ce qui est cherché.
2. Modèles pydantic + squelette CLI Fire + `uv`.
3. Ingestion + chunking (vérifier offsets et taille ≤ 2000).
4. BM25 + persistance de l'index.
5. `search_dataset` + `evaluate` → itérer jusqu'aux seuils de recall.
6. Génération avec Qwen3 + prompt.
7. Robustesse CLI, lint, Makefile, README.

## Ressources de départ

- BM25 : article Wikipedia « Okapi BM25 » ; doc de `bm25s`.
- Chunking : doc de `chonkie` ; doc Python du module `ast`.
- RAG : article original *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (Lewis et al., 2020).
- Hybride : *Reciprocal Rank Fusion* (Cormack et al., 2009).
- Qwen3 : fiche du modèle `Qwen/Qwen3-0.6B` sur Hugging Face (chat template, thinking mode).
- Outils : docs de `uv`, `pydantic` v2, `python-fire`, `tqdm`.
