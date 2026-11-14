"""W_QUESTION değerlerini tarar: hangi ağırlık en çok soruyu doğru eşleştiriyor?"""
import numpy as np
from sentence_transformers import SentenceTransformer

from config import EMBED_MODEL_NAME, QUERY_PREFIX
from retriever import Retriever
from test_retrieval import TESTS

r = Retriever(SentenceTransformer(EMBED_MODEL_NAME))
first_lines = [c.split("\n")[0] for c in r.chunks]
qvecs = {q: r.model.encode(QUERY_PREFIX + q, normalize_embeddings=True) for q, _ in TESTS}

print("w = soru vektörünün ağırlığı (0 = sadece tüm chunk, 1 = sadece soru)\n")
for w in np.arange(0, 1.01, 0.1):
    ok_scores, bad_scores, rank1, n_exp = [], [], 0, 0
    for q, exp in TESTS:
        s = w * (r.question @ qvecs[q]) + (1 - w) * (r.full @ qvecs[q])
        order = np.argsort(-s)
        if exp is None:
            bad_scores.append(s[order[0]])
        else:
            n_exp += 1
            i = first_lines.index(exp)
            rank1 += int(order[0] == i)
            ok_scores.append(s[i])
    lo, hi = min(ok_scores), max(bad_scores)
    print(f"w={w:.1f}  sıra1={rank1}/{n_exp}  min_doğru={lo:.3f}  "
          f"max_reddedilmeli={hi:.3f}  boşluk={lo - hi:+.3f}")