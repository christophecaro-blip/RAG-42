## Phase 1 — Comprendre le terrain

### Tâche 1 — Explorer les datasets
🎯 Comprendre ce que la moulinette attend de toi.

📚 Format JSON des datasets, recall@k, IoU (§7).

🛠️
- [x] Ouvrir `data/datasets/AnsweredQuestions/dataset_docs_public.json` et `dataset_code_public.json`.
    -> Fait
- [x] Compter les questions, regarder les champs (`question`, `sources`, `answer`, autres ?).
    -> 100 questions docs + 99 questions code ≈ 200 au total
       (cohérent avec la limite de perf : 200 questions en 90 s).
    ```bash
    python3 -c "import json; print(len(json.load(open('data/datasets/AnsweredQuestions/dataset_docs_public.json'))['rag_questions']))"
    ```
    Les champs :
    - question_id
    - question
    - answer : réponse de référence
    - sources : **toujours une seule source** par question
        - file_path
        - first_character_index
        - last_character_index
    - difficulty : toujours `"synthetic"` → questions générées automatiquement
    - is_valid : toujours `true`
    -> `difficulty` et `is_valid` ne servent pas pour le projet.

- [x] Pour 3 ou 4 questions, aller lire dans le corpus la plage `first_character_index → last_character_index` indiquée.
    - Question : "What HTTP endpoint is used to dynamically load a LoRA adapter in vLLM"
        -> Pour lire la plage exacte, on découpe le contenu du fichier avec Python :
        ```bash
        python3 -c "t=open('data/raw/vllm-0.10.1/docs/features/lora.md', encoding='utf-8').read(); print(t[4695:6098])"
        ```
        -> La plage commence exactement sur un titre Markdown : `### Using API Endpoints`.
           Les sources « docs » suivent la structure des sections → découper le Markdown
           par titres est une bonne piste (tâche 6).

- [x] Relever : quels dossiers / extensions reviennent dans les sources ? Quelle taille font les plages ?
    -> Les plages sont plus petites que 2000 caractères (le max est juste sous la limite) :

    | Dataset | min | médiane | max | Extensions | Dossiers |
    |---|---|---|---|---|---|
    | docs | 40 | ~1150 | 1997 | `.md` (97), `.txt` (3) | surtout `docs/`, + fichiers racine (`RELEASE.md`, `SECURITY.md`, `CMakeLists.txt`) |
    | code | 12 | ~880 | 1578 | `.py` (99) | uniquement `vllm/` |

    -> À indexer : `.md`, `.py` **et `.txt`** (les 3 sources `.txt` sont des `CMakeLists.txt`).
    -> Aucune source code dans `tests/`, `examples/`, `benchmarks/` : les exclure réduirait
       le bruit, mais les datasets privés peuvent différer → choix à mesurer, pas à supposer.
    -> Quelques plages sont très courtes (6 sur 199 font moins de 100 caractères) :
       voir la question IoU plus bas.

- [x] Comparer avec la version `UnansweredQuestions` : qu'est-ce qui manque ?
    -> Unanswered ne contient que `question_id` et `question`.
    -> Ce n'est pas un modèle qui génère les champs manquants :
       - **UnansweredQuestions** = l'énoncé : l'entrée de `search_dataset`.
       - **AnsweredQuestions** = le corrigé (vérité terrain) : utilisé par la moulinette
         et par ma commande `evaluate` pour noter mes résultats.
    -> Les deux fichiers ont les **mêmes `question_id`** : c'est ce qui permet d'associer
       mes résultats aux bonnes réponses. Je dois donc conserver le `question_id` du dataset
       en entrée dans mes résultats.

✅ Tu sais dire quels types de fichiers il faut indexer en priorité, et à quoi ressemble une « bonne » source.
    -> `.md`, `.txt` (docs) et `.py` sous `vllm/` (code). Une bonne source = une section
       cohérente (titre Markdown, fonction/classe Python), de quelques centaines à ~2000 caractères.

🎤 Pourquoi un IoU de 0.05 seulement ? Qu'est-ce que ça change pour la taille de tes chunks ?
    -> IoU = intersection / union des deux plages (même fichier obligatoire).
       - Chunk de 2000 qui contient une plage de 1000 → 1000 / 2000 = 0.5 ✔
       - Chunk de 2000 qui contient une plage de 100 → 100 / 2000 = 0.05 (juste à la limite)
       - Chunk de 2000 qui contient une plage de 12 → 12 / 2000 = 0.006 ✘
    -> Le seuil est bas pour ne pas exiger de retrouver la plage exacte : il suffit de
       tomber « dans la bonne zone du bon fichier ». Les plages de référence ne
       correspondent de toute façon pas à mes propres découpages.
    -> Conséquences pour la taille des chunks :
       - De gros chunks (proches de 2000) passent pour la grande majorité des plages
         (médianes ~900–1150) et donnent plus de contexte au modèle.
       - Mais ils ratent les plages très courtes : pour une plage de L caractères, un chunk
         qui la contient doit faire au plus 20 × L (ex. ≤ 240 pour une plage de 12).
       - Des chunks plus petits sont plus précis, mais une plage peut être répartie sur
         plusieurs chunks et le contexte donné au modèle est plus pauvre.
       → Compromis à mesurer avec `--max_chunk_size` (demandé dans le README).
    -> Ce que le seuil ne pardonne pas : un `file_path` différent donne toujours IoU = 0,
       même si le contenu est identique.

### Tâche 2 — Tester la moulinette à la main
🎯 Savoir évaluer un résultat avant même d'avoir un système.

🛠️
- [x] Lire `data+moulinette/moulinette_pkg/README.md`.
    -> Fait
- [x] Copier le binaire adapté à ta machine et le renommer `moulinette` (ne pas le commiter).
    -> Fait (Fedora → `moulinette-fedora`), ignoré par git.
- [x] Écrire **à la main** un petit fichier JSON de résultats pour 1 ou 2 questions (format `StudentSearchResults`).
    -> Fait : `data+moulinette/moulinette_pkg/test.json`
       (format décrit dans le sujet §6.4 / §6.5 et dans le README de la moulinette).
- [x] Le passer à `./moulinette evaluate_student_search_results ...` et observer le recall.
    Commande (depuis la racine du projet, résultats d'abord, corrigé ensuite) :
    ```bash
    ./data+moulinette/moulinette_pkg/moulinette evaluate_student_search_results \
        data+moulinette/moulinette_pkg/test.json \
        data/datasets/AnsweredQuestions/dataset_docs_public.json \
        --k 10 --max_context_length 2000
    ```
    ```
    Student data is valid: True
    Total number of questions: 100
    Total number of questions with sources: 100
    Total number of questions with student sources: 2
    📊 Questions evaluated: 100
    📈 Recall@1: 0.020 (2.0%)   Recall@3: 0.020   Recall@5: 0.020   Recall@10: 0.020
    ```
    -> Le recall est calculé sur **les 100 questions du corrigé**, pas seulement sur celles
       de mon fichier : 2 trouvées / 100 = 0.02. Une question absente compte comme ratée.
       → `search_dataset` doit produire un résultat pour **chaque** question.
    -> Les 4 recall sont égaux car chaque question n'a qu'une source, placée en 1re position.

- [x] Essayer volontairement une source > 2000 caractères ou un mauvais `file_path` : que se passe-t-il ?
    - Source trop longue (2645 caractères) :
    ```
    Source data/raw/vllm-0.10.1/docs/features/quantization/int8.md[2439:5084] has a length of 2645 which is more than the limit of 2000 characters
    Student data is valid: False
    ```
    -> **Tout le fichier** est rejeté, pas seulement cette question.
    - Mauvais `file_path` (`docs/featurs/lora.md`) : recall 0.02 → 0.01.
    -> Le fichier reste **valide**, la source compte juste comme ratée, **sans aucun avertissement**.
       Une faute de chemin est donc une erreur silencieuse → toujours construire les chemins
       à partir des fichiers réellement lus, jamais à la main.

- [x] Tests complémentaires (fichiers de test hors projet, question LoRA, plage attendue `4695 → 6098`, soit 1403 caractères)

    | Test | Résultat |
    |---|---|
    | Source de **2000** caractères pile (`4500 → 6500`) | ✔ valide, trouvée |
    | Source de **2001** caractères (`4500 → 6501`) | ✘ `has a length of 2001 ... more than the limit` → fichier invalide |
    | **11 sources** pour une question (`k` = 10) | ✘ `has more than 10 sources` → fichier invalide |
    | Mauvaise source en 1re, bonne en 2e | Recall@1 = 0.00, Recall@3/5/10 = 0.01 |
    | Bonne source en 1re, mauvaise en 2e | Recall@1 = 0.01 partout |
    | `"k": 10` dans le JSON, moulinette `--k 5` | ✘ `Student data has more than 5 sources` → fichier invalide |
    | `"k": 5` dans le JSON, moulinette `--k 10` | ✔ valide |
    | Source de 80 caractères dans la plage (IoU = 80/1403 ≈ 0.057) | ✔ trouvée |
    | Source de 71 caractères dans la plage (IoU ≈ 0.0506) | ✔ trouvée |
    | Source de 60 caractères dans la plage (IoU ≈ 0.043) | ✘ ratée |

    Conclusions :
    -> Limite de taille **inclusive** : `last - first <= 2000` est accepté, 2001 est refusé.
    -> Au plus `k` sources par question, sinon tout le fichier est invalide.
    -> Le champ `k` du JSON doit être **≤ au `--k` de la moulinette**. Pendant la soutenance,
       la moulinette est lancée avec `--k 10` → produire mes résultats avec `--k 10`.
    -> **L'ordre compte** : recall@1 ne regarde que la 1re source, recall@3 les 3 premières…
       Les sources doivent être triées de la plus pertinente à la moins pertinente.
    -> Le seuil d'IoU de 0.05 se vérifie en pratique : trop petite par rapport à la plage
       attendue, une source qui tombe pourtant au bon endroit est ratée (et inversement
       pour un gros chunk autour d'une petite plage).

✅ Tu comprends exactement ce qui est validé et ce qui est compté.

    | Cas | Effet |
    |---|---|
    | Question absente du fichier | comptée ratée, fichier valide |
    | Mauvais `file_path` | source ratée, fichier valide, **aucun avertissement** |
    | Source > 2000 caractères | **fichier entier invalide** |
    | Plus de `k` sources pour une question | **fichier entier invalide** |
    | `k` du JSON > `--k` de la moulinette | **fichier entier invalide** |
    | Mauvaise source avant la bonne | recall@1 perdu, recall@3+ conservé |
    | IoU < 0.05 (même fichier) | source ratée |

---

## Phase 2 — Les fondations

### Tâche 3 — Modèles pydantic
🎯 `src/models.py` contient les modèles du §6.4 du sujet.

📚 pydantic v2 : `BaseModel`, `Field(default_factory=...)`, héritage, unions `A | B` (§10).

🛠️
- [x] Écrire les 8 modèles du sujet, avec docstrings.
    -> Fait. `make lint` et `make lint-strict` passent.
- [x] Tester dans un `uv run python` : charger un dataset JSON avec `RagDataset.model_validate_json(...)`.
    ```python
    >>> from src.models import RagDataset
    >>> d = RagDataset.model_validate_json(open("data/datasets/AnsweredQuestions/dataset_docs_public.json").read())
    ```
    | Fichier | Questions | Type obtenu |
    |---|---|---|
    | AnsweredQuestions / docs | 100 | `AnsweredQuestion` |
    | UnansweredQuestions / docs | 100 | `UnansweredQuestion` |
    | AnsweredQuestions / code | 99 | `AnsweredQuestion` |
    | UnansweredQuestions / code | 99 | `UnansweredQuestion` |

    -> Les champs en trop des datasets (`difficulty`, `is_valid`) sont **ignorés sans erreur** :
       par défaut, pydantic ne garde que les champs déclarés.
    -> `test.json` se charge avec `StudentSearchResults`.

- [x] Tester un JSON malformé : quelle exception est levée ?
    - Syntaxe JSON fausse :
    ```
    pydantic_core._pydantic_core.ValidationError: 1 validation error for StudentSearchResults
      Invalid JSON: expected `,` or `}` at line 12 column 7 [type=json_invalid, input_value='{\n  "search_results": [...  }\n  ],\n  "k": 10\n}', input_type=str]
        For further information visit https://errors.pydantic.dev/2.14/v/json_invalid
    ```
    - Autres cas (JSON syntaxiquement correct mais contenu faux) :

    | Cas | Résultat | `type` de l'erreur |
    |---|---|---|
    | Champ `k` supprimé | ✘ `ValidationError` : `k  Field required` | `missing` |
    | `"k": "dix"` | ✘ `ValidationError` : `unable to parse string as an integer` | `int_parsing` |
    | `"k": "10"` (chaîne de chiffres) | ✔ **accepté**, converti en `10` | — |
    | `first_character_index: 4695.7` | ✘ `ValidationError` : `got a number with a fractional part` | `int_from_float` |
    | Champ inconnu ajouté (`"extra": 1`) | ✔ accepté, ignoré | — |
    | Fichier inexistant | ✘ `FileNotFoundError` levée par `open()`, **avant** pydantic | — |

    -> Tous les problèmes de contenu (syntaxe, champ manquant, mauvais type) lèvent la
       **même exception** : `pydantic.ValidationError`. Le message indique le chemin exact du
       champ fautif (ex. `search_results.0.retrieved_sources.0.first_character_index`).
    -> Un fichier absent lève une autre exception (`FileNotFoundError`, famille `OSError`).
       → Pour la CLI (tâche 14), il faudra intercepter **au moins** ces deux familles
         et afficher un message clair au lieu de la traceback.
    -> pydantic est **tolérant par défaut** (mode « lax ») : il convertit `"10"` en `10`.
       Pour tout refuser sauf un vrai entier, il existe un mode strict
       (`model_config = ConfigDict(strict=True)`) — pas nécessaire ici.

- [x] Sérialiser un objet avec `model_dump_json(indent=2)`.
    ```python
    >>> r = StudentSearchResults.model_validate_json(open("data+moulinette/moulinette_pkg/test.json").read())
    >>> print(r.model_dump_json(indent=2))
    ```
    -> Produit exactement le format attendu par la moulinette (mêmes clés, même imbrication).
       C'est ce que `search_dataset` utilisera pour écrire son fichier de sortie.
    -> Le JSON relu puis réécrit ne garde que les champs déclarés : les champs inconnus
       disparaissent.

✅ Les deux datasets publics se chargent sans erreur.
    -> Fait (voir tableau ci-dessus).

🎤 Pourquoi `AnsweredQuestion | UnansweredQuestion` dans `RagDataset` ? Dans quel ordre pydantic essaie-t-il les types ?
    -> **Pourquoi l'union** : le même modèle `RagDataset` sert à lire les deux sortes de fichiers,
       l'énoncé (questions seules) et le corrigé (questions + `sources` + `answer`).
    -> **Ordre** : en pydantic v2, l'ordre **ne compte pas** par défaut. Le mode `smart` essaie
       tous les types et garde celui qui correspond le mieux (celui qui utilise le plus de
       champs fournis). Test en inversant l'union :

    | Union | Mode | Type obtenu pour une question du corrigé |
    |---|---|---|
    | `AnsweredQuestion \| UnansweredQuestion` | `smart` (défaut) | `AnsweredQuestion` |
    | `UnansweredQuestion \| AnsweredQuestion` | `smart` (défaut) | `AnsweredQuestion` |
    | `UnansweredQuestion \| AnsweredQuestion` | `left_to_right` | ⚠️ `UnansweredQuestion` (`sources` perdues) |
    | `AnsweredQuestion \| UnansweredQuestion` | `left_to_right` | `AnsweredQuestion` |

    -> En mode `left_to_right` (`Field(union_mode="left_to_right")`), pydantic prend le
       **premier** type qui valide. Comme `UnansweredQuestion` accepte aussi une question
       du corrigé (les champs en trop sont ignorés), le placer en premier ferait perdre
       `sources` et `answer`.
    -> Mettre le type le plus complet (`AnsweredQuestion`) en premier, comme le sujet,
       est donc le choix sûr quel que soit le mode.

### Tâche 4 — Squelette de la CLI
🎯 `uv run python -m src <commande>` fonctionne pour les 6 commandes du §6.6, même si elles ne font encore rien.

📚 Rôle de `__main__.py` et `python -m`, Python Fire (classe → sous-commandes) (§11).

🛠️
- [x] Créer `src/__main__.py` avec une classe exposée via `fire.Fire(...)`.
    -> Classe `CLI`, appel `fire.Fire(CLI)` **sous la garde** `if __name__ == "__main__":`
       (sinon la CLI se lance dès qu'un autre fichier importe le module, ex. un test).
- [x] Déclarer `index`, `search`, `search_dataset`, `answer`, `answer_dataset`, `evaluate` avec leurs options.
    -> Noms des paramètres **identiques au sujet** : ce sont eux qui deviennent les options.
       Piège rencontré : `student_search_result_path` (sans *s*) → l'option du sujet
       `--student_search_results_path` était refusée.
    -> Ordre : `query` en premier pour `search` / `answer` (le sujet écrit `search <query> --k`).
       Paramètres avec défaut **après** ceux sans défaut (règle Python) → `k` en dernier.
    -> Défauts : `max_chunk_size = 2000` (imposé), `k = 10` (valeur utilisée partout dans le sujet,
       et la moulinette tourne en `--k 10`).
    -> **Validation avec pydantic** (`@validate_call` sur chaque méthode) et types réutilisables :

    | Type | Définition | Refuse |
    |---|---|---|
    | `ChunkSize` | `Annotated[int, Field(ge=1, le=2000, strict=True)]` | `0`, `2001`, `abc`, `15.5`, `True` |
    | `K` | `Annotated[int, Field(ge=1, le=10, strict=True)]` | `0`, `11`, `abc` |
    | `Query` | `Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]` | `""`, `"   "` |
    | `FilePath` (pydantic) | le fichier doit exister | fichier absent, dossier |

    -> Pas de `ConfigDict(strict=True)` sur toute la méthode : `FilePath` refuserait alors
       la chaîne envoyée par Fire (`Input should be an instance of Path`). Le mode strict est
       mis seulement sur les entiers, via `Field(strict=True)`.
    -> `ValidationError` interceptée autour de `fire.Fire(CLI)` : un message par erreur sur
       `stderr`, puis `sys.exit(1)`. Fire passe les arguments par position, donc pydantic
       donne un indice (`(1,)`) ; `_param_names` le retraduit en nom d'option :
       ```
       Error: --dataset_path='nope.json': Path does not point to a file
       Error: --k=0: Input should be greater than or equal to 1
       ```
    -> Piège de version : `f"{e["loc"]}"` (mêmes guillemets dedans et dehors) n'est valide
       qu'à partir de Python 3.12 → `{e['loc']}`, puisque le projet annonce `>=3.10`.
- [x] Vérifier `uv run python -m src --help` et `make run ARGS="search 'test' --k 3"`.
    -> OK : `--help` liste les 6 commandes avec leur docstring ; `make run ...` → code de sortie 0.
- [x] Tester `make debug` : tu tombes bien dans pdb ?
    -> OK : `make debug ARGS="search q"` s'arrête sur la 1re ligne de `src/__main__.py` avec
       l'invite `(Pdb)`.

✅ Chaque commande affiche ses arguments reçus.
    -> Les commandes ne font encore rien (`pass`), mais les arguments sont validés.

🎤 Comment Fire transforme-t-il les paramètres d'une méthode en options CLI ? Que se passe-t-il si on passe `--k abc` ?
    -> **Comment Fire construit la CLI** : `fire.Fire(CLI)` lit la classe par introspection
       (`inspect`) et applique ces règles :

    | Dans le code | Dans le terminal |
    |---|---|
    | méthode publique `search` | sous-commande `search` |
    | méthode commençant par `_` | cachée, pas de sous-commande |
    | paramètre `query` (sans défaut) | argument obligatoire, positionnel ou `--query` |
    | paramètre `k: K = 10` (avec défaut) | option facultative `--k`, défaut 10 |
    | docstring | texte de `--help` |
    | nom du paramètre | nom de l'option → doit être **exactement** celui du sujet |

    -> Un paramètre peut être passé par position (`search q 4`) ou par nom
       (`search q --k 4`) ; les options nommées s'écrivent dans n'importe quel ordre.
    -> Option inconnue (`--unknown 1`) : Fire refuse et affiche l'aide de la commande.

    -> **`--k abc`** : Fire **ne lit pas les annotations de type**. Il devine le type à partir
       du texte tapé (`5` → `int`, `5.0` → `float`, `True` → `bool`, `abc` → `str`) et le
       transmet tel quel. Sans validation, la méthode recevrait la chaîne `'abc'`
       sans aucune erreur.
    -> C'est pourquoi la CLI valide avec pydantic (`@validate_call` + types `ChunkSize`, `K`,
       `Query`, `FilePath`), puis intercepte `ValidationError` dans `__main__` :

    | Commande | Résultat |
    |---|---|
    | `search q --k abc` | `Error: --k='abc': Input should be a valid integer` |
    | `search q --k 5.0` | `Error: --k=5.0: Input should be a valid integer` |
    | `search q --k '"5"'` (chaîne) | `Error: --k='5': Input should be a valid integer` (mode strict) |
    | `search q --k 0` | `Error: --k=0: Input should be greater than or equal to 1` |

    -> Message propre sur `stderr`, code de sortie 1, pas de traceback.
    -> `strict=True` sur les entiers refuse aussi `True` et les chaînes de chiffres, que
       pydantic convertirait sinon en `1` ou en `5`.

## Phase 3 — Indexation

### Tâche 5 — Ingestion du corpus
🎯 Une fonction qui liste et lit les fichiers utiles de `data/raw/`.

📚 `pathlib`, encodage, fins de ligne, chemins relatifs (§1).

🛠️
**Architecture retenue** : un module par étape du pipeline, à plat dans `src/`
(`ingest.py`, puis `chunking.py`, `indexing.py`, `retrieval.py`, `evaluation.py`,
`generation.py`). `__main__.py` ne contient que la CLI. Les constantes par défaut sont
dans `src/config.py` (`RAW_DIR`, `EXTENSIONS`, `EXCLUDED_DIRS`).

**Pourquoi pas le `Pipeline` de chonkie pour l'ingestion** (testé) :
- il découpe bien (chunks ≤ 2000 caractères, offsets exacts),
- mais chaque document ne garde que `metadata = {"filename": "lora.md"}`, **jamais le chemin
  complet** : 170 noms distincts pour 206 fichiers (`README.md`, `index.md`…), donc impossible
  de reconstruire le `file_path` que la moulinette compare ;
- aussi : un seul découpeur par pipeline, pas d'exclusion de dossiers, une erreur de lecture
  arrête tout, pas de `tqdm`.
-> chonkie sera utilisé **seulement pour le découpage** (tâches 6 et 7), sur le contenu lu
   par `ingest.py`.

🛠️
- [x] Parcourir récursivement `data/raw/` et filtrer les extensions retenues à la tâche 1.
    -> `_list_files(root, extensions, excluded)` : `root.rglob("*")`, garde les fichiers dont
       `suffix` est dans `extensions` et dont aucun élément de `parts` n'est dans `excluded`.
    -> Résultat **trié** (`sorted`) : l'ordre de `rglob` dépend du système de fichiers, le tri
       rend l'index identique d'une machine à l'autre.
    -> 1969 fichiers `.py` / `.md` / `.txt` ; 1268 en excluant `tests`.
    -> Rappel : `p.parts` contient aussi `data`, `raw`, `vllm-0.10.1` → exclure un de ces noms
       viderait tout ; `p.relative_to(root).parts` limiterait le test à l'intérieur de la racine.
- [x] Lire chaque fichier en gérant les erreurs (encodage, fichier illisible) sans planter.
    -> `_read_file(path)` : `open(path, encoding="utf-8", newline="")` dans un `with`.
    -> Intercepte `UnicodeDecodeError` et `OSError` (fichier absent, dossier, permission) :
       avertissement sur `stderr` avec le chemin, puis `return None`. Pas de `except Exception`,
       qui cacherait de vrais bugs.

    | Cas testé | Résultat |
    |---|---|
    | `lora.md` | contenu lu |
    | `nope.md` | `None` + `Warning: cannot read nope.md: [Errno 2] No such file or directory` |
    | `data/raw` (dossier) | `None` + `[Errno 21] Is a directory` |
    | fichier non UTF-8 | `None` + `'utf-8' codec can't decode byte 0xe9…` |
    | fichier `\r\n` | `'a\r\nb\r\n'` (fins de ligne conservées) |

    -> Le message de `UnicodeDecodeError` ne contient pas le chemin → l'ajouter soi-même.
    -> mypy exige un `return None` **explicite** dans le `except` (type de retour `str | None`).
    -> Les fichiers vides ou faits d'espaces sont ignorés dans `ingest` (122 fichiers, surtout
       des `__init__.py`) : ils ne peuvent répondre à aucune question.
- [x] Construire le `file_path` exactement au format `data/raw/vllm-0.10.1/...`.
    -> Racine passée en **relatif** (`Path("data/raw")`) → chemins relatifs à la racine du
       projet ; `path.as_posix()` garantit des `/`.
    -> Le modèle pydantic `Document(file_path, content)` (dans `models.py`) transporte le
       résultat vers le découpage.
- [x] **Vérifier les offsets** : pour quelques sources du dataset, `contenu[first:last]` doit afficher le bon passage.
    -> Vérifié sur **toutes** les sources, pas seulement quelques-unes :

    | Corrigé | Sources | Introuvables | Plage hors du fichier |
    |---|---|---|---|
    | docs | 100 | 0 | 0 |
    | code | 99 | 0 | 0 |

    -> Exemple : « What activation formats does the fused batched MoE layer return? » →
       le passage commence bien par `def activation_formats(...)`.
- [x] Ajouter une barre `tqdm`.
    -> `tqdm(listed_files, desc="Reading files")`.

✅ Tu affiches le nombre de fichiers lus par extension, et les offsets du dataset tombent juste.
    -> **1847 documents en 0,1 s** : 1641 `.py`, 178 `.md`, 28 `.txt`
       (1969 fichiers − 122 vides). Offsets justes sur les deux corrigés.

🎤 Pourquoi la façon d'ouvrir le fichier (`newline`, `encoding`) peut-elle décaler tous les offsets ?
    -> Les offsets comptent des **caractères** dans le texte lu par Python, pas des octets sur
       le disque. Tout ce qui change ce texte décale les positions qui suivent.
    -> **`newline`** : par défaut (`None`), Python convertit `\r\n` en `\n` → un caractère de
       moins par ligne. Dans un fichier Windows, la position N du fichier réel ne correspond
       plus à la position N du texte lu, et l'écart grandit à chaque ligne.
       Mesuré : `vllm/model_executor/layers/quantization/utils/__init__.py` fait
       232 caractères avec `newline=None`, 235 avec `newline=""`.
    -> **`encoding`** : un caractère accentué ou un emoji fait 1 caractère en UTF-8 bien
       décodé, mais plusieurs avec un mauvais encodage (ex. `é` → `Ã©` en latin-1) → décalage
       après chaque caractère non ASCII. Sans `encoding`, Python prend celui du système,
       qui peut varier d'une machine à l'autre.
    -> **Choix fait : `encoding="utf-8", newline=""`**. Le texte lu est exactement celui du
       fichier sur le disque, donc les offsets désignent le contenu réel, quelle que soit la
       machine.
    -> Impact réel faible : 4 fichiers seulement en `\r\n` (3 dans `tests/`, 1 dans `vllm/`),
       aucune source publique dedans, et tout le corpus est en UTF-8 valide.
    -> La moulinette **ne lit pas** les fichiers du corpus (un chemin inexistant ne provoque
       aucune erreur, tâche 2) : elle compare seulement des plages. Les offsets doivent donc
       correspondre à ceux de la vérité terrain, d'où la vérification complète ci-dessus.
---

### Tâche 6 — Chunking Markdown avec chonkie
🎯 Découper les `.md` en chunks ≤ `max_chunk_size` avec leurs positions.

🛠️
**Architecture retenue** (`src/chunking.py`) : un découpeur par type de fichier, un seul code
de découpage.

| Fonction | Rôle |
|---|---|
| `_make_md_chunker(max_chunk_size)` | `RecursiveChunker` avec les règles Markdown |
| `_make_py_chunker(max_chunk_size)` | `RecursiveChunker` avec les règles Python (tâche 7) |
| `_chunk_doc(doc, chunker, max_chunk_size)` | un `Document` → liste de `Chunk`, avec garde-fou de taille |
| `chunk_documents(docs, max_chunk_size)` | **publique** : crée les découpeurs une fois, choisit selon l'extension (dict), `tqdm` |

Modèle pydantic ajouté : `Chunk(file_path, first_char_i, last_char_i, text)`.

- [x] Lire la doc de `chonkie.RecursiveChunker` (et sa recette markdown).
    -> Trois classes emboîtées : `RecursiveChunker` (l'outil) ← `RecursiveRules` (liste
       ordonnée) ← `RecursiveLevel` (une façon de couper : `delimiters`, `whitespace`,
       `include_delim`).
    -> Algorithme : couper au niveau 1 ; chaque morceau trop grand est recoupé au niveau
       suivant ; puis les morceaux voisins sont **regroupés** (glouton) tant qu'ils
       tiennent dans `chunk_size`.
    -> **Recettes (`from_recipe`) écartées** : elles importent `huggingface_hub` (absent)
       et se téléchargent depuis Hugging Face. L'import a lieu **même avec un fichier
       local** (`path=`), j'ai vérifié dans le code de chonkie. Les règles sont donc écrites
       à la main.
- [x] Attention : chonkie compte par défaut en **tokens**, le sujet en **caractères** → trouver comment configurer le tokenizer en mode caractères.
    -> Faux problème : `RecursiveChunker` utilise déjà `tokenizer="character"` par défaut.
    -> **Vrai piège : `chunk_size=2048` par défaut**, ce qui invaliderait tout le fichier
       de résultats. On passe toujours `chunk_size=max_chunk_size`.
- [x] Découper un fichier, afficher les chunks et leurs positions.
    -> Règles Markdown retenues :

    | # | Coupe sur | `include_delim` |
    |---|---|---|
    | 1 | `"\n# "`, `"\n## "`, `"\n### "`, `"\n#### "` | `"next"` (le titre ouvre le chunk suivant) |
    | 2 | `"\n\n"` (paragraphes) | `"prev"` |
    | 3 | `"\n"` (lignes) | `"prev"` |
    | 4 | `". "`, `"! "`, `"? "` (phrases) | `"prev"` |
    | 5 | espaces | |
    | 6 | rien = caractère par caractère (filet de sécurité) | |

    -> `lora.md` (9115 caractères) → 13 chunks contigus (fin de l'un = début du suivant,
       de 0 à la fin du fichier). Un chunk va de 4694 à 6099 sur `### Using API Endpoints` ;
       la source du corrigé est 4695 → 6098 (IoU ≈ 0,998).
    -> Les chunks commencent par `\n` à cause de `include_delim="next"` : sans conséquence,
       `text` reste égal à `content[start:end]`.
- [x] Vérifier pour **chaque** chunk : `contenu[start:end] == chunk.text` et `end - start <= max_chunk_size`.
    -> Vérifié par le main de `chunking.py` (`uv run python -m src.chunking [taille]`) :
       206 fichiers `.md`/`.txt` → **860 chunks** à 2000, **3352** à 500. Aucune erreur.
    -> **Sans le niveau 6**, chonkie a produit un chunk de **2517 caractères**
       (`tests/prompts/summary.txt`). Cause : chonkie regroupe parfois des lignes au-delà de
       `chunk_size`. Le niveau « caractères » recoupe alors ce bloc.
    -> Effet secondaire mesuré sur tout le corpus : **une seule** coupe au milieu d'un mot,
       à 2000 pile (`con|tact`), dans ce même `summary.txt` (sous-titres sur une seule
       ligne de 17 317 caractères). Ses 11 autres coupes tombent sur des fins de phrase,
       comme voulu. Aucune source des corrigés dans ce fichier → **pas de correction** :
       il faudrait réécrire le regroupement de chonkie pour un mot coupé dans un fichier de
       test.
    -> Garde-fou dans `_chunk_doc` : `ValueError` avec fichier, plage et taille si un chunk
       dépasse. On ne jette pas un chunk trop long en silence, cela ferait disparaître du
       contenu de l'index.

✅ Assertion vérifiée sur tous les `.md` du corpus.
    -> Et sur les `.txt`, découpés avec les mêmes règles (sans titre, le niveau 1 ne trouve
       rien et on passe aux paragraphes).

🎤 Pourquoi couper sur les titres plutôt que tous les N caractères ?
    -> Les sources du corrigé suivent la structure du document (une section, un
       paragraphe). Un chunk qui couvre la même section a un IoU élevé avec la source ; une
       coupe fixe tombe au milieu d'un mot, d'une phrase ou d'une section, et mélange deux
       sujets dans un même chunk.
    -> Mesuré, avec l'« atteignable » = il existe un chunk d'IoU ≥ 0,05 avec la source
       attendue (le meilleur recall possible si la recherche était parfaite) :

    | Règles (taille 2000) | Chunks `.md`/`.txt` | Sources docs atteignables |
    |---|---|---|
    | par défaut de chonkie (paragraphes d'abord) | 696 | 96 / 100 |
    | titres d'abord (retenu) | 860 | **99 / 100** |

    -> Un chunk centré sur une section a aussi un vocabulaire plus cohérent, ce qui aidera
       BM25.

---

### Tâche 7 — Chunking Python
🎯 Découper les `.py` selon leur structure (fonctions, classes).

🛠️
- [x] Lire la doc de `CodeChunker` (langage, taille, tokenizer en caractères).
    -> `CodeChunker(tokenizer="character", chunk_size=2048, language="auto")` : il analyse
       le code avec **tree-sitter** (arbre syntaxique) et regroupe les nœuds.
    -> **Deux défauts mesurés** sur les 1641 `.py` :
        1. **Positions en octets UTF-8, pas en caractères** : 588 chunks faux dans 63
           fichiers, tous ceux qui contiennent des caractères non ASCII (`é` = 2 octets →
           décalage). Exemple : `benchmarks/benchmark_dataset.py`, chunk annoncé
           12410 → 13997 (1587) pour un texte de 1585 caractères.
        2. **Dépasse la taille** : 4 chunks > 2000, jusqu'à 2027 (`flex_attention.py`),
           même après conversion des positions.
    -> Alternatives comparées (taille 2000) :

    | Méthode | Chunks | Max | Positions | Sources code atteignables | Temps |
    |---|---|---|---|---|---|
    | A. `CodeChunker` + conversion octets → caractères | 12 469 | 2027 ✘ | ✔ après correction | 98 / 99 | 6,6 s |
    | **B. `RecursiveChunker` + délimiteurs Python (retenu)** | 14 623 | 2000 ✔ | ✔ | 97 / 99 | 0,1 s |
    | C. `RecursiveChunker` par défaut | 10 481 | 2000 ✔ | ✔ | 97 / 99 | 0,2 s |
    | D. module `ast` (`lineno`/`end_lineno`) | non testé : plus de code, échoue sur un fichier mal formé | | | | |

    -> **Choix : B**. Même code que le Markdown (seules les règles changent), aucun piège
       d'offsets, facile à défendre en review. On perd 1 source atteignable sur 99 par
       rapport à A.
    -> Règles Python : niveaux 1-2 spécifiques, niveaux 3-6 comme le Markdown (sans les
       phrases, sans intérêt dans du code).

    | # | Coupe sur | `include_delim` |
    |---|---|---|
    | 1 | `"\nclass "`, `"\ndef "`, `"\nasync def "` | `"next"` |
    | 2 | `"\n    def "`, `"\n    async def "` (méthodes, 4 espaces) | `"next"` |
    | 3 | `"\n\n"` | `"prev"` |
    | 4 | `"\n"` | `"prev"` |
    | 5 | espaces | |
    | 6 | caractère par caractère | |

    -> Limite connue : un **décorateur** (`@property`) reste à la fin du chunk précédent,
       car la coupe se fait sur `"\ndef "`. Ajouter `"\n@"` coupe alors entre le
       décorateur et le `def` : même score atteignable (97), donc version simple gardée.
- [x] Découper un fichier connu (ex. `vllm/lora/request.py`) et vérifier que les fonctions ne sont pas coupées au hasard.
    -> 3 chunks : `0 → 226` (en-tête de licence et imports), `226 → 2162`
       (`class LoRARequest(...)`), `2162 → 3178` (`def local_path(self, value)`). Les
       coupes tombent sur la classe et sur une méthode.
- [x] Mêmes vérifications que la tâche 6 (offsets + taille).
    -> 1641 `.py` → **14 623 chunks** à 2000, 56 665 à 500. Toutes les assertions passent.
- [x] Que deviennent une très longue fonction et un fichier avec erreur de syntaxe ?
    -> **Fonction longue** (test fabriqué : 3401 caractères, 150 lignes sans ligne vide) :
       coupée en `0 → 2000`, `2000 → 2201`, `2201 → 3401`. La première coupe tombe au
       milieu d'une ligne (`compute(9` | `0)`) : c'est le regroupement de lignes de chonkie
       qui dépasse, puis le niveau « caractères » qui recoupe (même cause que les 2517 de
       la tâche 6). Aucun `.py` du corpus n'est concerné.
    -> **Erreur de syntaxe** : aucun effet, la stratégie B ne fait aucune analyse
       syntaxique, elle cherche seulement des délimiteurs. (Avec `ast`, `ast.parse` lèverait
       une `SyntaxError` ; tree-sitter, lui, tolère les erreurs.)

✅ Les deux stratégies tournent sur tout le corpus, toutes les assertions passent.
    -> `chunk_documents` sur les 1847 documents : **15 483 chunks** (860 + 14 623) en
       0,2 s. `make lint` passe sans erreur.
    -> Effet de la taille sur les sources atteignables :

    | `max_chunk_size` | Chunks | Docs atteignables | Code atteignables | Temps |
    |---|---|---|---|---|
    | 2000 | 15 483 | 99 / 100 | 97 / 99 | 0,2 s |
    | 1000 | 30 917 | 100 / 100 | 98 / 99 | 0,3 s |
    | 500 | 60 017 | 100 / 100 | 98 / 99 | 0,5 s |

    -> Plus petit = plus de chunks atteignables, mais aussi plus de candidats pour la
       recherche et moins de contexte par chunk. À trancher avec le recall réel
       (tâche 13).

🎤 En quoi tes deux stratégies sont-elles « distinctes » au sens du sujet ?
    -> Elles coupent selon la **structure propre à chaque format** : les titres pour le
       Markdown (sections), les `class`/`def` pour le Python (unités de code). Les
       niveaux 1-2 diffèrent, et la coupe en phrases n'existe que pour le texte.
    -> Le code est mutualisé (`_chunk_doc`) : seules les règles changent, choisies par
       extension dans `chunk_documents`. Ajouter un format = une fonction `_make_*` et une
       ligne dans le dictionnaire.

---

### Tâche 8 — Tokenisation pour la recherche
🎯 Une fonction qui transforme un texte en liste de termes.

**Pourquoi pas `bm25s.tokenize`** : il garde `enable_lora` entier et donne `llmengine` pour
`LLMEngine`, sans découper les identifiants. Or presque toutes les questions en contiennent
(`trust_remote_code`, `FP8_MIN`…) et le corpus est surtout du code.
**rank-bm25** (utilisé par un collègue) n'a pas de tokenizer non plus : il attend des listes
de termes, comme bm25s. Le choix de la bibliothèque se pose à la tâche 9 ; on garde bm25s
(sauvegarde/chargement intégrés, scores précalculés).

**Architecture** (`src/tokenizer.py`, pas `tokenize.py`, nom d'un module standard) :

| Élément | Rôle |
|---|---|
| `_WORD_RE`, `_CAMEL_RE`, `_STOPWORDS` | constantes de module, compilées une seule fois |
| `_split_snake(word)` | coupe aux `_`, sans morceaux vides |
| `_split_camel(part)` | coupe aux changements de casse |
| `tokenize(text, remove_stopwords=REMOVE_STOPWORDS)` | **publique** : enchaîne tout, filtre à la fin |

Le chemin d'un texte :
```
"How does LLMEngine handle enable_lora?"
 1. mots          : How, does, LLMEngine, handle, enable_lora
 2-3. morceaux    : LLMEngine → LLM, Engine ; enable_lora → enable, lora
 4. assemblage    : mot entier + morceaux s'il y en a plus d'un, en minuscules
 5. filtre        : stop words et termes d'une lettre
 → ['how', 'does', 'llmengine', 'llm', 'engine', 'handle', 'enable_lora', 'enable', 'lora']
```

🛠️
- [x] Écrire la tokenisation, la tester sur `"How does LLMEngine handle enable_lora?"`.
    -> Résultat ci-dessus. Le main de `tokenizer.py` (`uv run python -m src.tokenizer`)
       vérifie 15 cas (`OK`/`BAD`) et affiche 4 phrases, dont la chaîne vide (→ `[]`).
    -> **Mots** : `[A-Za-z0-9_]+` garde le `_` pour découper ensuite.
    -> **snake_case** : `split("_")` puis on garde les morceaux non vides
       (`__init__` → `init`, `a__b` → `a`, `b`).
       Piège rencontré : supprimer (`pop`) dans une liste pendant qu'on la parcourt saute
       des éléments (`___` laissait `['', '']`). On construit une **nouvelle** liste.
    -> **CamelCase**, une forme par ligne de la regex :

    | Forme | Exemple |
    |---|---|
    | `[A-Z]{2,}(?=s(?![a-z]))` | sigle au pluriel : `GPUs` → `GPU`, `s` |
    | `[A-Z]+(?=[A-Z][a-z])` | sigle avant un mot : `LLM` dans `LLMEngine` |
    | `[A-Z]?[a-z]+[0-9]*` | mot avec ses chiffres : `Engine`, `Qwen3` |
    | `[A-Z]+[0-9]*` | sigle avec ses chiffres : `HTTP`, `FP8` |
    | `[0-9]+` | nombre seul : `2048` |

    -> La 1re forme a été ajoutée après une recherche dans le corpus : sans elle,
       `GPUs` (279 fois dans les `.py`) donnait `GP`, `Us`, et `IDs` (227 fois) `I`, `Ds`.
       Bonus : `GPUs` donne `gpu`, donc une question sur « GPU » retrouve « GPUs ».
    -> Limites connues : `ROCm` → `RO`, `Cm` ; `MoE` → `Mo`, `E` ; `HANDLEhandle` →
       `HANDL`, `Ehandle` (ambigu : aucune regex ne peut savoir). Le mot entier (`rocm`,
       `moe`) étant toujours gardé, une question qui le cite le retrouve quand même.
    -> **Doublons** : on supprime seulement ceux **d'un même mot** (`class` donnait
       `class`, `class` : mot entier + son unique morceau). Ceux qui viennent de **deux mots
       différents** sont gardés (`vLLM` et `LLM` → deux `llm`) : BM25 compte les
       occurrences, donc pas de `set()` sur le résultat.
    -> **Minuscules** sur le mot entier aussi : pour BM25, `LLM` et `llm` seraient deux
       termes différents.
- [x] Décider : stemming oui/non ? stop words oui/non ? → noter pour comparer plus tard.
    -> **Stop words : oui, réglable.** Liste `STOPWORDS_EN` de bm25s (33 mots, dont les
       mots-clés Python `if`, `for`, `in`, `is`, `not`, `and`, `or`), convertie en
       `frozenset` : `in` sur un tuple compare élément par élément, sur un ensemble c'est
       immédiat (et `frozenset` empêche de modifier la constante). Attention : `how`,
       `what`, `does` n'y sont **pas**.
    -> Réglage : `REMOVE_STOPWORDS` dans `config.py`, valeur par défaut du paramètre
       `remove_stopwords`. Une seule source pour l'indexation et la recherche, sinon les
       termes ne correspondraient plus.
       Piège rencontré : `and` passe avant `or`. Il faut
       `len(t) > 1 and (t not in _STOPWORDS or not remove_stopwords)` ; sans les
       parenthèses, `remove_stopwords=False` laissait aussi passer les termes d'une
       lettre.
    -> **Termes d'une lettre : toujours retirés** (`s` de `What's`/`GPUs`, `v` de `vLLM`,
       variables `i`, `x`).
    -> **Stemming : non pour l'instant.** Il demande une dépendance (`PyStemmer`, absent) et
       peut abîmer les identifiants. À tester à la tâche 13.
    -> **Mesuré sur les 15 483 chunks** (taille 2000) :

    | `remove_stopwords` | Temps | Termes | Distincts | Chunks sans terme |
    |---|---|---|---|---|
    | `True` | 1,4 s | 2 588 902 | 57 795 | 2 |
    | `False` | 1,4 s | 2 820 243 (+9 %) | 57 827 | 2 |

    -> Termes les plus fréquents (stop words retirés) : `self` (54 456), `config`, `model`,
       `size`, `torch`, `num`, `vllm`, `none`, `tensor`, `def`, `from`, `import`.
       `self`, `def`, `from`, `import`, `none` sont les « stop words du code » : piste à
       tester à la tâche 13 (BM25 les pèse déjà peu, puisqu'ils sont partout).
    -> **2 chunks ne donnent aucun terme** : vérifier à la tâche 9 que bm25s accepte une
       liste vide.

✅ Le même tokenizer sert aux chunks et aux questions.
    -> `tokenize` est la seule fonction publique, avec un réglage centralisé dans
       `config.py`. À la tâche 9, enregistrer aussi ce réglage avec l'index serait plus sûr
       (un `index` lancé avec `True` puis un `search` avec `False` ne correspondraient
       plus).

🎤 Pourquoi garder à la fois `enable_lora` et `enable`, `lora` ?
    -> **Les morceaux** servent quand la question n'écrit pas l'identifiant : « How do I
       enable LoRA? » partage `enable` et `lora` avec un chunk qui contient seulement
       `enable_lora`. Sans découpage, aucun terme commun.
    -> **Le mot entier** sert quand la question cite l'identifiant exact : `enable_lora` est
       beaucoup plus **rare** que `enable` ou `lora`, donc son IDF est élevé. Le chunk qui
       le contient vraiment passe devant ceux qui parlent seulement de « lora » ou
       d'« enable » séparément.
    -> Garder les deux = **rappel** (les morceaux trouvent plus de chunks) **et précision**
       (le mot entier classe mieux le bon).
