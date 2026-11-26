"""Uçtan uca değerlendirme: retrieval + ön kontrol + LLM cevabı, degerlendirme.md üretir.

Çalıştırma:  python test_end_to_end.py

NOT: Otomatik işaret anahtar kelime kontrolüne dayanan KABA bir ölçüdür (çeviri hatalarını göremez).
Rapora koymadan önce cevapları oku ve MANUAL sözlüğüne kendi değerlendirmeni yaz.
"""
import time

from sentence_transformers import SentenceTransformer

from config import BASE_DIR, EMBED_MODEL_NAME, LLM_ALIAS, THRESHOLD, TOP_K, W_QUESTION
from rag_asistan import (
    NO_ANSWER_MSG,
    SCORE_MARGIN,
    USE_JUDGE,
    answer,
    chunk_answers,
    load_llm,
    needs_check,
)
from retriever import Retriever

# (soru, cevapta geçmesi beklenen anahtar kelimelerden herhangi biri; None = reddedilmeli)
TESTS = [
    # --- TEKNOFEST ---
    ("TEKNOFEST nedir?", ["festival", "havacılık", "aerospace"]),
    ("What is TEKNOFEST?", ["festival", "aerospace", "largest"]),
    ("TEKNOFEST'e giriş ücretli mi?", ["ücretsiz", "değildir", "free"]),
    ("Is there an admission fee for the festival?", ["no admission", "free", "no fee"]),
    ("TEKNOFEST ne zaman yapılır?", ["her yıl", "farklı", "every year"]),
    ("TEKNOFEST'e ziyaretçi olarak nasıl katılırım?", ["kayıt", "qr", "registration"]),
    ("TEKNOFEST hangi alanları kapsıyor?", ["yapay zeka", "artificial intelligence", "havacılık"]),
    ("Rapor şablonlarını nereden indirebilirim?", ["şartname", "belge", "specification"]),
    ("Milli Teknoloji Hamlesi nedir?", ["vizyon", "kalkınma", "vision"]),
    ("Takımlara maddi destek veriliyor mu?", ["destek", "ulaşım", "konaklama", "support"]),
    ("Ulaşım ve konaklama desteği var mı?", ["ulaşım", "konaklama", "transportation"]),
    ("Projelere para yardımı yapılıyor mu?", ["destek", "support"]),
    # --- Microsoft 365 Education ---
    ("Microsoft 365 Education nedir?", ["platform"]),
    ("What is Microsoft 365 Education?", ["platform"]),
    ("Microsoft 365 Education kaç para?", ["kademe", "üç", "three"]),
    ("A1, A3 ve A5 arasındaki fark nedir?", ["a1", "a3", "a5"]),
    ("Office 365 ile Microsoft 365 Education arasındaki fark nedir?", ["ai", "yapay zeka", "güvenlik"]),
    ("Teams'e nasıl giriş yaparım?", ["e-posta", "şifre", "email"]),
    ("How do I sign in to Teams?", ["email", "password", "sign in"]),
    ("Windows 11'e geçmeli miyim?", ["hız", "güvenlik", "speed", "faydalı"]),
    ("Windows 10 uygulamalarım Windows 11'de çalışır mı?", ["uyumlu", "compatible", "çalışır"]),
    ("Copilot+ PC nedir?", ["yapay zeka", "ai", "on-device"]),
    ("OneDrive hesabını kim yönetir?", ["okul", "school", "yönetici"]),
    # --- Reddedilmesi gerekenler: konuya yakın ama kaynakta cevabı yok ---
    ("TEKNOFEST'te kaç takım yarışır?", None),
    ("TEKNOFEST'e kaç kişi katılıyor?", None),
    ("Teams toplantısına en fazla kaç kişi katılabilir?", None),
    ("Microsoft 365 A3 lisansı kaç dolar?", None),
    ("TEKNOFEST ödülleri ne kadar?", None),
    # --- Reddedilmesi gerekenler: konu dışı ---
    ("Bitcoin fiyatı nedir?", None),
    ("What is the capital of France?", None),
    ("Bugün hava nasıl?", None),
    ("Python nedir?", None),
]

# Elle değerlendirme (çalıştırdıktan sonra cevapları okuyup doldur), örnek:
#   "Soru metni": "✅ Doğru",  "⚠️ Küçük hata: ...",  "❌ Yanlış: ..."
MANUAL = {
    "TEKNOFEST nedir?": "⚠️ Doğru bilgi, ama cevap soruyu tekrarlayarak başlıyor",
    "What is TEKNOFEST?": "✅ Doğru, kaynakla birebir",
    "TEKNOFEST'e giriş ücretli mi?": "✅ Doğru",
    "Is there an admission fee for the festival?": "✅ Doğru",
    "TEKNOFEST ne zaman yapılır?": "✅ Doğru",
    "TEKNOFEST'e ziyaretçi olarak nasıl katılırım?": "✅ Doğru",
    "TEKNOFEST hangi alanları kapsıyor?": "⚠️ Kapsam doğru; çeviri hatası: 'environment' yerine 'çeviklik'",
    "Rapor şablonlarını nereden indirebilirim?": "⚠️ Sayfa adı yanlış çevrilmiş ('Sınavlar ve Belgeler')",
    "Milli Teknoloji Hamlesi nedir?": "✅ Doğru",
    "Takımlara maddi destek veriliyor mu?": "⚠️ İçerik doğru; Türkçe-İngilizce karışık, soruyu tekrarlıyor",
    "Ulaşım ve konaklama desteği var mı?": "✅ Doğru",
    "Projelere para yardımı yapılıyor mu?": "⚠️ Çeviri hatası ('kahramanluk'), 'finale kalan takımlar' koşulu eksik",
    "Microsoft 365 Education nedir?": "⚠️ Doğru bilgi, ama cümle İngilizce karışmış ve tekrarlı",
    "What is Microsoft 365 Education?": "✅ Doğru, kaynakla birebir",
    "Microsoft 365 Education kaç para?": "⚠️ Ön kontrol reddetti; kayıttaki 'üç kademe, satış ortağı' bilgisi verilmedi",
    "A1, A3 ve A5 arasındaki fark nedir?": "⚠️ Genel olarak doğru; yazım hatası ('kapsamunda'), kaynakta olmayan 'sadece' ifadesi",
    "Office 365 ile Microsoft 365 Education arasındaki fark nedir?": "✅ Doğru",
    "Teams'e nasıl giriş yaparım?": "✅ Doğru (soruyu tekrar ederek başlıyor)",
    "How do I sign in to Teams?": "✅ Doğru, kaynakla uyumlu",
    "Windows 11'e geçmeli miyim?": "✅ Doğru, kaynakla uyumlu",
    "Windows 10 uygulamalarım Windows 11'de çalışır mı?": "✅ Doğru",
    "Copilot+ PC nedir?": "⚠️ Temel bilgi var; bozuk çeviri: 'On-ikisinde AI'",
    "OneDrive hesabını kim yönetir?": "✅ Doğru (soruyu tekrar ederek başlıyor)",
    "TEKNOFEST'te kaç takım yarışır?": "✅ Doğru ret (ön kontrol)",
    "TEKNOFEST'e kaç kişi katılıyor?": "✅ Doğru ret (ön kontrol)",
    "Teams toplantısına en fazla kaç kişi katılabilir?": "✅ Doğru ret (ön kontrol)",
    "Microsoft 365 A3 lisansı kaç dolar?": "✅ Doğru ret (ön kontrol)",
    "TEKNOFEST ödülleri ne kadar?": "✅ Doğru ret (ön kontrol)",
    "Bitcoin fiyatı nedir?": "✅ Eşikte reddedildi",
    "What is the capital of France?": "✅ Eşikte reddedildi",
    "Bugün hava nasıl?": "✅ Eşikte reddedildi",
    "Python nedir?": "✅ Eşikte reddedildi",
}

REFUSAL_MARKERS = [
    "bilgim yok", "bilgi yok", "bilgi verilmemiş", "bilgi bulunmuyor", "bilgi bulunmamaktadır",
    "bulunmamaktadır", "belirtilmemiş", "yeterli bilgi", "don't have", "do not have",
    "no information", "not provided", "not mention", "no_answer",
]


def is_refusal(text):
    t = text.lower()
    return any(m in t for m in REFUSAL_MARKERS)


def cell(text):
    """Markdown tablo hücresi için satır sonu ve | karakterlerini temizle."""
    return text.replace("\n", " ").replace("|", "/").strip()


def respond(retriever, client, q):
    """rag_asistan.py'deki akışın aynısı. Döner: (en iyi skor, cevap metni, reddedildi mi?)"""
    results = retriever.search(q)
    top_score = results[0][2]
    hits = [h for h in results if h[2] >= THRESHOLD]
    if not hits:
        return top_score, "Bilgi tabanında yeterli bilgi yok. (eşikte reddedildi)", True
    hits = [h for h in hits if h[2] >= hits[0][2] - SCORE_MARGIN]
    if USE_JUDGE and needs_check(q) and not chunk_answers(client, q, hits[0][1]):
        return top_score, NO_ANSWER_MSG + " (ön kontrolde reddedildi)", True
    return top_score, answer(client, q, hits), False


def main():
    print("Modeller yükleniyor...")
    retriever = Retriever(SentenceTransformer(EMBED_MODEL_NAME))
    model = load_llm()
    client = model.get_chat_client()

    rows, passed = [], 0
    try:
        for q, keywords in TESTS:
            t = time.perf_counter()
            try:
                top_score, reply, refused = respond(retriever, client, q)
            except Exception as e:
                top_score, reply, refused = 0.0, f"HATA: {e}", False
            sec = time.perf_counter() - t

            if keywords is None:
                ok = refused or is_refusal(reply)
                expected = "Reddedilmeli"
            else:
                ok = (not refused) and (not is_refusal(reply)) and any(k in reply.lower() for k in keywords)
                expected = "Cevap: " + " / ".join(keywords[:3])

            passed += ok
            mark = "✅" if ok else "❌"
            print(f"{mark} {sec:5.1f}s  skor={top_score:.3f}  {q}\n      -> {reply[:150]}")
            rows.append((q, expected, top_score, reply, sec, mark))
    finally:
        model.unload()

    avg = sum(r[4] for r in rows) / len(rows)
    lines = [
        "# Uçtan Uca Değerlendirme",
        "",
        f"- LLM: `{LLM_ALIAS}`",
        f"- Embedding: `{EMBED_MODEL_NAME}`",
        f"- Ayarlar: W_QUESTION={W_QUESTION}, THRESHOLD={THRESHOLD}, TOP_K={TOP_K}, "
        f"SCORE_MARGIN={SCORE_MARGIN}, USE_JUDGE={USE_JUDGE}, Türkçe takma adlar: açık",
        f"- Otomatik kontrol (anahtar kelime): **{passed}/{len(TESTS)}**",
        f"- Ortalama süre: {avg:.1f} sn/soru",
        "",
        "| # | Soru | Beklenen | En iyi skor | Gelen cevap | Süre (sn) | Otomatik | Elle değerlendirme |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, (q, exp, sc, reply, sec, mark) in enumerate(rows, 1):
        lines.append(
            f"| {i} | {cell(q)} | {cell(exp)} | {sc:.3f} | {cell(reply)} | {sec:.1f} | {mark} | "
            f"{cell(MANUAL.get(q, '—'))} |"
        )

    out = BASE_DIR / "degerlendirme.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSonuç: {passed}/{len(TESTS)}  |  ortalama {avg:.1f} sn/soru")
    print(f"Tablo kaydedildi: {out}")


if __name__ == "__main__":
    main()