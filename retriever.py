"""Hybrid retrieval over the SQLite knowledge base.

Score = W_QUESTION * question_similarity + (1 - W_QUESTION) * full_text_similarity
where question_similarity is the best of: the English question line of the record and
any of its Turkish alias questions (aliases_tr.txt).
"""
import json
import sqlite3

import numpy as np
from sentence_transformers import SentenceTransformer

import config


def normalize(matrix):
    """L2-normalize rows so a dot product equals cosine similarity."""
    matrix = np.asarray(matrix, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.clip(norms, 1e-9, None)


class Retriever:
    def __init__(self, model=None):
        # Reuse an already loaded embedding model when one is passed in
        self.model = model if model is not None else SentenceTransformer(config.EMBED_MODEL_NAME)

        conn = sqlite3.connect(str(config.DB_PATH))
        rows = conn.execute(
            "SELECT id, source, text, embedding_full, embedding_question FROM documents ORDER BY id"
        ).fetchall()
        try:
            alias_rows = conn.execute("SELECT document_id, embedding FROM aliases").fetchall()
        except sqlite3.OperationalError:  # database built without aliases
            alias_rows = []
        conn.close()

        self.sources = [r[1] for r in rows]
        self.chunks = [r[2] for r in rows]
        self.full = normalize([json.loads(r[3]) for r in rows])
        self.question = normalize([json.loads(r[4]) for r in rows])

        # Alias vectors and, for each one, the index of the record it belongs to
        position = {r[0]: i for i, r in enumerate(rows)}
        alias_rows = [a for a in alias_rows if a[0] in position]
        self.alias_owner = np.array([position[a[0]] for a in alias_rows], dtype=int)
        self.alias = normalize([json.loads(a[1]) for a in alias_rows]) if alias_rows else None

    def search(self, query, k=config.TOP_K):
        """Return the k best records as [(source, chunk, score)], best first."""
        q = self.model.encode(
            [config.QUERY_PREFIX + query], normalize_embeddings=True, show_progress_bar=False
        )[0]
        full_sim = self.full @ q
        question_sim = self.question @ q

        # A Turkish alias can raise a record's question similarity, never lower it
        if self.alias is not None and len(self.alias_owner):
            alias_sim = self.alias @ q
            for owner, sim in zip(self.alias_owner, alias_sim):
                if sim > question_sim[owner]:
                    question_sim[owner] = sim

        score = config.W_QUESTION * question_sim + (1 - config.W_QUESTION) * full_sim
        order = np.argsort(-score)[:k]
        return [(self.sources[i], self.chunks[i], float(score[i])) for i in order]