"""Default settings of the RAG system."""

RAW_DIR: str = "data/raw"
EXTENSIONS: set[str] = {".py", ".md", ".txt"}
EXCLUDED_DIRS: set[str] = set()
REMOVE_STOPWORDS: bool = True
PROCESSED_DIR: str = "data/processed"
