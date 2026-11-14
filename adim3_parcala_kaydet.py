"""Ingestion: source/*.txt dosyalarını parçalar, embed eder, SQLite'a yazar."""
import json
import sqlite3

from sentence_transformers import SentenceTransformer

from config import DB_PATH, EMBED_MODEL_NAME, PASSAGE_PREFIX, QUERY_PREFIX, SOURCE_DIR


def chunk_file(path):
    """Çift satır başıyla ayrılmış blokları (soru + cevap) chunk olarak al."""
    text = path.read_text(encoding="utf-8")
    return [b.strip() for b in text.split("\n\n") if b.strip()]


def main():
    files = sorted(SOURCE_DIR.glob("*.txt"))
    if not files:
        raise SystemExit(f"HATA: {SOURCE_DIR} içinde .txt bulunamadı. DB'ye dokunulmadı.")

    rows = [(f.name, c) for f in files for c in chunk_file(f)]
    print(f"{len(files)} dosya, {len(rows)} chunk bulundu.")

    print(f"Embedding modeli yükleniyor ({EMBED_MODEL_NAME})...")
    model = SentenceTransformer(EMBED_MODEL_NAME)

    # 1) Tüm chunk (soru + cevap), doküman prefix'i ile
    full_vecs = model.encode(
        [PASSAGE_PREFIX + c for _, c in rows],
        batch_size=32, normalize_embeddings=True, show_progress_bar=True,
    )
    # 2) Sadece ilk satır (soru), sorgu prefix'i ile
    question_vecs = model.encode(
        [QUERY_PREFIX + c.split("\n", 1)[0] for _, c in rows],
        batch_size=32, normalize_embeddings=True, show_progress_bar=True,
    )

    conn = sqlite3.connect(DB_PATH)
    try:
        with conn:
            conn.execute("DROP TABLE IF EXISTS dokumanlar")
            conn.execute(
                """CREATE TABLE dokumanlar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kaynak TEXT,
                    paragraf TEXT,
                    embedding TEXT,
                    embedding_soru TEXT)"""
            )
            conn.executemany(
                "INSERT INTO dokumanlar (kaynak, paragraf, embedding, embedding_soru) "
                "VALUES (?,?,?,?)",
                [
                    (src, c, json.dumps(f.tolist()), json.dumps(q.tolist()))
                    for (src, c), f, q in zip(rows, full_vecs, question_vecs)
                ],
            )
    finally:
        conn.close()
    print(f"✅ {len(rows)} chunk veritabanına kaydedildi: {DB_PATH}")


if __name__ == "__main__":
    main()