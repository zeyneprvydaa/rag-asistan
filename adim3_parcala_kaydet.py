"""Kaynak dosyaları (source/*.txt) ve Türkçe takma soruları (aliases_tr.txt) veritabanına işler."""
import glob
import json
import os
import sqlite3

from sentence_transformers import SentenceTransformer

import config

ALIAS_PATH = os.path.join(str(config.BASE_DIR), "aliases_tr.txt")


def kayitlari_oku():
    """source/*.txt -> [(dosya_adi, chunk)]. Kayıtlar boş satırla ayrılır."""
    sonuc = []
    for yol in sorted(glob.glob(os.path.join(str(config.SOURCE_DIR), "*.txt"))):
        with open(yol, "r", encoding="utf-8") as f:
            metin = f.read().replace("\r\n", "\n")
        for blok in metin.split("\n\n"):
            blok = blok.strip()
            if blok:
                sonuc.append((os.path.basename(yol), blok))
    return sonuc


def takma_adlari_oku():
    """aliases_tr.txt -> {kaydın ilk satırı: [Türkçe soru, ...]}"""
    sonuc = {}
    if not os.path.exists(ALIAS_PATH):
        print("Uyarı: aliases_tr.txt bulunamadı, takma ad kullanılmayacak.")
        return sonuc
    with open(ALIAS_PATH, "r", encoding="utf-8") as f:
        for satir in f:
            satir = satir.strip()
            if not satir or satir.startswith("#"):
                continue
            parcalar = [p.strip() for p in satir.split("||") if p.strip()]
            if len(parcalar) >= 2:
                sonuc.setdefault(parcalar[0], []).extend(parcalar[1:])
    return sonuc


def main():
    kayitlar = kayitlari_oku()
    takma = takma_adlari_oku()
    dosya_sayisi = len({k for k, _ in kayitlar})
    print(f"{dosya_sayisi} dosya, {len(kayitlar)} chunk bulundu.")

    ilk_satirlar = [c.split("\n")[0].strip() for _, c in kayitlar]
    eslesmeyen = [k for k in takma if k not in ilk_satirlar]
    for k in eslesmeyen:
        print(f"UYARI: takma ad anahtarı hiçbir kayıtla eşleşmedi: {k!r}")

    print(f"Embedding modeli yükleniyor ({config.EMBED_MODEL_NAME})...")
    model = SentenceTransformer(config.EMBED_MODEL_NAME)

    tam = model.encode(
        [config.PASSAGE_PREFIX + c for _, c in kayitlar],
        batch_size=16, normalize_embeddings=True, show_progress_bar=False,
    )
    soru = model.encode(
        [config.QUERY_PREFIX + s for s in ilk_satirlar],
        batch_size=16, normalize_embeddings=True, show_progress_bar=False,
    )

    alias_satirlari = []  # (kayıt_indeksi, soru_metni)
    for idx, ilk in enumerate(ilk_satirlar):
        for s in takma.get(ilk, []):
            alias_satirlari.append((idx, s))
    if alias_satirlari:
        alias_vek = model.encode(
            [config.QUERY_PREFIX + s for _, s in alias_satirlari],
            batch_size=16, normalize_embeddings=True, show_progress_bar=False,
        )
    else:
        alias_vek = []

    conn = sqlite3.connect(str(config.DB_PATH))
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS takma_adlar")
    cur.execute("DROP TABLE IF EXISTS dokumanlar")
    cur.execute(
        """CREATE TABLE dokumanlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kaynak TEXT, paragraf TEXT, embedding TEXT, embedding_soru TEXT)"""
    )
    cur.execute(
        """CREATE TABLE takma_adlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dokuman_id INTEGER, soru TEXT, embedding TEXT)"""
    )
    ids = []
    for (kaynak, chunk), v_tam, v_soru in zip(kayitlar, tam, soru):
        cur.execute(
            "INSERT INTO dokumanlar (kaynak, paragraf, embedding, embedding_soru) VALUES (?,?,?,?)",
            (kaynak, chunk, json.dumps(v_tam.tolist()), json.dumps(v_soru.tolist())),
        )
        ids.append(cur.lastrowid)
    for (idx, s), v in zip(alias_satirlari, alias_vek):
        cur.execute(
            "INSERT INTO takma_adlar (dokuman_id, soru, embedding) VALUES (?,?,?)",
            (ids[idx], s, json.dumps(v.tolist())),
        )
    conn.commit()
    conn.close()
    print(f"✅ {len(kayitlar)} kayıt ve {len(alias_satirlari)} Türkçe takma soru kaydedildi.")


if __name__ == "__main__":
    main()