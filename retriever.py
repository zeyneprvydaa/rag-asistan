"""Hibrit retriever: soru vektörü ve tüm chunk vektörünün ağırlıklı ortalaması."""
import json
import sqlite3

import numpy as np

from config import DB_PATH, QUERY_PREFIX, TOP_K, W_QUESTION


def _normalize(m):
    return m / np.linalg.norm(m, axis=1, keepdims=True)


class Retriever:
    def __init__(self, embed_model):
        self.model = embed_model
        conn = sqlite3.connect(DB_PATH)
        try:
            rows = conn.execute(
                "SELECT kaynak, paragraf, embedding, embedding_soru FROM dokumanlar"
            ).fetchall()
        finally:
            conn.close()
        if not rows:
            raise RuntimeError("Veritabanı boş. Önce adim3_parcala_kaydet.py çalıştır.")

        self.sources = [r[0] for r in rows]
        self.chunks = [r[1] for r in rows]
        self.full = _normalize(np.array([json.loads(r[2]) for r in rows], dtype=np.float32))
        self.question = _normalize(np.array([json.loads(r[3]) for r in rows], dtype=np.float32))

    def search(self, query, k=TOP_K):
        q = self.model.encode(QUERY_PREFIX + query, normalize_embeddings=True)
        scores = W_QUESTION * (self.question @ q) + (1 - W_QUESTION) * (self.full @ q)
        top = np.argsort(-scores)[:k]
        return [(self.sources[i], self.chunks[i], float(scores[i])) for i in top]