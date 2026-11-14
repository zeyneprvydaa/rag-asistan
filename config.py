"""Ortak ayarlar: tüm scriptler buradan import eder."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "veritabani.db"
SOURCE_DIR = BASE_DIR / "source"

# Çok dilli (TR + EN) embedding modeli. E5 ailesinde prefix zorunludur.
EMBED_MODEL_NAME = "intfloat/multilingual-e5-base"
QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "

# test.py'de çalıştığı kanıtlanmış model
LLM_ALIAS = "qwen3.5-2b"

TOP_K = 3
W_QUESTION = 0.6
THRESHOLD = 0.80