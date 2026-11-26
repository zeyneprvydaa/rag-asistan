"""RAG asistanı: top-K retrieval + Foundry Local LLM (CLI)."""
import re

from foundry_local_sdk import Configuration, FoundryLocalManager
from sentence_transformers import SentenceTransformer

from config import EMBED_MODEL_NAME, LLM_ALIAS, THRESHOLD
from retriever import Retriever

# En iyi skordan bu kadar veya daha fazla düşük kayıtlar LLM'e verilmez
SCORE_MARGIN = 0.03
# Cevap üretmeden önce "bu kayıt soruyu gerçekten cevaplıyor mu?" kontrolü
USE_JUDGE = True
# Ön kontrol sadece sayı/miktar soran sorularda çalışır (uydurma en çok burada çıkıyor)
QUANTITY_WORDS = ("kaç", "en fazla", "en az", "ne kadar", "how many", "how much", "maximum", "minimum", "limit")

NO_ANSWER = "NO_ANSWER"
NO_ANSWER_MSG = "Bu konuda bilgim yok. / I don't have that information."

SYSTEM_PROMPT = (
    "You answer questions using FAQ entries. Each entry has a 'Q:' line and an 'A:' line. "
    "Use only the entry whose Q: matches the user's question, and base your answer ONLY on its A: line. "
    "Do not add any detail that is not in that A: line. "
    "Do not start your answer with 'Yes' or 'No'. "
    "Answer in the same language as the user's question, in 1-2 sentences. "
    f"If no entry answers the question, reply with exactly {NO_ANSWER} and nothing else."
)

JUDGE_PROMPT = (
    "You check whether an FAQ entry answers a user's question. "
    "Reply NO only if the A: line is about the same topic but is missing the specific fact the question asks for "
    "(for example the question asks for a number, date, price or limit that is not in the A: line). "
    "If the question asks for advice or a reason (for example 'should I...?' or 'why...?') "
    "and the A: line gives reasons or benefits, reply YES. "
    "Reply with one word: YES or NO."
)


def load_llm():
    FoundryLocalManager.initialize(Configuration(app_name="rag_asistan"))
    manager = FoundryLocalManager.instance
    manager.download_and_register_eps()
    model = manager.catalog.get_model(LLM_ALIAS)
    model.download(lambda p: print(f"\rModel indiriliyor: {p:.1f}%", end=""))
    print()
    model.load()
    return model


def format_chunk(chunk):
    """İlk satırı soru, kalanı cevap olarak etiketler."""
    parts = chunk.split("\n", 1)
    if len(parts) == 2:
        return f"Q: {parts[0]}\nA: {parts[1]}"
    return chunk


def _norm(s):
    return " ".join(s.split()).lower()


def clean_answer(out, hits):
    # <think> bloğunu temizle (Qwen3 ailesi)
    text = re.sub(r"<think>.*?</think>", "", out, flags=re.S).strip()
    # Model cevap + NO_ANSWER karışık yazarsa kelimeyi at, cevabı koru
    text = text.replace(NO_ANSWER, "").strip()
    # Kaynak etiketlerini kopyalarsa baştaki "Q: ..." / "A:" satırlarını at
    lines = text.split("\n")
    while lines and re.match(r"^\s*Q:", lines[0]):
        lines.pop(0)
    text = "\n".join(lines).strip()
    text = re.sub(r"^\s*A:\s*", "", text)
    # Baştaki Yes/No/Evet/Hayır'ı at
    text = re.sub(r"^(yes|no|evet|hayır|hayir)[,.!]?\s+", "", text, flags=re.I)

    # Kaynak metni aynen kopyalanmış paragrafları at (başka paragraf kaldıysa)
    kaynak = _norm(" ".join(c for _, c, _ in hits))
    paragraflar = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    kalan = [p for p in paragraflar if _norm(p) not in kaynak]
    if kalan:
        text = "\n\n".join(kalan)

    if not text:
        return NO_ANSWER_MSG
    return text[0].upper() + text[1:]


def needs_check(question):
    q = question.lower()
    return any(w in q for w in QUANTITY_WORDS)


def chunk_answers(client, question, chunk):
    """LLM'e 'bu kayıt soruyu doğrudan cevaplıyor mu?' diye sorar."""
    messages = [
        {"role": "system", "content": JUDGE_PROMPT},
        {"role": "user", "content": f"{format_chunk(chunk)}\n\nUser question: {question}"},
    ]
    out = client.complete_chat(messages).choices[0].message.content
    out = re.sub(r"<think>.*?</think>", "", out, flags=re.S).strip().upper()
    return not out.startswith("NO") and not out.startswith("HAYIR")


def answer(client, question, hits):
    context = "\n\n".join(f"[Source: {s}]\n{format_chunk(c)}" for s, c, _ in hits)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"FAQ entry:\n{context}\n\nUser question: {question}"},
    ]
    out = client.complete_chat(messages).choices[0].message.content
    return clean_answer(out, hits)


def main():
    print("Embedding modeli yükleniyor...")
    retriever = Retriever(SentenceTransformer(EMBED_MODEL_NAME))

    print("Foundry Local başlatılıyor...")
    model = load_llm()
    client = model.get_chat_client()
    print("\n✅ Asistan hazır! (Çıkış için 'q')\n")

    try:
        while True:
            q = input("Soru: ").strip()
            if q.lower() == "q":
                break
            if not q:
                continue

            results = retriever.search(q)
            print(f"[En iyi eşleşme skoru: {results[0][2] * 100:.1f}%]")
            hits = [h for h in results if h[2] >= THRESHOLD]
            if not hits:
                print("Bilgi tabanında yeterli bilgi yok.\n")
                continue

            # En iyi skora çok uzak kayıtları ele (LLM'i şaşırtmasınlar)
            hits = [h for h in hits if h[2] >= hits[0][2] - SCORE_MARGIN]

            for s, c, sc in hits:
                print(f"  -> ({s}, {sc:.3f}) {c.splitlines()[0]}")

            try:
                if USE_JUDGE and needs_check(q) and not chunk_answers(client, q, hits[0][1]):
                    print(f"\nCevap: {NO_ANSWER_MSG}")
                    print("(Ön kontrol: en iyi kayıt soruyu doğrudan cevaplamıyor)\n")
                    continue
                cevap = answer(client, q, hits)
            except Exception as e:
                cevap = f"Cevap üretilemedi ({e})"
            print(f"\nCevap: {cevap}")
            for _, c, sc in hits:
                print(f"Kaynak ({sc:.3f}): {c.split(chr(10), 1)[-1]}")
            print()
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        model.unload()
        print("Çıkılıyor...")


if __name__ == "__main__":
    main()