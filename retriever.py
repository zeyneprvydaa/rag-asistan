"""Hibrit arama: soru benzerliği (Türkçe takma adlar dahil) + tam metin benzerliği."""
import json
import sqlite3

import numpy as np
from sentence_transformers import SentenceTransformer

import config


def _norm(m):
    m = np.asarray(m, dtype=np.float32)
    n = np.linalg.norm(m, axis=1, keepdims=True)
    return m / np.clip(n, 1e-9, None)


class Retriever:
    def __init__(self, model=None):
        # Dışarıdan hazır model verilirse onu kullan (modeli tekrar yüklememek için)
        self.model = model if model is not None else SentenceTransformer(config.EMBED_MODEL_NAME)
        conn = sqlite3.connect(str(config.DB_PATH))
        rows = conn.execute(
            "SELECT id, kaynak, paragraf, embedding, embedding_soru FROM dokumanlar ORDER BY id"
        ).fetchall()
        try:
            alias = conn.execute("SELECT dokuman_id, embedding FROM takma_adlar").fetchall()
        except sqlite3.OperationalError:
            alias = []
        conn.close()

        self.kaynak = [r[1] for r in rows]
        self.chunks = [r[2] for r in rows]
        self.full = _norm([json.loads(r[3]) for r in rows])
        self.question = _norm([json.loads(r[4]) for r in rows])

        pos = {r[0]: i for i, r in enumerate(rows)}
        alias = [a for a in alias if a[0] in pos]
        self.alias_owner = np.array([pos[a[0]] for a in alias], dtype=int)
        self.alias = _norm([json.loads(a[1]) for a in alias]) if alias else None

    def search(self, query, k=config.TOP_K):
        q = self.model.encode(
            [config.QUERY_PREFIX + query], normalize_embeddings=True, show_progress_bar=False
        )[0]
        full_sim = self.full @ q
        q_sim = self.question @ q
        if self.alias is not None and len(self.alias_owner):
            a_sim = self.alias @ q
            for owner, s in zip(self.alias_owner, a_sim):
                if s > q_sim[owner]:
                    q_sim[owner] = s  # en iyi (İngilizce soru ya da Türkçe takma ad) kazanır
        score = config.W_QUESTION * q_sim + (1 - config.W_QUESTION) * full_sim
        order = np.argsort(-score)[:k]
        return [(self.kaynak[i], self.chunks[i], float(score[i])) for i in order]