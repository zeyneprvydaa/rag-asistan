"""Retrieval testi: doğru chunk 1. sırada mı, konu dışı sorular reddediliyor mu?"""
import time

from sentence_transformers import SentenceTransformer

from config import EMBED_MODEL_NAME, THRESHOLD
from retriever import Retriever

# (soru, beklenen chunk'ın ilk satırı; None = reddedilmeli)
TESTS = [
    ("What is TEKNOFEST?", "What is TEKNOFEST Aerospace and Technology Festival?"),
    ("TEKNOFEST nedir?", "What is TEKNOFEST Aerospace and Technology Festival?"),
    ("Is there an admission fee for the festival?", "Is there an admission fee for the festival?"),
    ("TEKNOFEST'e giriş ücretli mi?", "Is there an admission fee for the festival?"),
    ("TEKNOFEST ne zaman yapılır?", "When is TEKNOFEST held?"),
    ("When is TEKNOFEST held?", "When is TEKNOFEST held?"),
    ("Rapor şablonlarını nereden indirebilirim?", "Where can I access report templates?"),
    ("TEKNOFEST'e ziyaretçi olarak nasıl katılırım?", "How can I attend TEKNOFEST as a visitor?"),
    ("TEKNOFEST hangi alanları kapsıyor?", "Which fields does TEKNOFEST cover?"),
    ("Milli Teknoloji Hamlesi nedir?", "What is the National Technology Initiative?"),
        ("Microsoft 365 Education nedir?", "What is Microsoft 365 Education?"),
    ("Microsoft 365 Education kaç para?", "How much does Microsoft 365 Education cost?"),
    ("Which version of Microsoft 365 Education should my school choose?", "What version of Microsoft 365 Education is right for my institution?"),
    ("Teams'e nasıl giriş yaparım?", "How do I sign in to Microsoft Teams for Education?"),
    ("Windows 10 uygulamalarım Windows 11'de çalışır mı?", "Will my current Windows 10 applications, software or programs work with Windows 11?"),
    ("What is a Copilot+ PC?", "What is a Copilot+ PC and what does on-device AI mean?"),
    ("OneDrive hesabını kim yönetir?", "Who manages the OneDrive account provided with this offer?"),
    ("Which laptops do schools use?", "Which laptops and computers do institutions use?"),
    ("What is the capital of France?", None),
    ("Bugün hava nasıl?", None),
    ("Python nedir?", None),
    ("Bitcoin fiyatı nedir?", None),
    ("How do I bake a cake?", None),
]


def main():
    r = Retriever(SentenceTransformer(EMBED_MODEL_NAME))
    first_lines = [c.split("\n")[0] for c in r.chunks]
    passed = 0

    for q, expected in TESTS:
        t = time.perf_counter()
        hits = r.search(q, k=len(r.chunks))  # tüm chunk'lar skor sırasına göre
        ms = (time.perf_counter() - t) * 1000
        top_score = hits[0][2]

        if expected is None:
            ok = top_score < THRESHOLD
            info = f"top={top_score:.3f} (reddedilmeli)"
        else:
            ranked = [h[1].split("\n")[0] for h in hits]
            rank = ranked.index(expected) + 1
            exp_score = hits[rank - 1][2]
            ok = rank == 1 and exp_score >= THRESHOLD
            info = f"beklenen sıra={rank}, skor={exp_score:.3f}, top={top_score:.3f}"

        passed += ok
        print(f"{'✓' if ok else '✗'} {ms:4.0f}ms  {info}  |  {q}")

    print(f"\nGeçen: {passed}/{len(TESTS)}  (eşik={THRESHOLD})")


if __name__ == "__main__":
    main()