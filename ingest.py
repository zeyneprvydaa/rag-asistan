"""Ingestion: reads source/*.txt and aliases_tr.txt, embeds them, stores everything in SQLite.

Source format: records are separated by a blank line; the first line of a record is the
question, the rest is the answer. Run again whenever a source file, the alias file or the
embedding model changes:  python ingest.py
"""
import glob
import json
import os
import sqlite3

from sentence_transformers import SentenceTransformer

import config


def read_records():
    """Return [(file_name, chunk)] for every record in source/*.txt."""
    records = []
    for path in sorted(glob.glob(os.path.join(str(config.SOURCE_DIR), "*.txt"))):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read().replace("\r\n", "\n")
        for block in text.split("\n\n"):
            block = block.strip()
            if block:
                records.append((os.path.basename(path), block))
    return records


def read_aliases():
    """Return {first line of a record: [Turkish question, ...]} from aliases_tr.txt."""
    aliases = {}
    path = str(config.ALIAS_PATH)
    if not os.path.exists(path):
        print("Uyarı: aliases_tr.txt bulunamadı, Türkçe takma sorular kullanılmayacak.")
        return aliases
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("||") if p.strip()]
            if len(parts) >= 2:
                aliases.setdefault(parts[0], []).extend(parts[1:])
    return aliases


def encode(model, prefix, texts):
    """Embed texts with an E5 prefix; vectors are L2-normalized."""
    if not texts:
        return []
    return model.encode(
        [prefix + t for t in texts],
        batch_size=16, normalize_embeddings=True, show_progress_bar=False,
    )


def create_tables(cur):
    cur.execute("DROP TABLE IF EXISTS aliases")
    cur.execute("DROP TABLE IF EXISTS documents")
    cur.execute(
        """CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            text TEXT,
            embedding_full TEXT,
            embedding_question TEXT)"""
    )
    cur.execute(
        """CREATE TABLE aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            question TEXT,
            embedding TEXT)"""
    )


def main():
    records = read_records()
    aliases = read_aliases()
    n_files = len({source for source, _ in records})
    print(f"{n_files} dosya, {len(records)} chunk bulundu.")

    first_lines = [chunk.split("\n")[0].strip() for _, chunk in records]
    for key in aliases:
        if key not in first_lines:
            print(f"UYARI: takma ad anahtarı hiçbir kayıtla eşleşmedi: {key!r}")

    print(f"Embedding modeli yükleniyor ({config.EMBED_MODEL_NAME})...")
    model = SentenceTransformer(config.EMBED_MODEL_NAME)

    full_vecs = encode(model, config.PASSAGE_PREFIX, [chunk for _, chunk in records])
    question_vecs = encode(model, config.QUERY_PREFIX, first_lines)

    alias_rows = []  # (record index, Turkish question)
    for idx, first_line in enumerate(first_lines):
        for question in aliases.get(first_line, []):
            alias_rows.append((idx, question))
    alias_vecs = encode(model, config.QUERY_PREFIX, [q for _, q in alias_rows])

    conn = sqlite3.connect(str(config.DB_PATH))
    cur = conn.cursor()
    create_tables(cur)

    ids = []
    for (source, chunk), v_full, v_question in zip(records, full_vecs, question_vecs):
        cur.execute(
            "INSERT INTO documents (source, text, embedding_full, embedding_question) VALUES (?,?,?,?)",
            (source, chunk, json.dumps(v_full.tolist()), json.dumps(v_question.tolist())),
        )
        ids.append(cur.lastrowid)
    for (idx, question), vec in zip(alias_rows, alias_vecs):
        cur.execute(
            "INSERT INTO aliases (document_id, question, embedding) VALUES (?,?,?)",
            (ids[idx], question, json.dumps(vec.tolist())),
        )
    conn.commit()
    conn.close()
    print(f"✅ {len(records)} kayıt ve {len(alias_rows)} Türkçe takma soru kaydedildi.")


if __name__ == "__main__":
    main()