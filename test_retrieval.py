"""Retrieval testi: doğru kayıt 1. sırada mı, skor eşiği geçiyor mu, alakasız sorular reddediliyor mu?

Çalıştırma:  python test_retrieval.py

Üç grup var:
  A) Bilinen sorular (bazıları aliases_tr.txt içindeki ifadelerle aynı; skorlar biraz şişkin olabilir)
  B) Yeni ifadeler: takma adlarda OLMAYAN Türkçe sorular. Gerçek ölçü bu grup.
  C) Bilgi tabanıyla ilgisiz sorular: eşikte reddedilmeli.
"""
import time

from sentence_transformers import SentenceTransformer

from config import EMBED_MODEL_NAME, THRESHOLD
from retriever import Retriever

# (soru, beklenen kaydın ilk satırında geçen ifadelerden herhangi biri)
GRUP_A = [
    ("What is TEKNOFEST?", ("TEKNOFEST Aerospace and Technology Festival",)),
    ("TEKNOFEST nedir?", ("TEKNOFEST Aerospace and Technology Festival",)),
    ("Is there an admission fee for the festival?", ("admission fee",)),
    ("TEKNOFEST'e giriş ücretli mi?", ("admission fee",)),
    ("TEKNOFEST ne zaman yapılır?", ("When is TEKNOFEST held",)),
    ("TEKNOFEST'e ziyaretçi olarak nasıl katılırım?", ("attend TEKNOFEST as a visitor",)),
    ("TEKNOFEST hangi alanları kapsıyor?", ("Which fields does TEKNOFEST cover",)),
    ("Milli Teknoloji Hamlesi nedir?", ("National Technology Initiative",)),
    ("Microsoft 365 Education nedir?", ("What is Microsoft 365 Education",)),
    ("Microsoft 365 Education kaç para?", ("How much does Microsoft 365 Education cost",)),
    ("Teams'e nasıl giriş yaparım?", ("sign in to Microsoft Teams",)),
    ("Windows 10 uygulamalarım Windows 11'de çalışır mı?", ("Windows 10 applications",)),
    ("OneDrive hesabını kim yönetir?", ("OneDrive",)),
    ("Takımlara maddi destek veriliyor mu?", ("material support",)),
    ("A1, A3 ve A5 arasındaki fark nedir?", ("What version of Microsoft 365 Education",)),
    ("Ulaşım ve konaklama desteği var mı?", ("material support",)),
]

GRUP_B = [
    ("Takımlara para desteği var mı?", ("material support",)),
    ("Finale kalan takımlar için konaklama sağlanıyor mu?", ("material support",)),
    ("Projelere para yardımı yapılıyor mu?", ("material support",)),
    ("Festival ücretsiz mi?", ("admission fee",)),
    ("TEKNOFEST'e kayıt nasıl yapılır?", ("attend TEKNOFEST as a visitor",)),
    ("TEKNOFEST ne amaçla düzenleniyor?", ("primary objective",)),
    ("Windows 11'e geçmeli miyim?", ("major differences between Windows 11", "benefits of the Windows 11")),
    ("Windows 11 almaya değer mi?", ("major differences between Windows 11", "benefits of the Windows 11")),
    ("Eski uygulamalarım Windows 11'de açılır mı?", ("Windows 10 applications",)),
    ("Cihazları Windows 11'e nasıl güncellerim?", ("upgrade my devices",)),
    ("Microsoft 365 Education'ın fiyatı ne kadar?", ("How much does Microsoft 365 Education cost",)),
    ("A3 ile A5 farkı ne?", ("What version of Microsoft 365 Education",)),
    ("Office 365 ve Microsoft 365 Education aynı şey mi?", ("difference between Office 365",)),
    ("Teams'e nasıl giriş yapabilirim?", ("sign in to Microsoft Teams",)),
    ("Teams çalışmıyor, ne yapmalıyım?", ("isn't working",)),
    ("Copilot+ bilgisayar ne işe yarar?", ("Copilot+",)),
    ("OneDrive'ı kim kontrol eder?", ("OneDrive",)),
]

GRUP_C = [
    "What is the capital of France?",
    "Bugün hava nasıl?",
    "Python nedir?",
    "Bitcoin fiyatı nedir?",
    "How do I bake a cake?",
    "En yakın pizzacı nerede?",
    "Fenerbahçe maçı kaç kaç bitti?",
]


def rank_of(results, keys):
    for i, (_, chunk, score) in enumerate(results, 1):
        if any(k.lower() in chunk.split("\n")[0].lower() for k in keys):
            return i, score
    return None, 0.0


def run_answerable(r, grup, baslik):
    print(f"\n--- {baslik} ---")
    gecen = 0
    for q, keys in grup:
        t = time.perf_counter()
        results = r.search(q, k=len(r.chunks))
        ms = (time.perf_counter() - t) * 1000
        rank, score = rank_of(results, keys)
        top = results[0][2]
        ok = rank == 1 and score >= THRESHOLD
        gecen += ok
        mark = "✓" if ok else "✗"
        print(f"{mark} {ms:4.0f}ms  beklenen sıra={rank}, skor={score:.3f}, top={top:.3f}  |  {q}")
    print(f"Geçen: {gecen}/{len(grup)}")
    return gecen, len(grup)


def run_refusals(r, sorular):
    print("\n--- C) Bilgi tabanıyla ilgisiz sorular (reddedilmeli) ---")
    gecen = 0
    for q in sorular:
        top = r.search(q, k=1)[0][2]
        ok = top < THRESHOLD
        gecen += ok
        print(f"{'✓' if ok else '✗'} top={top:.3f} (reddedilmeli)  |  {q}")
    print(f"Geçen: {gecen}/{len(sorular)}")
    return gecen, len(sorular)


def main():
    r = Retriever(SentenceTransformer(EMBED_MODEL_NAME))
    a = run_answerable(r, GRUP_A, "A) Bilinen sorular")
    b = run_answerable(r, GRUP_B, "B) Yeni ifadeler (takma adlarda yok)")
    c = run_refusals(r, GRUP_C)
    toplam = a[0] + b[0] + c[0]
    sayi = a[1] + b[1] + c[1]
    print(f"\nToplam: {toplam}/{sayi}  (eşik={THRESHOLD})")


if __name__ == "__main__":
    main()