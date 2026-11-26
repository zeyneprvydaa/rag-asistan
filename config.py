"""Shared settings for the local RAG assistant."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "knowledge.db"
SOURCE_DIR = BASE_DIR / "source"
ALIAS_PATH = BASE_DIR / "aliases_tr.txt"

# Embedding model (E5 expects these prefixes)
EMBED_MODEL_NAME = "intfloat/multilingual-e5-base"
QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "

# LLM served by Foundry Local
LLM_ALIAS = "qwen3.5-2b"

# Retrieval
TOP_K = 3          # records fetched per question
THRESHOLD = 0.82   # records scoring below this are never used
W_QUESTION = 0.6   # weight of the question-line similarity in the hybrid score