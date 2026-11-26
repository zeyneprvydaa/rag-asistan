"""Uçtan uca değerlendirme: arama + model cevabını ölçer, degerlendirme.md üretir.

Çalıştırma:  python test_end_to_end.py   (açık asistan varsa önce q ile kapat)

"Otomatik" sütunu kaba bir anahtar kelime kontrolüdür. "Elle değerlendirme" sütunu
cevapların okunmasıyla yazılmıştır (MANUAL sözlüğü). Model, kaynaklar ya da ayarlar
değişirse cevapları yeniden okuyup MANUAL'ı güncelle.
"""
import time

from sentence_transformers import SentenceTransformer

from config import BASE_DIR, EMBED_MODEL_NAME, LLM_ALIAS, THRESHOLD, TOP_K, W_QUESTION
from rag_asistan import answer, load_llm
from retriever import Retriever

OK, WARN, BAD = "✅", "⚠️", "❌"

# (soru, cevapta geçmesi beklenen kelimelerden herhangi biri; None = reddedilmeli)
TESTS = [
    ("TEKNOFEST nedir?", ["festival", "havacılık", "aerospace"]),
    ("What is TEKNOFEST?", ["festival", "aerospace", "largest"]),
    ("TEKNOFEST'e giriş ücretli mi?", ["ücretsiz", "değildir", "free"]),
    ("Is there an admission fee for the festival?", ["no admission", "free", "no fee"]),
    ("TEKNOFEST ne zaman yapılır?", ["her yıl", "farklı", "every year", "different"]),
    ("TEKNOFEST'e ziyaretçi olarak nasıl katılırım?", ["kayıt", "qr", "registration"]),
    ("TEKNOFEST hangi alanları kapsıyor?", ["yapay zeka", "artificial intelligence", "havacılık", "aviation"]),
    ("Rapor şablonlarını nereden indirebilirim?", ["şartname", "belge", "specification", "document"]),
    ("Milli Teknoloji Hamlesi nedir?", ["vizyon", "kalkınma", "vision", "development"]),
    ("Microsoft 365 Education nedir?", ["platform"]),
    ("What is Microsoft 365 Education?", ["platform"]),
    ("Microsoft 365 Education kaç para?", ["kademe", "üç", "three", "tier", "satış", "sales", "partner"]),
    ("Teams'e nasıl giriş yaparım?", ["e-posta", "şifre", "email", "password"]),
    ("How do I sign in to Teams?", ["email", "password", "sign in"]),
    ("Windows 11'e geçmeli miyim?", ["hız", "güvenlik", "speed", "security", "yeni"]),
    ("Windows 10 uygulamalarım Windows 11'de çalışır mı?", ["uyumlu", "compatible", "çalışır"]),
    ("Copilot+ PC nedir?", ["yapay zeka", "ai", "on-device", "cihaz"]),
    ("OneDrive hesabını kim yönetir?", ["okul", "school", "yönetici", "administrator"]),
    ("TEKNOFEST'te kaç takım yarışır?", None),
    ("Microsoft 365 A3 lisansı kaç dolar?", None),
    ("Bitcoin fiyatı nedir?", None),
    ("What is the capital of France?", None),
    ("Bugün hava nasıl?", None),
]

# Cevapların elle okunmasıyla yazılan değerlendirme (soru -> (işaret, not)).
MANUAL = {
    "TEKNOFEST nedir?": (OK, "Doğru"),
    "What is TEKNOFEST?": (OK, "Doğru, kaynakla birebir"),
    "TEKNOFEST'e giriş ücretli mi?": (OK, "Doğru"),
    "Is there an admission fee for the festival?": (OK, "Doğru"),
    "TEKNOFEST ne zaman yapılır?": (OK, "Doğru"),
    "TEKNOFEST'e ziyaretçi olarak nasıl katılırım?": (OK, "Doğru, QR kodu ayrıntısı eksik"),
    "TEKNOFEST hangi alanları kapsıyor?": (WARN, "Kapsam doğru; çeviri hatası: 'environment' yerine 'çeviklik'"),
    "Rapor şablonlarını nereden indirebilirim?": (WARN, "Sayfa adı yanlış çevrilmiş: 'Sınavlar ve Belgeler' (kaynakta 'specifications and documents')"),
    "Milli Teknoloji Hamlesi nedir?": (OK, "Doğru"),
    "Microsoft 365 Education nedir?": (WARN, "Anlam kayması: kurumlar yerine 'eğitimciler', cümle bozuk"),
    "What is Microsoft 365 Education?": (OK, "Doğru, kaynakla birebir"),
    "Microsoft 365 Education kaç para?": (WARN, "Fiyat olmadığını söylemesi doğru; üç kademe ve satış ortağı bilgisini vermiyor"),
    "Teams'e nasıl giriş yaparım?": (OK, "Doğru (soruyu tekrar ederek başlıyor)"),
    "How do I sign in to Teams?": (OK, "Doğru, kaynakla birebir"),
    "Windows 11'e geçmeli miyim?": (BAD, "Kaynakta olmayan iddialar: 'zorunlu değildir', 'ücretsiz'"),
    "Windows 10 uygulamalarım Windows 11'de çalışır mı?": (OK, "Doğru"),
    "Copilot+ PC nedir?": (WARN, "Temel bilgi var; bozuk çeviri: 'On-ikisinde AI'"),
    "OneDrive hesabını kim yönetir?": (OK, "Doğru (soruyu tekrar ederek başlıyor)"),
    "TEKNOFEST'te kaç takım yarışır?": (BAD, "Reddetmesi gerekirdi; kaynakta olmayan 'sayı her yıl değişir' iddiası, yazım bozuk"),
    "Microsoft 365 A3 lisansı kaç dolar?": (OK, "Doğru ret: fiyat bilgisi yok"),
    "Bitcoin fiyatı nedir?": (OK, "Eşikte reddedildi"),
    "What is the capital of France?": (OK, "Eşikte reddedildi"),
    "Bugün hava nasıl?": (OK, "Eşikte reddedildi"),
}

NO_HITS_MSG = "Bilgi tabanında yeterli bilgi yok. (eşikte reddedildi)"
REFUSAL_MARKERS = [
    "bilgim yok", "bilgi yok", "bilgi verilmemiş", "bilgi bulunmuyor", "belirtilmemiş",
    "bulunmamaktadır", "bulunmuyor", "bulunamadı", "yeterli bilgi", "don't have",
    "do not have", "no information", "not provided", "not mention", "no_answer",
]


def is_refusal(text):
    t = text.lower()
    return any(m in t for m in REFUSAL_MARKERS)


def cell(text):
    return text.replace("\n", " ").replace("|", "/").strip()


def main():
    print("Modeller yükleniyor...")
    retriever = Retriever(SentenceTransformer(EMBED_MODEL_NAME))
    model = load_llm()
    client = model.get_chat_client()

    rows, auto_ok = [], 0
    try:
        for q, keywords in TESTS:
            t = time.perf_counter()
            results = retriever.search(q)
            top = results[0][2]
            hits = [h for h in results if h[2] >= THRESHOLD]
            try:
                reply = answer(client, q, hits) if hits else NO_HITS_MSG
            except Exception as e:  # noqa: BLE001
                reply = f"HATA: {type(e).__name__}"
            sec = time.perf_counter() - t

            if keywords is None:
                ok = (not hits) or is_refusal(reply)
                expected = "Reddedilmeli"
            else:
                ok = bool(hits) and any(k in reply.lower() for k in keywords)
                expected = "Cevap: " + " / ".join(keywords[:3])

            auto_ok += ok
            mark = OK if ok else BAD
            print(f"{mark} {sec:5.1f}s  skor={top:.3f}  {q}")
            rows.append((q, expected, top, reply, sec, mark))
    finally:
        model.unload()

    total = len(rows)
    avg = sum(r[4] for r in rows) / total
    counts = {OK: 0, WARN: 0, BAD: 0}
    for q, *_ in rows:
        sign = MANUAL.get(q, ("", ""))[0]
        if sign in counts:
            counts[sign] += 1

    lines = [
        "# Uçtan Uca Değerlendirme",
        "",
        f"- LLM: `{LLM_ALIAS}`",
        f"- Embedding: `{EMBED_MODEL_NAME}`",
        f"- Ayarlar: W_QUESTION={W_QUESTION}, THRESHOLD={THRESHOLD}, TOP_K={TOP_K}",
        f"- Otomatik kontrol (anahtar kelime): **{auto_ok}/{total}**",
        f"- Elle değerlendirme: **{counts[OK]} doğru, {counts[WARN]} küçük hata, {counts[BAD]} gerçek hata** ({total} soru)",
        f"- Ortalama süre: {avg:.1f} sn/soru",
        "",
        "| # | Soru | Beklenen | En iyi skor | Gelen cevap | Süre (sn) | Otomatik | Elle değerlendirme |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, (q, exp, sc, reply, sec, mark) in enumerate(rows, 1):
        sign, note = MANUAL.get(q, ("", ""))
        lines.append(
            f"| {i} | {cell(q)} | {cell(exp)} | {sc:.3f} | {cell(reply)} | {sec:.1f} | {mark} | {sign} {cell(note)} |"
        )

    out = BASE_DIR / "degerlendirme.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nOtomatik: {auto_ok}/{total}  |  elle: {counts[OK]} doğru, {counts[WARN]} küçük hata, {counts[BAD]} gerçek hata")
    print(f"Tablo kaydedildi: {out}")


if __name__ == "__main__":
    main()